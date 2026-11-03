#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>

namespace WiseEyeEvents {
struct Event { int X,Y,P;int64_t T; };
struct Model {
    float On=.2f,Off=.2f;int64_t Refractory=100;
    int W=0,H=0;double PreviousTime=-1;
    std::vector<float> Previous,Reference;
    std::vector<int64_t> Last;
    uint64_t Truncated=0;
    void Reset() { W=H=0;PreviousTime=-1;std::vector<float>().swap(Previous);std::vector<float>().swap(Reference);std::vector<int64_t>().swap(Last);Truncated=0; }
    std::vector<Event> Process(const float* Intensity,int Width,int Height,double Time,size_t Limit=20000) {
        std::vector<Event> Out;
        if (!Intensity || Width<=0 || Height<=0 || !std::isfinite(Time) || Time<0 || (PreviousTime>=0 && Time<=PreviousTime)) return Out;
        const int Count=Width*Height;std::vector<float> Current(Count);
        for (int I=0;I<Count;++I) Current[I]=std::isfinite(Intensity[I])?std::log(std::max(1e-6f,Intensity[I])):((W==Width && H==Height && PreviousTime>=0)?Previous[I]:std::log(1e-6f));
        if (W!=Width || H!=Height || PreviousTime<0) {
            W=Width;H=Height;Reference=Previous=Current;Last.assign(Count,-1000000000);PreviousTime=Time;return Out;
        }
        Out.reserve(std::min(Limit,size_t(Count)));
        uint64_t Seen=0;uint32_t Random=0x9e3779b9u;
        for (int I=0;I<Count;++I) {
            const float Delta=Current[I]-Reference[I];const int P=Delta>=0?1:-1;
            const float Step=P>0?On:Off;
            const int N=std::min(100000,int(std::floor(std::abs(Delta)/Step)));
            const float Before=Reference[I];
            for (int K=1;K<=std::min(N,8);++K) {
                const float Slope=Current[I]-Previous[I];
                const float A=std::abs(Slope)>1e-9f?std::clamp((Before+P*Step*K-Previous[I])/Slope,0.f,1.f):1.f;
                const int64_t T=int64_t(std::llround((PreviousTime+(Time-PreviousTime)*A)*1e6));
                if (T-Last[I]<Refractory) continue;
                Last[I]=T;
                ++Seen;
                if (Out.size()<Limit) Out.push_back({I%W,I/W,P,T});
                else {
                    // Bounded reservoir avoids discarding only the bottom of
                    // the image during global illumination or camera motion.
                    ++Truncated;Random^=Random<<13;Random^=Random>>17;Random^=Random<<5;
                    const uint64_t Pick=Random%Seen;
                    if (Pick<Limit) Out[size_t(Pick)]={I%W,I/W,P,T};
                }
            }
            if (N>8) Truncated+=N-8;
            Reference[I]+=P*Step*N;
        }
        std::sort(Out.begin(),Out.end(),[](const Event& A,const Event& B){return A.T<B.T || (A.T==B.T && (A.Y<B.Y || (A.Y==B.Y && A.X<B.X)));});
        Previous=std::move(Current);PreviousTime=Time;return Out;
    }
};
}
