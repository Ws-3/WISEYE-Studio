#include "WiseEyeDemo.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#if PLATFORM_WINDOWS
#include "Windows/WindowsHWrapper.h"
#endif

bool AWiseEyeDemo::SetSimulationWindowVisible(bool Visible) {
#if PLATFORM_WINDOWS
    struct FRequest {bool Visible;bool Found=false;} Request{Visible};
    ::EnumWindows([](HWND Window,LPARAM Data)->BOOL {
        auto& R=*reinterpret_cast<FRequest*>(Data);DWORD Pid=0;::GetWindowThreadProcessId(Window,&Pid);
        wchar_t Class[128]={};::GetClassNameW(Window,Class,128);
        if (Pid!=::GetCurrentProcessId() || !FString(Class).Contains(TEXT("UnrealWindow"))) return true;
        R.Found=true;
        if (R.Visible) {RECT Rect{};::GetWindowRect(Window,&Rect);if (Rect.left< -10000 || Rect.top< -10000) ::SetWindowPos(Window,nullptr,80,80,1280,720,SWP_NOZORDER|SWP_NOACTIVATE);}
        ::ShowWindow(Window,R.Visible?SW_RESTORE:SW_HIDE);return true;
    },reinterpret_cast<LPARAM>(&Request));
    if (Request.Found) {SimulationWindowVisible=Visible;SimulationWindowInitialized=true;}return Request.Found;
#else
    return false;
#endif
}
void AWiseEyeDemo::UpdateSimulationWindow() {
    if (!SimulationWindowInitialized && FParse::Param(FCommandLine::Get(),TEXT("WiseEyeHiddenWindow"))) SetSimulationWindowVisible(false);
}
