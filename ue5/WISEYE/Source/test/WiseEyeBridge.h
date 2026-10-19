#pragma once
#include "CoreMinimal.h"

class AWiseEyeDemo;
class FSocket;
class FJsonObject;

struct FWiseEyeClient
{
    FSocket* Socket = nullptr;
    TArray<uint8> Input;
    TArray<uint8> Output;
    int32 Sent = 0;
};

/** Bounded nonblocking TCP I/O; all actor access stays on the game thread. */
class FWiseEyeBridge
{
public:
    explicit FWiseEyeBridge(AWiseEyeDemo& InDemo) : Demo(InDemo) {}
    ~FWiseEyeBridge();
    bool Start(int32 Port,FString& Error);
    void Tick();
private:
    AWiseEyeDemo& Demo;
    FSocket* Listener = nullptr;
    TArray<FWiseEyeClient> Clients;
    double LastManualInput = 0;
    int64 VisibleFrameNumber = 0;
    int64 InfraredFrameNumber = 0;
    TSharedPtr<FJsonObject> State() const;
    TSharedPtr<FJsonObject> Execute(const TSharedPtr<FJsonObject>& Request);
    void Close(FWiseEyeClient& Client);
};
