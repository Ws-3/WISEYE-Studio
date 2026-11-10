#pragma once
// Stable C boundary: UE does not inherit JSBSim's STL, exceptions or RTTI flags.
struct WiseEyeFDMState {
    double dx,dy,dz,speed,yaw,pitch,roll,throttle,alpha,beta,p,q,r,load_factor;
};
#ifdef WISEYE_JSBSIM_EXPORT
#define WISEYE_FDM_API extern "C" __declspec(dllexport)
#else
#define WISEYE_FDM_API extern "C"
#endif
WISEYE_FDM_API void* WiseEyeFDMCreate(const char* Root,char* Error,int Capacity);
WISEYE_FDM_API int WiseEyeFDMReset(void* Handle,double HeadingDeg,double Speed,char* Error,int Capacity);
WISEYE_FDM_API int WiseEyeFDMStep(void* Handle,double Dt,double SpeedCommand,double BankCommandDeg,double GammaCommandDeg,WiseEyeFDMState* Output,char* Error,int Capacity);
WISEYE_FDM_API void WiseEyeFDMDestroy(void* Handle);
