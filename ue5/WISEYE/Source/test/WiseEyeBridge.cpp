#include "WiseEyeBridge.h"
#include "WiseEyeDemo.h"
#include "Components/SceneComponent.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "IPAddress.h"
#include "HAL/PlatformTime.h"
#include "HAL/FileManager.h"

namespace
{
    constexpr int32 MaxMessage = 65536;
    TSharedPtr<FJsonObject> Reply(const FString& Id,const TSharedPtr<FJsonObject>& Payload,const FString& Code=TEXT(""),const FString& Message=TEXT(""))
    {
        auto R = MakeShared<FJsonObject>();
        R->SetNumberField(TEXT("version"),1);
        R->SetStringField(TEXT("request_id"),Id);
        R->SetStringField(TEXT("status"),Code.IsEmpty()?TEXT("ok"):TEXT("error"));
        R->SetObjectField(TEXT("payload"),Payload);
        if (!Code.IsEmpty())
        {
            auto E = MakeShared<FJsonObject>();
            E->SetStringField(TEXT("code"),Code);
            E->SetStringField(TEXT("message"),Message);
            R->SetObjectField(TEXT("error"),E);
        }
        return R;
    }
    TArray<TSharedPtr<FJsonValue>> Vector(const FVector& V)
    {
        return {MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)};
    }
}

void FWiseEyeBridge::Close(FWiseEyeClient& C)
{
    if (C.Socket)
    {
        C.Socket->Close();
        ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(C.Socket);
        C.Socket = nullptr;
    }
}
FWiseEyeBridge::~FWiseEyeBridge()
{
    for (auto& C : Clients) Close(C);
    if (Listener)
    {
        Listener->Close();
        ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Listener);
    }
    Demo.SetManualInput(0,0,0,0);
}
bool FWiseEyeBridge::Start(int32 Port,FString& Error)
{
    auto* S = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
    if (Port<1024 || Port>65535) { Error=TEXT("Invalid control port"); return false; }
    auto Address=S->CreateInternetAddr();
    bool Valid=false;
    Address->SetIp(TEXT("127.0.0.1"),Valid);
    Address->SetPort(Port);
    Listener=S->CreateSocket(NAME_Stream,TEXT("WISEYE control"),false);
    if (!Listener || !Valid || !Listener->SetNonBlocking(true) || !Listener->Bind(*Address) || !Listener->Listen(4))
    {
        Error=FString::Printf(TEXT("Cannot listen on 127.0.0.1:%d (socket error %d)"),Port,int32(S->GetLastErrorCode()));
        return false;
    }
    UE_LOG(LogTemp,Display,TEXT("WISEYE control listening on 127.0.0.1:%d"),Port);
    return true;
}
TSharedPtr<FJsonObject> FWiseEyeBridge::State() const
{
    auto R=MakeShared<FJsonObject>();
    R->SetStringField(TEXT("application"),TEXT("WISEYE Studio"));
    R->SetBoolField(TEXT("paused"),Demo.Paused);
    R->SetNumberField(TEXT("simulation_time_s"),Demo.SimulationTime);
    R->SetStringField(TEXT("flight_mode"),Demo.AutomaticFlight?TEXT("auto"):TEXT("manual"));
    R->SetBoolField(TEXT("tracking"),Demo.TrackingEnabled);
    R->SetBoolField(TEXT("rotors_running"),Demo.RotorsRunning);
    R->SetNumberField(TEXT("rotor_rpm"),Demo.RotorRPM);
    R->SetNumberField(TEXT("yaw_deg"),Demo.YawPivot->GetRelativeRotation().Yaw);
    R->SetNumberField(TEXT("pitch_deg"),Demo.PitchPivot->GetRelativeRotation().Pitch);
    R->SetNumberField(TEXT("pointing_error_deg"),Demo.PointingError);
    R->SetStringField(TEXT("sensor_mode"),Demo.InfraredMode?TEXT("infrared"):TEXT("visible"));
    R->SetStringField(TEXT("palette"),Demo.BlackHot?TEXT("black_hot"):TEXT("white_hot"));
    R->SetNumberField(TEXT("fov_deg"),Demo.FieldOfView);
    UTextureRenderTarget2D* Target=Demo.GetSensorTarget();
    R->SetNumberField(TEXT("width"),Target?Target->SizeX:0);
    R->SetNumberField(TEXT("height"),Target?Target->SizeY:0);
    R->SetArrayField(TEXT("drone_position_cm"),Vector(Demo.Drone->GetActorLocation()));
    R->SetStringField(TEXT("tracking_source"),TEXT("UE ground truth"));
    R->SetStringField(TEXT("thermal_model"),TEXT("synthetic normalized heat"));
    R->SetStringField(TEXT("last_export_path"),Demo.LastExportPath);
    return R;
}

TSharedPtr<FJsonObject> FWiseEyeBridge::Execute(const TSharedPtr<FJsonObject>& Request)
{
    FString Id,Command;
    double Version=0;
    auto Empty=MakeShared<FJsonObject>();
    Request->TryGetStringField(TEXT("request_id"),Id);
    if (Id.IsEmpty() || Id.Len()>128 || !Request->TryGetNumberField(TEXT("version"),Version) || Version!=1 || !Request->TryGetStringField(TEXT("command"),Command))
        return Reply(Id,Empty,TEXT("bad_request"),TEXT("version=1, request_id and command are required"));
    const TSharedPtr<FJsonObject>* P=nullptr;
    if (Request->HasField(TEXT("payload")) && !Request->TryGetObjectField(TEXT("payload"),P))
        return Reply(Id,Empty,TEXT("invalid_payload"),TEXT("payload must be an object"));
    TSharedPtr<FJsonObject> Args=P?*P:Empty;
    auto Fail=[&](const FString& Message) { return Reply(Id,Empty,TEXT("invalid_argument"),Message); };
    if (Command==TEXT("sim.ping") || Command==TEXT("sim.get_state")) return Reply(Id,State());
    if (Command==TEXT("sim.pause")) Demo.Paused=true;
    else if (Command==TEXT("sim.resume")) Demo.Paused=false;
    else if (Command==TEXT("sim.reset")) Demo.ResetSimulation();
    else if (Command==TEXT("gimbal.set_tracking") || Command==TEXT("rotors.set_enabled"))
    {
        bool Enabled=false;
        if (!Args->TryGetBoolField(TEXT("enabled"),Enabled)) return Fail(TEXT("enabled must be a boolean"));
        if (Command==TEXT("gimbal.set_tracking")) Demo.TrackingEnabled=Enabled;
        else Demo.RotorsRunning=Enabled;
    }
    else if (Command==TEXT("flight.set_mode"))
    {
        FString Mode;
        if (!Args->TryGetStringField(TEXT("mode"),Mode) || (Mode!=TEXT("auto") && Mode!=TEXT("manual"))) return Fail(TEXT("mode must be auto or manual"));
        if (Demo.AutomaticFlight!=(Mode==TEXT("auto"))) Demo.ToggleFlightMode();
    }
    else if (Command==TEXT("flight.set_input"))
    {
        if (Demo.AutomaticFlight) return Fail(TEXT("Manual input requires manual flight mode"));
        double F,R,U,Y;
        if (!Args->TryGetNumberField(TEXT("forward"),F) || !Args->TryGetNumberField(TEXT("right"),R) || !Args->TryGetNumberField(TEXT("up"),U) || !Args->TryGetNumberField(TEXT("yaw"),Y)) return Fail(TEXT("forward, right, up, yaw are required"));
        for (double Value : {F,R,U,Y}) if (!FMath::IsFinite(Value) || FMath::Abs(Value)>1) return Fail(TEXT("Manual inputs must be finite and within [-1,1]"));
        Demo.SetManualInput(float(F),float(R),float(U),float(Y));
        LastManualInput=FPlatformTime::Seconds();
    }
    else if (Command==TEXT("gimbal.set_angles"))
    {
        double Y,Pit;
        if (!Args->TryGetNumberField(TEXT("yaw_deg"),Y) || !Args->TryGetNumberField(TEXT("pitch_deg"),Pit) || !FMath::IsFinite(Y) || !FMath::IsFinite(Pit) || Y< -180 || Y>180 || Pit<Demo.MinPitch || Pit>Demo.MaxPitch) return Fail(TEXT("Angles exceed gimbal limits"));
        Demo.TrackingEnabled=false;
        Demo.YawPivot->SetRelativeRotation(FRotator(0,Y,0));
        Demo.PitchPivot->SetRelativeRotation(FRotator(Pit,0,0));
    }
    else if (Command==TEXT("camera.set_mode"))
    {
        FString Mode;
        if (!Args->TryGetStringField(TEXT("mode"),Mode) || (Mode!=TEXT("visible") && Mode!=TEXT("infrared"))) return Fail(TEXT("mode must be visible or infrared"));
        if (Mode==TEXT("infrared") && !Demo.ThermalInstance) return Fail(TEXT("IR material unavailable"));
        Demo.InfraredMode=Mode==TEXT("infrared");
        Demo.RefreshSensors();
    }
    else if (Command==TEXT("camera.set_palette"))
    {
        FString Palette;
        if (!Args->TryGetStringField(TEXT("palette"),Palette) || (Palette!=TEXT("white_hot") && Palette!=TEXT("black_hot"))) return Fail(TEXT("palette must be white_hot or black_hot"));
        Demo.BlackHot=Palette==TEXT("black_hot");
        Demo.RefreshSensors();
    }
    else if (Command==TEXT("camera.set_fov"))
    {
        double Fov;
        if (!Args->TryGetNumberField(TEXT("fov_deg"),Fov) || !FMath::IsFinite(Fov) || Fov<5 || Fov>120) return Fail(TEXT("fov_deg must be within [5,120]"));
        Demo.FieldOfView=float(Fov);
        Demo.RefreshSensors();
    }
    else if (Command==TEXT("camera.capture"))
    {
        Demo.ExportFrame();
        if (Demo.LastExportPath.IsEmpty() || !IFileManager::Get().FileExists(*Demo.LastExportPath)) return Reply(Id,Empty,TEXT("capture_failed"),TEXT("PNG export failed"));
        auto R=State();
        R->SetStringField(TEXT("frame_path"),Demo.LastExportPath);
        return Reply(Id,R);
    }
    else return Reply(Id,Empty,TEXT("unknown_command"),TEXT("Command is not supported"));
    return Reply(Id,State());
}

void FWiseEyeBridge::Tick()
{
    if (!Demo.BridgeReady) return;
    if (LastManualInput>0 && FPlatformTime::Seconds()-LastManualInput>.35)
    {
        Demo.SetManualInput(0,0,0,0);
        LastManualInput=0;
    }
    bool Pending=false;
    if (Listener->HasPendingConnection(Pending) && Pending)
    {
        FSocket* Socket=Listener->Accept(TEXT("WISEYE client"));
        if (Socket)
        {
            Socket->SetNonBlocking(true);
            Socket->SetNoDelay(true);
            FWiseEyeClient C; C.Socket=Socket;
            if (Clients.Num()<4) Clients.Add(MoveTemp(C));
            else Close(C);
        }
    }
    for (int32 I=Clients.Num()-1; I>=0; --I)
    {
        auto& C=Clients[I];
        if (C.Sent>0)
        {
            C.Output.RemoveAt(0,C.Sent,EAllowShrinking::No);
            C.Sent=0;
        }
        bool Alive=true;
        int32 Budget=8192;
        while (Budget>0 && C.Socket->Wait(ESocketWaitConditions::WaitForRead,FTimespan::Zero()))
        {
            uint8 Buffer[2048]; int32 Count=0;
            if (!C.Socket->Recv(Buffer,sizeof(Buffer),Count) || Count<=0) { Alive=false; break; }
            C.Input.Append(Buffer,Count); Budget-=Count;
            if (C.Input.Num()>MaxMessage) { Alive=false; break; }
        }
        for (int32 Messages=0; Alive && Messages<8; ++Messages)
        {
            int32 End=C.Input.Find(uint8('\n'));
            if (End==INDEX_NONE) break;
            FUTF8ToTCHAR Text(reinterpret_cast<const ANSICHAR*>(C.Input.GetData()),End);
            FString Line(Text.Length(),Text.Get());
            C.Input.RemoveAt(0,End+1,EAllowShrinking::No);
            TSharedPtr<FJsonObject> Request;
            auto Reader=TJsonReaderFactory<>::Create(Line);
            auto Response=FJsonSerializer::Deserialize(Reader,Request) && Request.IsValid() ? Execute(Request) : Reply(TEXT(""),MakeShared<FJsonObject>(),TEXT("bad_json"),TEXT("Expected a JSON object"));
            FString Encoded;
            FJsonSerializer::Serialize(Response.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Encoded));
            Encoded+=TEXT("\n");
            FTCHARToUTF8 Utf8(*Encoded);
            C.Output.Append(reinterpret_cast<const uint8*>(Utf8.Get()),Utf8.Length());
            if (C.Output.Num()-C.Sent>MaxMessage*4) Alive=false;
        }
        if (Alive && C.Sent<C.Output.Num())
        {
            int32 Count=0;
            if (C.Socket->Send(C.Output.GetData()+C.Sent,C.Output.Num()-C.Sent,Count)) C.Sent+=Count;
            else if (ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->GetLastErrorCode()!=SE_EWOULDBLOCK) Alive=false;
            if (C.Sent==C.Output.Num()) { C.Output.Reset(); C.Sent=0; }
        }
        if (!Alive)
        {
            Close(C);
            Clients.RemoveAt(I);
        }
    }
}
