#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

// Normalized engineering signals, NOT degrees Celsius or calibrated radiance.
namespace WiseEyeThermal
{
struct DetectorSettings
{
    int Mode=0; // 0 auto, 1 hold current window, 2 manual normalized signal range
    bool Stable=false,SensorNoise=false,Facade=false;
    float Low=0,High=1,Brightness=0,Denoise=0,Noise=0;
    uint32_t Seed=1337;
    bool operator==(const DetectorSettings& D) const {
        return Mode==D.Mode && Stable==D.Stable && SensorNoise==D.SensorNoise && Facade==D.Facade && Low==D.Low && High==D.High && Brightness==D.Brightness && Denoise==D.Denoise && Noise==D.Noise && Seed==D.Seed;
    }
};
struct PixelLabels
{
    bool Sky=true,Target=false,Motor=false;
    void Add(float B) { Sky=Sky && B>.06f && B<.2f;Target=Target || B>.25f;Motor=Motor || B>.75f; }
};
// Historical signal scaling for replay flag 1; runtime uses FacadeDisplayValue.
inline float FacadeDisplaySignal(float Signal,float Low,bool Sky,bool Target) {
    return Sky || Target ? Signal : Low+(Signal-Low)*.72f;
}
// Display-domain tone, after the common AGC. Keep sky dark, lift background
// midtone contrast, and reduce the whole-target white silhouette without flattening heat.
inline float FacadeDisplayValue(float Value,bool Sky,bool Target,float Signal=-1.f) {
    Value=std::clamp(Value,0.f,1.f);
    if (Sky) return Value;
    if (Target) {
        if (Signal<0) return .82f*Value; // Historical replay without raw heat.
        // A sky-only AGC window can clip every part of the drone equally.
        // Retain the measured normalized-signal differences in the highlights.
        const float Heat=.62f+.24f*std::tanh((Signal-.33f)*6.f);
        return .35f*.82f*Value+.65f*Heat;
    }
    // Spread the middle of the background range; soft shoulders preserve roofs
    // and shaded walls instead of flattening the whole city to one grey level.
    return .08f+.76f*(.5f+.5f*std::tanh((Value-.68f)*8.f));
}
// A weak final optical low-pass tames tone-expanded outlines. Protect targets
// and their immediate neighbours so tiny drone heat does not bleed into sky.
inline void SoftenBackgroundDisplay(uint8_t* Data,float* Scratch,const uint8_t* Target,int W,int H,int Stride=4) {
    for (int Y=0;Y<H;++Y) for (int X=0;X<W;++X) {
        const int I=Y*W+X;float Sum=.4f*Data[I*Stride];bool Protected=Target[I]!=0;
        for (int J : {Y*W+std::max(0,X-1),Y*W+std::min(W-1,X+1),std::max(0,Y-1)*W+X,std::min(H-1,Y+1)*W+X}) {
            Protected=Protected || Target[J]!=0;Sum+=.15f*Data[J*Stride];
        }
        Scratch[I]=Protected?float(Data[I*Stride]):Sum;
    }
    for (int I=0;I<W*H;++I) {
        const uint8_t V=uint8_t(std::round(Scratch[I]));
        for (int C=0;C<std::min(Stride,3);++C) Data[I*Stride+C]=V;
    }
}
inline uint32_t Hash(uint32_t X) { X^=X>>16;X*=0x7feb352du;X^=X>>15;X*=0x846ca68bu;return X^(X>>16); }
inline float ReadNoise(uint32_t Seed,uint64_t Frame,uint32_t Pixel) {
    const float Temporal=float(Hash(Seed^Hash(uint32_t(Frame))^Hash(Pixel))&65535)/65535.f-.5f;
    const float Fixed=float(Hash(Seed^Pixel^0xa511e9b3u)&65535)/65535.f-.5f;
    return Temporal+.15f*Fixed;
}
// Spatial-only cloud smoothing: no history, no reprojection or target averaging.
inline void SmoothSky(float* Data,float* Scratch,const uint8_t* Sky,int W,int H,float Amount)
{
    if (Amount<=0) return;
    auto Pass=[&](const float* In,float* Out,bool Horizontal) {
        for (int Y=0;Y<H;++Y) for (int X=0;X<W;++X) {
            const int I=Y*W+X;const float C=In[I];
            if (!Sky[I]) { Out[I]=C;continue; }
            float Sum=2*C,Weight=2;
            for (int D : {-1,1}) {
                const int J=Horizontal?Y*W+std::clamp(X+D,0,W-1):std::clamp(Y+D,0,H-1)*W+X;
                if (!Sky[J]) continue;
                const float Delta=In[J]-C;
                const float K=std::max(0.f,1.f-Delta*Delta/(.06f*.06f));
                Sum+=K*In[J];Weight+=K;
            }
            Out[I]=C+Amount*(Sum/Weight-C);
        }
    };
    Pass(Data,Scratch,true);Pass(Scratch,Data,false);
}
inline void OpticalBlur(float* Data,float* Scratch,int W,int H,float Sigma)
{
    if (Sigma<=.01f) return;
    const int Radius=std::clamp(int(std::ceil(Sigma*2)),1,4);std::array<float,9> Kernel{};
    float Sum=0;
    for (int K=-Radius;K<=Radius;++K) { float V=std::exp(-.5f*K*K/(Sigma*Sigma));Kernel[K+Radius]=V;Sum+=V; }
    for (float& V:Kernel) V/=Sum;
    for (int Y=0;Y<H;++Y) for (int X=0;X<W;++X) { float V=0;for (int K=-Radius;K<=Radius;++K) V+=Data[Y*W+std::clamp(X+K,0,W-1)]*Kernel[K+Radius];Scratch[Y*W+X]=V; }
    for (int Y=0;Y<H;++Y) for (int X=0;X<W;++X) { float V=0;for (int K=-Radius;K<=Radius;++K) V+=Scratch[std::clamp(Y+K,0,H-1)*W+X]*Kernel[K+Radius];Data[Y*W+X]=V; }
}
inline float Approach(float Value,float Target,float Dt,float Tau)
{
    return Target+(Value-Target)*std::exp(-std::max(0.f,Dt)/std::max(.01f,Tau));
}
struct HeatState
{
    float Motor=0, Battery=0;
    void Step(float Power,float Dt) {
        Power=std::clamp(Power,0.f,1.f);
        Motor=Approach(Motor,Power,Dt,Power>Motor?12.f:35.f);
        Battery=Approach(Battery,Power,Dt,Power>Battery?55.f:110.f);
    }
};
struct Exposure
{
    float Low=0,High=1;
    double Time=-1;
    void Update(const float* Data,int Count,double Now,float Response,bool Auto,bool Stable=false,const uint8_t* Exclude=nullptr) {
        if (!Auto) { Low=0;High=1;Time=Now;return; }
        std::array<uint32_t,256> Histogram{};
        int Valid=0;
        for (int I=0;I<Count;++I) if (std::isfinite(Data[I]) && !(Stable && Exclude && Exclude[I])) {
            ++Histogram[int(std::clamp(Data[I],0.f,1.f)*255.f)];++Valid;
        }
        if (Stable && Exclude && Valid<std::max(32,Count/100)) {
            // Sky/target-only views must not replace the building window with a
            // different population. Hold the last exposure until terrain returns.
            if (Time>=0) { Time=std::max(Time,Now);return; }
            Histogram.fill(0);Valid=0;
            for (int I=0;I<Count;++I) if (std::isfinite(Data[I])) { ++Histogram[int(std::clamp(Data[I],0.f,1.f)*255.f)];++Valid; }
        }
        if (!Valid) return;
        auto Percentile=[&](float P) {
            uint32_t Sum=0;const auto Threshold=uint32_t(std::max(1,int(std::ceil(Valid*P))));
            for (int I=0;I<256;++I) { Sum+=Histogram[I];if (Sum>=Threshold) return I/255.f; }
            return 1.f;
        };
        float L=Percentile(Stable?.005f:.02f)-.025f,H=Percentile(Stable?.995f:.98f)+(Stable?.055f:.025f);
        // This normalized proxy places ordinary facades around .25-.30.
        // Keep an engineering reference window in stable auto mode: a nearly
        // uniform wall must not define its own black point. Not Celsius limits.
        if (Stable) { L=std::min(L,.10f);H=std::max(H,.36f); }
        const float Half=Stable?.10f:.08f;
        if (H-L<2*Half) { const float Mid=(L+H)*.5f;L=Mid-Half;H=Mid+Half; }
        if (Time<0) { Low=L;High=H; }
        else if (Now>Time) {
            const float Dt=Stable?std::min(.25f,float(Now-Time)):float(Now-Time);
            auto Adapt=[&](float Old,float Desired) {
                if (Stable && std::abs(Desired-Old)<.003f) return Old;
                const float V=Approach(Old,Desired,Dt,Response);
                return Stable?Old+std::clamp(V-Old,-.025f*Dt,.025f*Dt):V;
            };
            Low=Adapt(Low,L);High=Adapt(High,H);
        }
        Time=std::max(Time,Now);
    }
    float Display(float Signal,float Contrast,bool BlackHot,float Brightness=0) const {
        float V=std::clamp(((Signal-Low)/std::max(.001f,High-Low)-.5f)*Contrast+.5f+Brightness,0.f,1.f);
        return BlackHot?1.f-V:V;
    }
    void Apply(const float* Data,int Count,double Now,float Response,const DetectorSettings& D,const uint8_t* Exclude=nullptr) {
        if (D.Mode==1) { Time=Now;return; }
        if (D.Mode==2) { Low=D.Low;High=D.High;Time=Now;return; }
        Update(Data,Count,Now,Response,true,D.Stable,Exclude);
    }
    float DisplaySoft(float Signal,float Contrast,bool BlackHot,float Brightness=0) const {
        float V=((Signal-Low)/std::max(.001f,High-Low)-.5f)*Contrast+.5f+Brightness;
        if (V>.75f) V=.75f+.25f*(1.f-std::exp(-(V-.75f)/.5f));
        V=std::clamp(V,0.f,1.f);
        return BlackHot?1.f-V:V;
    }
};
}
