#include "../../ue5/WISEYE/Source/test/WiseEyeThermalMath.h"
#include <fstream>
#include <vector>
#include <stdexcept>
#include <cstdio>
#include <string>
template<class T> std::vector<T> Read(const char* Path,int N) {
    std::ifstream F(Path,std::ios::binary);std::vector<T> V(N);
    if (!F.read(reinterpret_cast<char*>(V.data()),N*sizeof(T))) throw std::runtime_error("Cannot read raw frame/mask");
    return V;
}
int main(int Argc,char** Argv) {
    try {
        if (Argc<6) throw std::runtime_error("Usage: replay signal.f32 sky.u8 target.u8 output.pgm denoise [noise seed frame facade_tone]");
        constexpr int W=640,H=512,N=W*H;
        auto Signal=Read<float>(Argv[1],N);auto Sky=Read<uint8_t>(Argv[2],N);auto Target=Read<uint8_t>(Argv[3],N);
        std::vector<float> Scratch(N);
        WiseEyeThermal::SmoothSky(Signal.data(),Scratch.data(),Sky.data(),W,H,std::stof(Argv[5]));
        WiseEyeThermal::OpticalBlur(Signal.data(),Scratch.data(),W,H,.8f);
        const float Noise=Argc>6?std::stof(Argv[6]):0;
        const uint32_t Seed=Argc>7?uint32_t(std::stoul(Argv[7])):1337;
        const uint64_t Frame=Argc>8?std::stoull(Argv[8]):1;
        const int FacadeTone=Argc>9?std::stoi(Argv[9]):0; // 1 historical; 2 balanced
        const float BackgroundMid=Argc>10?std::stof(Argv[10]):.68f,BackgroundSlope=Argc>11?std::stof(Argv[11]):8.f;
        WiseEyeThermal::Exposure Exposure;Exposure.Low=.05f;Exposure.High=.45f;
        std::vector<uint8_t> Bytes(N);
        for (int I=0;I<N;++I) {
            float V=std::clamp(Signal[I]+Noise*WiseEyeThermal::ReadNoise(Seed,Frame,I),0.f,1.f);
            if (FacadeTone==1) V=WiseEyeThermal::FacadeDisplaySignal(V,Exposure.Low,Sky[I]!=0,Target[I]!=0);
            const float DetectorSignal=V;
            V=Exposure.DisplaySoft(V,1.1f,false);
            if (FacadeTone==2) V=WiseEyeThermal::FacadeDisplayValue(V,Sky[I]!=0,Target[I]==1,DetectorSignal,BackgroundMid,BackgroundSlope);
            Bytes[I]=uint8_t(std::round(255*V));
        }
        if (FacadeTone==2) WiseEyeThermal::SoftenBackgroundDisplay(Bytes.data(),Scratch.data(),Target.data(),W,H,1);
        std::ofstream Out(Argv[4],std::ios::binary);Out<<"P5\n"<<W<<" "<<H<<"\n255\n";
        Out.write(reinterpret_cast<const char*>(Bytes.data()),N);
        if (!Out) throw std::runtime_error("Cannot write replay output");return 0;
    } catch (const std::exception& E) { std::fprintf(stderr,"%s\n",E.what());return 1; }
}
