#pragma once
#include "CoreMinimal.h"
#include "WiseEyeEventMath.h"
class FJsonObject;

/** Frame-driven log-intensity event approximation, with independent cursors. */
class FWiseEyeEventCamera {
public:
    void Configure(bool Enabled,float On,float Off,int64 Refractory);
    void Process(const TArray<float>& Signal,int Width,int Height,double Time,int64 Frame,int64 Revision);
    TSharedPtr<FJsonObject> State() const;
    TSharedPtr<FJsonObject> Packet(int64 After,int32 Limit,bool Latest) const;
    int64 Revision() const;
private:
    mutable FCriticalSection Lock;
    WiseEyeEvents::Model Model;
    TArray<WiseEyeEvents::Event> Ring;
    bool Enabled=false;
    int64 Generation=0,Next=1,Frames=0,LastFrame=0,DroppedFrames=0;
    int32 Count=0,Write=0;
    double LastTime=-1,ActualHz=0;
};
