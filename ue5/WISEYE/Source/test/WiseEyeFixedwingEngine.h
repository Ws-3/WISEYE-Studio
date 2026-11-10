#pragma once
#include "CoreMinimal.h"
#include "WiseEyeJSBSimAPI.h"

class FWiseEyeFixedwingEngine {
public:
    ~FWiseEyeFixedwingEngine();
    bool Reset(double Heading,double Speed,FString& Error);
    bool Step(double Dt,double Speed,double Bank,double Gamma,FString& Error);
    WiseEyeFDMState State{};
private:
    void* Aircraft=nullptr;
};
