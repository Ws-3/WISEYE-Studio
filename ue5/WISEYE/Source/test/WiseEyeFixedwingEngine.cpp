#include "WiseEyeFixedwingEngine.h"
#include "HAL/PlatformProcess.h"
#include "Misc/Paths.h"
namespace {
using FCreate=decltype(&WiseEyeFDMCreate);
using FReset=decltype(&WiseEyeFDMReset);
using FStep=decltype(&WiseEyeFDMStep);
using FDestroy=decltype(&WiseEyeFDMDestroy);
struct FAPI {
    void* Library=nullptr;FCreate Create=nullptr;FReset Reset=nullptr;FStep Step=nullptr;FDestroy Destroy=nullptr;
    FAPI() {
        FString Path=FPaths::Combine(FPaths::ProjectDir(),TEXT("ThirdParty/JSBSim/bin/WiseEyeJSBSim.dll"));
        if (!FPaths::FileExists(Path)) Path=FPaths::Combine(FPlatformProcess::BaseDir(),TEXT("WiseEyeJSBSim.dll"));
        Library=FPlatformProcess::GetDllHandle(*Path);
        if (!Library) return;
        Create=reinterpret_cast<FCreate>(FPlatformProcess::GetDllExport(Library,TEXT("WiseEyeFDMCreate")));
        Reset=reinterpret_cast<FReset>(FPlatformProcess::GetDllExport(Library,TEXT("WiseEyeFDMReset")));
        Step=reinterpret_cast<FStep>(FPlatformProcess::GetDllExport(Library,TEXT("WiseEyeFDMStep")));
        Destroy=reinterpret_cast<FDestroy>(FPlatformProcess::GetDllExport(Library,TEXT("WiseEyeFDMDestroy")));
    }
};
FAPI& API(){static FAPI Instance;return Instance;}
}
FWiseEyeFixedwingEngine::~FWiseEyeFixedwingEngine(){if (Aircraft && API().Destroy) API().Destroy(Aircraft);}
bool FWiseEyeFixedwingEngine::Reset(double Heading,double Speed,FString& Error) {
    auto& A=API();
    if (!A.Create || !A.Reset || !A.Step || !A.Destroy) {Error=TEXT("JSBSim native runtime is unavailable; run Build-JSBSim.ps1");return false;}
    ANSICHAR Message[2048]={};
    if (!Aircraft) {
        const FString Root=FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectDir(),TEXT("ThirdParty/JSBSim/Resources")));
        Aircraft=A.Create(TCHAR_TO_UTF8(*Root),Message,2048);
    }
    if (!Aircraft || !A.Reset(Aircraft,Heading,Speed,Message,2048)) {Error=UTF8_TO_TCHAR(Message);return false;}
    State={};State.speed=Speed;State.yaw=Heading;State.pitch=State.alpha=3;
    return true;
}
bool FWiseEyeFixedwingEngine::Step(double Dt,double Speed,double Bank,double Gamma,FString& Error) {
    ANSICHAR Message[2048]={};
    if (!Aircraft || !API().Step(Aircraft,Dt,Speed,Bank,Gamma,&State,Message,2048)) {Error=UTF8_TO_TCHAR(Message);return false;}
    return true;
}
