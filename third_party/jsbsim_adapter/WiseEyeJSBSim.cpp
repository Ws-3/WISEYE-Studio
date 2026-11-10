#include "WiseEyeJSBSim.h"
#include "FGFDMExec.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <memory>
#include <stdexcept>
namespace {
constexpr double Pi=3.141592653589793,Feet=.3048,Step=1./120.;
double Rad(double V){return V*Pi/180.;}
double Deg(double V){return V*180./Pi;}
double Clamp(double V,double A,double B){return std::clamp(V,A,B);}
struct Aircraft {
    std::unique_ptr<JSBSim::FGFDMExec> F;
    double Accumulator=0,Throttle=.2,Aileron=0,Elevator=0,Rudder=0;
    WiseEyeFDMState Last{};
    double Get(const char* Key){return F->GetPropertyValue(Key);}
    void Set(const char* Key,double V){F->SetPropertyValue(Key,V);}
};
void ErrorText(char* Out,int N,const char* Message){if(Out && N>0){std::strncpy(Out,Message,N-1);Out[N-1]=0;}}
}
void* WiseEyeFDMCreate(const char* Root,char* Error,int Capacity) {
    try {
        auto A=std::make_unique<Aircraft>();A->F=std::make_unique<JSBSim::FGFDMExec>();
        A->F->SetDebugLevel(0);A->F->SetRootDir(SGPath(Root));
        A->F->SetAircraftPath(SGPath("aircraft"));A->F->SetEnginePath(SGPath("engine"));A->F->SetSystemsPath(SGPath("systems"));
        A->F->Setdt(Step);
        if(!A->F->LoadModel("wiseye80"))throw std::runtime_error("JSBSim could not load wiseye80.xml");
        return A.release();
    } catch(const std::exception& E){ErrorText(Error,Capacity,E.what());return nullptr;}
    catch(...){ErrorText(Error,Capacity,"JSBSim initialization failed");return nullptr;}
}
int WiseEyeFDMReset(void* Handle,double HeadingDeg,double Speed,char* Error,int Capacity) {
    try {
        auto& A=*static_cast<Aircraft*>(Handle);
        A.Set("ic/lat-gc-deg",0);A.Set("ic/long-gc-deg",0);A.Set("ic/h-sl-ft",500/Feet);
        A.Set("ic/terrain-elevation-ft",0);A.Set("ic/psi-true-deg",HeadingDeg);
        A.Set("ic/phi-deg",0);A.Set("ic/gamma-deg",0);A.Set("ic/vt-fps",Speed/Feet);
        A.Set("ic/alpha-deg",3);A.Set("ic/beta-deg",0);
        A.Set("ic/p-rad_sec",0);A.Set("ic/q-rad_sec",0);A.Set("ic/r-rad_sec",0);
        A.Set("fcs/elevator-cmd-norm",-.08);A.Set("fcs/aileron-cmd-norm",0);A.Set("fcs/rudder-cmd-norm",0);A.Set("fcs/throttle-cmd-norm",.2);
        if(!A.F->RunIC())throw std::runtime_error("JSBSim initial conditions failed");
        A.Accumulator=0;A.Throttle=.2;A.Aileron=0;A.Elevator=-.08;A.Rudder=0;A.Last={};
        A.Last.speed=Speed;A.Last.yaw=HeadingDeg;A.Last.pitch=3;A.Last.alpha=3;
        return 1;
    }catch(const std::exception& E){ErrorText(Error,Capacity,E.what());return 0;}
    catch(...){ErrorText(Error,Capacity,"JSBSim reset failed");return 0;}
}
int WiseEyeFDMStep(void* Handle,double Dt,double SpeedCommand,double BankCommandDeg,double GammaCommandDeg,WiseEyeFDMState* Output,char* Error,int Capacity) {
    try {
        if(!Handle || !Output || !std::isfinite(Dt) || Dt<0 || !std::isfinite(SpeedCommand) || !std::isfinite(BankCommandDeg) || !std::isfinite(GammaCommandDeg))throw std::runtime_error("Invalid JSBSim step arguments");
        auto& A=*static_cast<Aircraft*>(Handle);A.Accumulator+=Clamp(Dt,0.,.1);
        double Dx=0,Dy=0,Dz=0;
        while(A.Accumulator+1e-10>=Step) {
            A.Accumulator-=Step;
            const double V=A.Get("velocities/vt-fps")*Feet,Phi=A.Get("attitude/phi-rad"),Theta=A.Get("attitude/theta-rad");
            const double P=A.Get("velocities/p-rad_sec"),Q=A.Get("velocities/q-rad_sec"),R=A.Get("velocities/r-rad_sec");
            const double Gamma=std::atan2(-A.Get("velocities/v-down-fps"),std::hypot(A.Get("velocities/v-north-fps"),A.Get("velocities/v-east-fps")));
            const double Bank=Rad(Clamp(BankCommandDeg,-30.,30.));
            const double G=Rad(Clamp(GammaCommandDeg,-12.,12.));
            const double Cl=.65*9.80665/(.5*1.17*std::max(25.,V*V)*.15*std::max(.6,std::cos(Phi)));
            const double TrimAlpha=Clamp((Cl-.2)/4.5,-.05,.22);
            const double Pitch=Clamp(TrimAlpha+G+.65*(G-Gamma),Rad(-15),Rad(25));
            const double Throttle=Clamp(.18+.16*(SpeedCommand-V)+.8*std::sin(G),0.,1.);
            const double Aileron=Clamp(2.4*(Bank-Phi)-.4*P,-.65,.65);
            const double Elevator=Clamp(-.04-.8*TrimAlpha-2.4*(Pitch-Theta)+.5*Q,-.7,.7);
            const double Rudder=Clamp(-.6*A.Get("aero/beta-rad")-.15*R,-.3,.3);
            const double K=1-std::exp(-Step/.12);
            A.Aileron+=(Aileron-A.Aileron)*K;A.Elevator+=(Elevator-A.Elevator)*K;A.Rudder+=(Rudder-A.Rudder)*K;
            A.Throttle+=(Throttle-A.Throttle)*(1-std::exp(-Step/.45));
            A.Set("fcs/throttle-cmd-norm",A.Throttle);A.Set("fcs/aileron-cmd-norm",A.Aileron);A.Set("fcs/elevator-cmd-norm",A.Elevator);A.Set("fcs/rudder-cmd-norm",A.Rudder);
            if(!A.F->Run())throw std::runtime_error("JSBSim run stopped");
            Dx+=A.Get("velocities/v-north-fps")*Feet*Step;Dy+=A.Get("velocities/v-east-fps")*Feet*Step;Dz-=A.Get("velocities/v-down-fps")*Feet*Step;
        }
        auto& S=A.Last;S.dx=Dx;S.dy=Dy;S.dz=Dz;S.speed=A.Get("velocities/vt-fps")*Feet;
        S.yaw=A.Get("attitude/psi-deg");S.pitch=A.Get("attitude/theta-deg");S.roll=A.Get("attitude/phi-deg");S.throttle=A.Throttle;
        S.alpha=A.Get("aero/alpha-deg");S.beta=A.Get("aero/beta-deg");S.p=A.Get("velocities/p-rad_sec");S.q=A.Get("velocities/q-rad_sec");S.r=A.Get("velocities/r-rad_sec");S.load_factor=A.Get("accelerations/Nz");
        for(double Value:{S.dx,S.dy,S.dz,S.speed,S.yaw,S.pitch,S.roll,S.alpha,S.beta,S.p,S.q,S.r})if(!std::isfinite(Value))throw std::runtime_error("JSBSim nonfinite state");
        *Output=S;return 1;
    }catch(const std::exception& E){ErrorText(Error,Capacity,E.what());return 0;}
    catch(...){ErrorText(Error,Capacity,"JSBSim integration failed");return 0;}
}
void WiseEyeFDMDestroy(void* Handle){delete static_cast<Aircraft*>(Handle);}
