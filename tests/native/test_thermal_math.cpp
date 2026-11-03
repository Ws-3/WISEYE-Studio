#include "../../ue5/WISEYE/Source/test/WiseEyeThermalMath.h"
#include <cassert>
#include <limits>
#include <cstdio>
#include <vector>

int main()
{
    using namespace WiseEyeThermal;
    HeatState A,B;
    for (int I=0;I<10;++I) A.Step(1,1);
    for (int I=0;I<100;++I) B.Step(1,.1f);
    assert(std::abs(A.Motor-B.Motor)<.00001f);
    assert(A.Motor>A.Battery && A.Battery>0);
    A.Motor=A.Battery=1;A.Step(0,35);
    assert(A.Motor<A.Battery && A.Motor>0);
    A.Step(10,10000);assert(A.Motor<=1 && A.Battery<=1);
    float Dark[1000],Bright[1000];
    for (int I=0;I<1000;++I) { Dark[I]=.1f;Bright[I]=.7f; }
    Exposure E;E.Update(Dark,1000,0,1,true);
    assert(E.High-E.Low>=.159f);
    const float Old=E.Low;E.Update(Bright,1000,.1,1,true);
    assert(E.Low>Old && E.Low<.5f); // adaptation must not jump to the new window
    E.Update(Bright,1000,10,1,true);assert(E.Low>.6f);
    assert(std::abs(E.Display(.67f,1,false)+E.Display(.67f,1,true)-1)<.00001f);
    float Bad[]={std::numeric_limits<float>::quiet_NaN(),std::numeric_limits<float>::infinity()};
    const float Before=E.Low;E.Update(Bad,2,11,1,true);assert(E.Low==Before);
    E.Update(Bright,1000,12,1,false);assert(E.Low==0 && E.High==1);
    for (int I=0;I<1000;++I) Dark[I]=.2f;
    Dark[999]=1;E.Time=-1;E.Update(Dark,1000,13,1,true);
    assert(E.High<.4f); // one hot target cannot dictate the whole camera's gain
    E.Low=0;E.High=1;
    assert(E.DisplaySoft(1.2f,1,false)>E.DisplaySoft(.9f,1,false));
    assert(E.DisplaySoft(1.2f,1,false)<1);
    assert(std::abs(E.DisplaySoft(1.2f,1,false)+E.DisplaySoft(1.2f,1,true)-1)<.00001f);
    DetectorSettings D;D.Mode=1;E.Low=.15f;E.High=.65f;
    E.Apply(Bright,1000,99,1,D);assert(E.Low==.15f && E.High==.65f);
    D.Mode=2;D.Low=.2f;D.High=.6f;E.Apply(Bright,1000,100,1,D);assert(E.Low==D.Low && E.High==D.High);
    assert(E.Display(.3f,1,false,.1f)>E.Display(.3f,1,false));
    assert(std::abs(E.Display(.3f,1,false,.1f)+E.Display(.3f,1,true,.1f)-1)<.00001f);
    std::vector<uint8_t> Exclude(1000,0);
    for (int I=0;I<1000;++I) { Bright[I]=I<600?.2f:.9f;Exclude[I]=I>=600; }
    D.Mode=0;D.Stable=true;E.Time=-1;E.Apply(Bright,1000,0,1,D,Exclude.data());assert(E.High<.4f);
    for (float& V:Bright) V=.9f;
    const float Previous=E.Low;E.Apply(Bright,1000,.1,1,D);assert(E.Low-Previous<=.01501f);
    // Losing the last building pixels must hold gain, not switch populations.
    std::vector<uint8_t> AllExcluded(1000,1);
    const float HeldLow=E.Low,HeldHigh=E.High;
    E.Apply(Bright,1000,10,1,D,AllExcluded.data());
    assert(E.Low==HeldLow && E.High==HeldHigh);
    E.Apply(Bright,1000,10.1,1,D);
    assert(std::abs(E.Low-HeldLow)<=.002501f);
    // Identical walls at different sky occupancy retain the same exposure.
    Exposure WallA,WallB;
    float SceneA[1000],SceneB[1000];std::vector<uint8_t> MaskA(1000),MaskB(1000);
    for (int I=0;I<1000;++I) {
        SceneA[I]=I<500?.28f:.05f;MaskA[I]=I>=500;
        SceneB[I]=I<100?.28f:.05f;MaskB[I]=I>=100;
    }
    WallA.Apply(SceneA,1000,0,1,D,MaskA.data());WallB.Apply(SceneB,1000,0,1,D,MaskB.data());
    assert(WallA.Low==WallB.Low && WallA.High==WallB.High);
    const float WallGrey=FacadeDisplayValue(WallA.DisplaySoft(.28f,1.1f,false),false,false);
    assert(WallGrey>.25f && WallGrey<.75f);
    std::vector<float> Cloud(32*32),Original,Scratch(32*32);std::vector<uint8_t> Sky(32*32,1);
    for (int I=0;I<1024;++I) Cloud[I]=.15f+.02f*ReadNoise(1337,1,I);
    for (int I: {500,501,532,533}) { Cloud[I]=.8f;Sky[I]=0; } // two-pixel-wide target
    Sky[0]=0;Cloud[0]=.4f;Original=Cloud;
    SmoothSky(Cloud.data(),Scratch.data(),Sky.data(),32,32,.8f);
    float BeforeRough=0,AfterRough=0;
    for (int Y=1;Y<10;++Y) for (int X=1;X<30;++X) { int I=Y*32+X;BeforeRough+=std::abs(Original[I]-Original[I-1]);AfterRough+=std::abs(Cloud[I]-Cloud[I-1]); }
    assert(AfterRough<BeforeRough*.8f);
    for (int I: {0,500,501,532,533}) assert(Cloud[I]==Original[I]);
    assert(ReadNoise(123,1,4)==ReadNoise(123,1,4));assert(ReadNoise(123,1,4)!=ReadNoise(124,1,4));
    PixelLabels Subpixel;Subpixel.Add(.125f);Subpixel.Add(.125f);Subpixel.Add(.5f);Subpixel.Add(.125f);
    assert(Subpixel.Target && !Subpixel.Sky); // one of four samples is sufficient to protect a tiny target
    E.Low=.05f;E.High=.45f;
    assert(E.DisplaySoft(FacadeDisplaySignal(.35f,E.Low,false,false),1.1f,false)<E.DisplaySoft(.35f,1.1f,false));
    assert(FacadeDisplaySignal(.35f,E.Low,false,true)==.35f);
    assert(FacadeDisplaySignal(.15f,E.Low,true,false)==.15f);
    assert(FacadeDisplayValue(.1f,true,false)==.1f);
    assert(FacadeDisplayValue(1.f,false,true)<.85f);
    assert(FacadeDisplayValue(1.f,false,true,.48f)-FacadeDisplayValue(1.f,false,true,.34f)>.08f);
    assert(FacadeDisplayValue(.9f,false,true)>FacadeDisplayValue(.6f,false,true));
    assert(FacadeDisplayValue(.5f,false,false)>FacadeDisplayValue(.3f,false,false));
    assert(FacadeDisplayValue(.70f,false,false)>.5f);
    assert(FacadeDisplayValue(.78f,false,false)-FacadeDisplayValue(.60f,false,false)>.4f);
    uint8_t Edge[5]={0,0,255,0,0},Mask[5]={0,0,0,0,0};float Work[5];
    SoftenBackgroundDisplay(Edge,Work,Mask,5,1,1);assert(Edge[2]<255 && Edge[2]>100);
    uint8_t Small[5]={0,0,255,0,0};Mask[2]=1;
    SoftenBackgroundDisplay(Small,Work,Mask,5,1,1);assert(Small[2]==255 && Small[1]==0);
    std::puts("thermal math invariants: passed");
}
