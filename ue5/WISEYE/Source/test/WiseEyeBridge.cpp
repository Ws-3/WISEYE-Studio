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
#include "Misc/Base64.h"
#include "Camera/CameraActor.h"
#include "Materials/MaterialInterface.h"

namespace
{
    constexpr int32 MaxRequestMessage = 65536;
    constexpr int32 MaxResponseMessage = 16*1024*1024;
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
    if (!Listener || !Valid || !Listener->SetNonBlocking(true) || !Listener->Bind(*Address) || !Listener->Listen(24))
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
    R->SetStringField(TEXT("scene_id"),Demo.SceneId);
    R->SetStringField(TEXT("run_id"),Demo.PlaySessionId);
    auto Streams=MakeShared<FJsonObject>();
    for (bool Infrared : {false,true})
    {
        int64 Sequence=0,Completed=0; double CaptureTime=0;
        Demo.GetStreamStatistics(Infrared,Sequence,Completed,CaptureTime);
        auto Stats=MakeShared<FJsonObject>();
        Stats->SetNumberField(TEXT("frame_seq"),Sequence);
        Stats->SetNumberField(TEXT("completed_frames"),Completed);
        Stats->SetNumberField(TEXT("readback_queued_ue_monotonic_s"),CaptureTime);
        Stats->SetNumberField(TEXT("cache_age_ms"),CaptureTime>0?(FPlatformTime::Seconds()-CaptureTime)*1000:0);
        Streams->SetObjectField(Infrared?TEXT("CH2"):TEXT("CH1"),Stats);
    }
    R->SetObjectField(TEXT("streams"),Streams);
    R->SetArrayField(TEXT("initial_drone_position_cm"),Vector(Demo.FlightOrigin));
    R->SetArrayField(TEXT("gimbal_position_cm"),Vector(Demo.GetActorLocation()));
    R->SetStringField(TEXT("drone_id"),Demo.DroneId);
    R->SetStringField(TEXT("gimbal_id"),Demo.GimbalId);
    R->SetArrayField(TEXT("devices"),Demo.DeviceInventory());
    R->SetStringField(TEXT("tracking_target"),Demo.TrackingTargetId);
    R->SetStringField(TEXT("observer_mode"),Demo.FleetRoot?Demo.FleetRoot->ObserverMode:Demo.ObserverMode);
    auto Placement=MakeShared<FJsonObject>();
    const auto& PlacementDemo=Demo.FleetRoot?*Demo.FleetRoot:Demo;
    Placement->SetBoolField(TEXT("active"),PlacementDemo.PlacementActive);
    Placement->SetBoolField(TEXT("has_result"),PlacementDemo.PlacementHasResult);
    Placement->SetStringField(TEXT("device_id"),PlacementDemo.PlacementDevice);
    Placement->SetStringField(TEXT("request_token"),PlacementDemo.PlacementToken);
    Placement->SetStringField(TEXT("error"),PlacementDemo.PlacementError);
    Placement->SetNumberField(TEXT("sequence"),PlacementDemo.PlacementSequence);
    Placement->SetArrayField(TEXT("position_cm"),Vector(PlacementDemo.PlacementPosition));
    Placement->SetArrayField(TEXT("surface_cm"),Vector(PlacementDemo.PlacementSurface));
    R->SetObjectField(TEXT("placement"),Placement);
    if (Demo.FreeObserver) R->SetArrayField(TEXT("observer_position_cm"),Vector(Demo.FreeObserver->GetActorLocation()));
    R->SetStringField(TEXT("input_mode"),Demo.FleetRoot?Demo.FleetRoot->ControlMode:Demo.ControlMode);
    R->SetNumberField(TEXT("pitch_min_deg"),Demo.MinPitch);
    R->SetNumberField(TEXT("pitch_max_deg"),Demo.MaxPitch);
    R->SetNumberField(TEXT("lidar_horizontal_fov_deg"),Demo.LidarHorizontalFov);
    R->SetNumberField(TEXT("lidar_vertical_fov_deg"),Demo.LidarVerticalFov);
    R->SetNumberField(TEXT("lidar_scan_rate_hz"),Demo.LidarScanRateHz);
    R->SetNumberField(TEXT("lidar_range_m"),Demo.LidarRangeMeters);
    R->SetStringField(TEXT("pending_scene"),Demo.PendingScene);
    R->SetBoolField(TEXT("paused"),Demo.Paused);
    R->SetNumberField(TEXT("simulation_time_s"),Demo.SimulationTime);
    R->SetStringField(TEXT("flight_mode"),Demo.AutomaticFlight?TEXT("auto"):TEXT("manual"));
    R->SetStringField(TEXT("flight_backend"),Demo.FlightBackend==EWiseEyeFlightBackend::ProjectAirSim?TEXT("projectairsim"):TEXT("kinematic"));
    R->SetStringField(TEXT("drone_model"),Demo.DroneModel);
    R->SetArrayField(TEXT("drone_models_available"),{
        MakeShared<FJsonValueString>(TEXT("mavic3")),
        MakeShared<FJsonValueString>(TEXT("avata"))});
    R->SetBoolField(TEXT("dynamics_connected"),Demo.DynamicsConnected);
    R->SetStringField(TEXT("dynamics_actor"),IsValid(Demo.DynamicsSource)?Demo.DynamicsSource->GetName():TEXT(""));
    R->SetBoolField(TEXT("tracking"),Demo.TrackingEnabled);
    R->SetBoolField(TEXT("rotors_running"),Demo.RotorsRunning);
    R->SetNumberField(TEXT("rotor_rpm"),Demo.RotorRPM);
    TArray<TSharedPtr<FJsonValue>> RPMs; for (float RPM:Demo.MotorRPMs) RPMs.Add(MakeShared<FJsonValueNumber>(RPM));
    R->SetArrayField(TEXT("motor_rpm"),RPMs);
    R->SetStringField(TEXT("rotor_source"),Demo.FlightBackend==EWiseEyeFlightBackend::ProjectAirSim?TEXT("airsim_rad_s"):TEXT("kinematic"));
    R->SetBoolField(TEXT("rotor_telemetry_fresh"),Demo.RotorTelemetryValid && FPlatformTime::Seconds()-Demo.RotorTelemetryTime<1.5);
    R->SetNumberField(TEXT("tick_seq"),Demo.TickSequence);
    const auto& Root=Demo.FleetRoot?*Demo.FleetRoot:Demo;
    if (Root.RuntimeStatus) R->SetObjectField(TEXT("runtime_hardware"),Root.RuntimeStatus);
    auto& EnvironmentRoot=Demo.FleetRoot?*Demo.FleetRoot:Demo;
    R->SetObjectField(TEXT("environment"),EnvironmentRoot.EnvironmentState());
    R->SetStringField(TEXT("performance_profile"),Root.PerformanceProfile);
    R->SetNumberField(TEXT("visible_capture_hz"),Root.VisibleCaptureHz);
    R->SetNumberField(TEXT("infrared_capture_hz"),Root.InfraredCaptureHz);
    R->SetNumberField(TEXT("observer_capture_hz"),Root.ObserverCaptureHz);
    R->SetNumberField(TEXT("yaw_deg"),Demo.YawPivot->GetRelativeRotation().Yaw);
    R->SetNumberField(TEXT("pitch_deg"),Demo.PitchPivot->GetRelativeRotation().Pitch);
    R->SetNumberField(TEXT("pointing_error_deg"),Demo.PointingError);
    R->SetStringField(TEXT("sensor_mode"),Demo.InfraredMode?TEXT("infrared"):TEXT("visible"));
    R->SetStringField(TEXT("active_sensor"),Demo.ActiveSensor);
    R->SetArrayField(TEXT("available_sensors"),{
        MakeShared<FJsonValueString>(TEXT("visible")),
        MakeShared<FJsonValueString>(TEXT("infrared")),
        MakeShared<FJsonValueString>(TEXT("lidar"))});
    auto Sensors=MakeShared<FJsonObject>();
    for (const FString Sensor : {FString(TEXT("visible")),FString(TEXT("infrared")),FString(TEXT("lidar"))})
    {
        auto Settings=MakeShared<FJsonObject>();
        const bool IR=Sensor==TEXT("infrared"), Lidar=Sensor==TEXT("lidar");
        Settings->SetBoolField(TEXT("enabled"),Lidar?Demo.LidarEnabled:IR?Demo.InfraredEnabled:Demo.VisibleEnabled);
        if (!Lidar) Settings->SetNumberField(TEXT("fov_deg"),IR?Demo.InfraredFOV:Demo.VisibleFOV);
        if (IR) {
            Settings->SetStringField(TEXT("palette"),Demo.BlackHot?TEXT("black_hot"):TEXT("white_hot")); Settings->SetNumberField(TEXT("noise"),Demo.ThermalNoise);
            const bool Experimental=Demo.ThermalMaterial && Demo.ThermalMaterial->GetName()==TEXT("M_IR_Experimental");
            Settings->SetStringField(TEXT("thermal_profile"),Experimental?Demo.ThermalProfile:TEXT("legacy"));
            Settings->SetBoolField(TEXT("enhanced_available"),Experimental);
            Settings->SetNumberField(TEXT("blur_px"),Demo.ThermalBlurPixels);
            Settings->SetNumberField(TEXT("contrast"),Demo.ThermalContrast);
            Settings->SetNumberField(TEXT("background_detail"),Demo.ThermalBackgroundDetail);
        }
        if (Lidar) {
            Settings->SetNumberField(TEXT("horizontal_fov_deg"),Demo.LidarHorizontalFov);
            Settings->SetNumberField(TEXT("vertical_fov_deg"),Demo.LidarVerticalFov);
            Settings->SetNumberField(TEXT("range_m"),Demo.LidarRangeMeters);
            Settings->SetNumberField(TEXT("scan_rate_hz"),Demo.LidarScanRateHz);
        }
        Sensors->SetObjectField(Sensor,Settings);
    }
    R->SetObjectField(TEXT("sensors"),Sensors);
    R->SetStringField(TEXT("palette"),Demo.BlackHot?TEXT("black_hot"):TEXT("white_hot"));
    R->SetNumberField(TEXT("fov_deg"),Demo.FieldOfView);
    UTextureRenderTarget2D* Target=Demo.GetSensorTarget();
    R->SetNumberField(TEXT("width"),Target?Target->SizeX:0);
    R->SetNumberField(TEXT("height"),Target?Target->SizeY:0);
    R->SetArrayField(TEXT("drone_position_cm"),Vector(Demo.Drone->GetActorLocation()));
    R->SetStringField(TEXT("tracking_source"),TEXT("UE ground truth"));
    R->SetStringField(TEXT("thermal_model"),TEXT("synthetic normalized heat"));
    R->SetStringField(TEXT("last_export_path"),Demo.LastExportPath);
    R->SetBoolField(TEXT("lidar_enabled"),Demo.LidarEnabled);
    R->SetNumberField(TEXT("lidar_hits"),Demo.LidarHitCount);
    R->SetNumberField(TEXT("lidar_rays"),Demo.LastLidarRangesMeters.Num());
    R->SetNumberField(TEXT("lidar_nearest_m"),Demo.LidarNearestRangeMeters);
    R->SetStringField(TEXT("lidar_last_export_path"),Demo.LastLidarExportPath);
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
    if (!Demo.FleetChild && Args->HasField(TEXT("device_id")))
    {
        FString DeviceId;
        if (!Args->TryGetStringField(TEXT("device_id"),DeviceId)) return Fail(TEXT("device_id must be a string"));
        AWiseEyeDemo* Target=Demo.FindDevice(DeviceId);
        if (!Target) return Fail(TEXT("Unknown device_id"));
        const bool GimbalCommand=Command.StartsWith(TEXT("gimbal.")) || Command.StartsWith(TEXT("sensor.")) || Command.StartsWith(TEXT("camera."));
        const bool DroneCommand=Command.StartsWith(TEXT("drone.")) || Command.StartsWith(TEXT("rotors.")) || Command.StartsWith(TEXT("flight.")) || Command==TEXT("sim.pause") || Command==TEXT("sim.resume") || Command==TEXT("sim.reset");
        if (GimbalCommand && DeviceId!=Target->GimbalId) return Fail(TEXT("Command requires a gimbal device_id"));
        if (DroneCommand && (!Target->OwnsDrone || DeviceId!=Target->DroneId)) return Fail(TEXT("Command requires a drone device_id"));
        if (Target!=&Demo && Command!=TEXT("flight.get_local_control") && (GimbalCommand || DroneCommand || Command==TEXT("sim.get_state") || Command==TEXT("sim.ping"))) return Target->DispatchDevice(Request);
    }
    if (Command==TEXT("input.select_drone") || Command==TEXT("input.select_gimbal")) {
        FString TargetId;const bool Drone=Command==TEXT("input.select_drone");
        if (!Args->TryGetStringField(Drone?TEXT("drone_id"):TEXT("gimbal_id"),TargetId)) return Fail(TEXT("Target ID required"));
        auto* Target=Demo.FindDevice(TargetId);
        if (!Target || (Drone?(!Target->OwnsDrone || Target->DroneId!=TargetId):Target->GimbalId!=TargetId)) return Fail(TEXT("Unknown target device"));
        if (Drone) { Demo.LocalFlightInput=FVector::ZeroVector;Demo.LocalYawInput=0;Demo.LocalFlightInputDirty=true;Demo.ControlledDroneId=TargetId; }
        else { for (auto Rig : Demo.FleetRigs) Rig->RemoteGimbalInput=FVector2D::ZeroVector;Demo.ControlledGimbalId=TargetId; }
        if (Demo.ObserverMode==TEXT("gimbal") || Demo.ObserverMode==TEXT("follow")) Demo.SetObserverMode(Demo.ObserverMode);
        return Reply(Id,State());
    }
    if (Command==TEXT("gimbal.set_target")) {
        FString TargetId;if (!Args->TryGetStringField(TEXT("drone_id"),TargetId)) return Fail(TEXT("drone_id is required"));
        auto* Target=Demo.FindDevice(TargetId);if (!Target || !Target->OwnsDrone || Target->DroneId!=TargetId) return Fail(TEXT("Unknown drone target"));
        Demo.TrackingTargetId=TargetId;Demo.TrackingDrone=Target->Drone;return Reply(Id,State());
    }
    if (Command==TEXT("sim.ping") || Command==TEXT("sim.get_state")) return Reply(Id,State());
    if (Command==TEXT("environment.configure") || Command==TEXT("environment.reset")) {
        auto& Root=Demo.FleetRoot?*Demo.FleetRoot:Demo;
        if (Command==TEXT("environment.reset")) Root.ResetEnvironment();
        else {
            bool Override=false;double Hour=0,Fog=0,Rain=0;
            if (!Args->TryGetBoolField(TEXT("time_override"),Override) || !Args->TryGetNumberField(TEXT("hour"),Hour) ||
                !Args->TryGetNumberField(TEXT("fog"),Fog) || !Args->TryGetNumberField(TEXT("rain"),Rain) ||
                !FMath::IsFinite(Hour) || Hour<0 || Hour>=24 || !FMath::IsFinite(Fog) || Fog<0 || Fog>1 || !FMath::IsFinite(Rain) || Rain<0 || Rain>1)
                return Fail(TEXT("Environment requires time_override, hour [0,24), fog/rain [0,1]"));
            FString Error;if (!Root.ConfigureEnvironment(Override,Hour,Fog,Rain,Error)) return Fail(Error);
        }
        return Reply(Id,State());
    }
    if (Command==TEXT("sim.set_performance_profile")) {
        FString Profile;
        if (!Args->TryGetStringField(TEXT("profile"),Profile) || (Profile!=TEXT("quality") && Profile!=TEXT("balanced") && Profile!=TEXT("economy"))) return Fail(TEXT("profile must be quality, balanced or economy"));
        Demo.SetPerformanceProfile(Profile); return Reply(Id,State());
    }
    if (Command==TEXT("rotors.sync_state")) {
        const TArray<TSharedPtr<FJsonValue>>* RPMs=nullptr;
        if (!Args->TryGetArrayField(TEXT("rpm"),RPMs) || RPMs->Num()!=4) return Fail(TEXT("rpm must contain four motor speeds"));
        TArray<float> Values; for (const auto& Value:*RPMs) { double RPM=0; if (!Value->TryGetNumber(RPM) || !FMath::IsFinite(RPM) || RPM<0 || RPM>30000) return Fail(TEXT("rpm must be finite in [0,30000]")); Values.Add(RPM); }
        bool Fresh=false; if (!Args->TryGetBoolField(TEXT("fresh"),Fresh)) return Fail(TEXT("fresh boolean required"));
        Demo.MotorRPMs=Values; Demo.RotorTelemetryTime=FPlatformTime::Seconds(); Demo.RotorTelemetryValid=Fresh;
        return Reply(Id,State());
    }
    if (Command==TEXT("gimbal.get_capabilities")) {
        auto R=State(); auto C=MakeShared<FJsonObject>();
        C->SetStringField(TEXT("angle_unit"),TEXT("degree")); C->SetNumberField(TEXT("yaw_min"),-180); C->SetNumberField(TEXT("yaw_max"),180);
        C->SetNumberField(TEXT("pitch_min"),Demo.MinPitch); C->SetNumberField(TEXT("pitch_max"),Demo.MaxPitch);
        C->SetNumberField(TEXT("yaw_rate_deg_s"),30); C->SetNumberField(TEXT("pitch_rate_deg_s"),20); C->SetNumberField(TEXT("input_watchdog_ms"),300);
        R->SetObjectField(TEXT("gimbal_capabilities"),C); return Reply(Id,R);
    }
    if (Command.StartsWith(TEXT("placement.")))
    {
        FString Scene,Token;
        if (!Args->TryGetStringField(TEXT("scene_id"),Scene) || Scene!=Demo.SceneId ||
            !Args->TryGetStringField(TEXT("request_token"),Token) || Token.IsEmpty() || Token.Len()>64)
            return Fail(TEXT("Current scene_id and a request_token up to 64 characters are required"));
        if (Command==TEXT("placement.cancel"))
        {
            if (Token!=Demo.PlacementToken) return Fail(TEXT("Placement request no longer current"));
            Demo.PlacementError=TEXT("Placement cancelled");
            Demo.PlacementHasResult=false;
            Demo.CancelPlacement();
        }
        else if (Command==TEXT("placement.begin") || Command==TEXT("placement.snap"))
        {
            FString Device,Error; double Clearance=0;
            if (!Args->TryGetStringField(TEXT("device_id"),Device) || !Args->TryGetNumberField(TEXT("clearance_cm"),Clearance) ||
                !FMath::IsFinite(Clearance) || Clearance<0 || Clearance>1000)
                return Fail(TEXT("device_id and clearance_cm within [0,1000] are required"));
            if (Command==TEXT("placement.begin"))
            {
                if (!Demo.BeginPlacement(Device,Token,Clearance,Error)) return Fail(Error);
            }
            else
            {
                const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
                if (!Args->TryGetArrayField(TEXT("position_cm"),Values) || Values->Num()!=3) return Fail(TEXT("position_cm requires three finite coordinates"));
                double Coordinates[3];
                for (int32 I=0;I<3;++I) if (!(*Values)[I]->TryGetNumber(Coordinates[I]) || !FMath::IsFinite(Coordinates[I]) || FMath::Abs(Coordinates[I])>1e7)
                    return Fail(TEXT("position_cm requires three finite coordinates within world limits"));
                if (!Demo.SnapPlacement(Device,Token,FVector(Coordinates[0],Coordinates[1],Coordinates[2]),Clearance,Error)) return Fail(Error);
            }
        }
        else return Reply(Id,Empty,TEXT("unknown_command"),TEXT("Unknown placement command"));
        return Reply(Id,State());
    }
    if (Command==TEXT("observer.set_mode") || Command==TEXT("input.set_mode"))
    {
        FString Mode;
        if (!Args->TryGetStringField(TEXT("mode"),Mode)) return Fail(TEXT("mode is required"));
        const bool Success=Command==TEXT("observer.set_mode")?Demo.SetObserverMode(Mode):Demo.SetControlMode(Mode);
        if (!Success) return Fail(TEXT("Unsupported mode or unavailable view"));
        return Reply(Id,State());
    }
    if (Command==TEXT("gimbal.set_input") || Command==TEXT("observer.set_input"))
    {
        double X=0,Y=0,Z=0,Yaw=0,Pitch=0;
        if (Command==TEXT("gimbal.set_input")) {
            if (!Args->TryGetNumberField(TEXT("yaw"),X) || !Args->TryGetNumberField(TEXT("pitch"),Y) || !FMath::IsFinite(X) || !FMath::IsFinite(Y) || FMath::Abs(X)>1 || FMath::Abs(Y)>1)
                return Fail(TEXT("yaw and pitch must be within [-1,1]"));
            if ((Demo.FleetRoot?Demo.FleetRoot->ControlMode:Demo.ControlMode)!=TEXT("gimbal") && (X!=0 || Y!=0)) return Fail(TEXT("Select gimbal input mode first"));
            Demo.RemoteGimbalInput=FVector2D(X,Y); Demo.GimbalInputTime=FPlatformTime::Seconds();
        } else {
            if (!Args->TryGetNumberField(TEXT("forward"),X) || !Args->TryGetNumberField(TEXT("right"),Y) || !Args->TryGetNumberField(TEXT("up"),Z) || !Args->TryGetNumberField(TEXT("yaw_deg"),Yaw) || !Args->TryGetNumberField(TEXT("pitch_deg"),Pitch)) return Fail(TEXT("All observer inputs required"));
            for (double V : {X,Y,Z,Yaw,Pitch}) if (!FMath::IsFinite(V)) return Fail(TEXT("Inputs must be finite"));
            if (FMath::Abs(X)>1 || FMath::Abs(Y)>1 || FMath::Abs(Z)>1 || FMath::Abs(Yaw)>90 || FMath::Abs(Pitch)>90) return Fail(TEXT("Observer input exceeds limits"));
            if (Demo.ControlMode!=TEXT("observer") || Demo.ObserverMode!=TEXT("free") || !Demo.FreeObserver) return Fail(TEXT("Select observer input and free view first"));
            Demo.RemoteObserverInput=FVector(X,Y,Z); Demo.ObserverInputTime=FPlatformTime::Seconds();
            auto Rotation=Demo.FreeObserver->GetActorRotation(); Rotation.Yaw+=Yaw; Rotation.Pitch=FMath::Clamp(Rotation.Pitch+Pitch,-85.,85.); Demo.FreeObserver->SetActorRotation(Rotation);
        }
        return Reply(Id,State());
    }
    if (Command==TEXT("sensor.configure"))
    {
        FString Sensor,Palette; bool Enabled=false;
        if (!Args->TryGetStringField(TEXT("sensor"),Sensor) || !Args->TryGetBoolField(TEXT("enabled"),Enabled)) return Fail(TEXT("sensor and enabled required"));
        if (Sensor==TEXT("visible") || Sensor==TEXT("infrared")) {
            double Fov,Noise=0;
            if (!Args->TryGetNumberField(TEXT("fov_deg"),Fov) || !FMath::IsFinite(Fov) || Fov<5 || Fov>120) return Fail(TEXT("fov_deg must be within [5,120]"));
            if (Sensor==TEXT("infrared")) {
                if (!Args->TryGetStringField(TEXT("palette"),Palette) || (Palette!=TEXT("white_hot") && Palette!=TEXT("black_hot")) || !Args->TryGetNumberField(TEXT("noise"),Noise) || !FMath::IsFinite(Noise) || Noise<0 || Noise>1) return Fail(TEXT("Invalid infrared palette/noise"));
                FString Profile=Demo.ThermalProfile;
                double Blur=Demo.ThermalBlurPixels,Contrast=Demo.ThermalContrast,Detail=Demo.ThermalBackgroundDetail;
                if (Args->HasField(TEXT("thermal_profile")) && (!Args->TryGetStringField(TEXT("thermal_profile"),Profile) || (Profile!=TEXT("legacy") && Profile!=TEXT("enhanced")))) return Fail(TEXT("Invalid thermal_profile"));
                auto OptionalNumber=[&](const TCHAR* Key,double& Value,double Low,double High) {
                    return !Args->HasField(Key) || (Args->TryGetNumberField(Key,Value) && FMath::IsFinite(Value) && Value>=Low && Value<=High);
                };
                if (!OptionalNumber(TEXT("blur_px"),Blur,0,2) || !OptionalNumber(TEXT("contrast"),Contrast,.3,3) || !OptionalNumber(TEXT("background_detail"),Detail,0,1)) return Fail(TEXT("Invalid thermal appearance parameters"));
                if (Profile==TEXT("enhanced") && (!Demo.ThermalMaterial || Demo.ThermalMaterial->GetName()!=TEXT("M_IR_Experimental"))) return Fail(TEXT("Enhanced infrared material is not installed"));
                Demo.ThermalProfile=Profile; Demo.ThermalBlurPixels=Blur; Demo.ThermalContrast=Contrast; Demo.ThermalBackgroundDetail=Detail;
                Demo.InfraredEnabled=Enabled; Demo.InfraredFOV=Fov; Demo.BlackHot=Palette==TEXT("black_hot"); Demo.ThermalNoise=Noise;
            } else { Demo.VisibleEnabled=Enabled; Demo.VisibleFOV=Fov; }
            Demo.RefreshSensors();
        } else if (Sensor==TEXT("lidar")) {
            double H,V,R,Rate;
            if (!Args->TryGetNumberField(TEXT("horizontal_fov_deg"),H) || !Args->TryGetNumberField(TEXT("vertical_fov_deg"),V) || !Args->TryGetNumberField(TEXT("range_m"),R) || !Args->TryGetNumberField(TEXT("scan_rate_hz"),Rate)) return Fail(TEXT("All lidar parameters required"));
            if (!FMath::IsFinite(H) || H<.1 || H>60 || !FMath::IsFinite(V) || V<.1 || V>60 || !FMath::IsFinite(R) || R<1 || R>1000 || !FMath::IsFinite(Rate) || Rate<.05 || Rate>10) return Fail(TEXT("Invalid lidar parameters"));
            Demo.LidarHorizontalFov=H; Demo.LidarVerticalFov=V; Demo.LidarRangeMeters=R; Demo.LidarScanRateHz=Rate; Demo.LidarEnabled=Enabled;
            if (Enabled) Demo.ScanLidar(); else { Demo.LastLidarPointsWorldCm.Reset(); Demo.LidarHitCount=0; }
        } else return Fail(TEXT("Unknown sensor"));
        return Reply(Id,State());
    }
    if (Command==TEXT("flight.get_local_control"))
    {
        auto R=MakeShared<FJsonObject>();
        R->SetStringField(TEXT("play_session_id"),Demo.PlaySessionId);
        R->SetStringField(TEXT("controlled_drone_id"),Demo.ControlledDroneId);
        R->SetBoolField(TEXT("dynamics_connected"),Demo.DynamicsConnected);
        TArray<TSharedPtr<FJsonValue>> Commands;
        for (const FString& C : Demo.LocalFlightCommands) Commands.Add(MakeShared<FJsonValueString>(C));
        R->SetArrayField(TEXT("commands"),Commands);
        Demo.LocalFlightCommands.Reset();
        R->SetBoolField(TEXT("input_dirty"),Demo.LocalFlightInputDirty);
        R->SetNumberField(TEXT("forward"),Demo.LocalFlightInput.X);
        R->SetNumberField(TEXT("right"),Demo.LocalFlightInput.Y);
        R->SetNumberField(TEXT("up"),Demo.LocalFlightInput.Z);
        R->SetNumberField(TEXT("yaw"),Demo.LocalYawInput);
        Demo.LocalFlightInputDirty=false;
        return Reply(Id,R);
    }
    if (Command==TEXT("flight.sync_state"))
    {
        FString Mode; bool Paused=false;
        if (!Args->TryGetStringField(TEXT("mode"),Mode) || (Mode!=TEXT("auto") && Mode!=TEXT("manual")) || !Args->TryGetBoolField(TEXT("paused"),Paused))
            return Fail(TEXT("mode and paused are required"));
        Demo.AutomaticFlight=Mode==TEXT("auto");
        Demo.Paused=Paused;
        return Reply(Id,State());
    }
    if (Command==TEXT("sim.load_scene"))
    {
        FString IdToLoad,Error;
        if (!Args->TryGetStringField(TEXT("scene_id"),IdToLoad) || !Demo.RequestScene(IdToLoad,Error))
            return Fail(Error.IsEmpty()?TEXT("scene_id is required"):Error);
    }
    else if (Command==TEXT("sim.pause")) Demo.Paused=true;
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
        if (Demo.FlightBackend==EWiseEyeFlightBackend::ProjectAirSim) return Fail(TEXT("Project AirSim owns flight control; use the WISEYE Project AirSim runner"));
        if (Demo.AutomaticFlight) return Fail(TEXT("Manual input requires manual flight mode"));
        double F,R,U,Y;
        if (!Args->TryGetNumberField(TEXT("forward"),F) || !Args->TryGetNumberField(TEXT("right"),R) || !Args->TryGetNumberField(TEXT("up"),U) || !Args->TryGetNumberField(TEXT("yaw"),Y)) return Fail(TEXT("forward, right, up, yaw are required"));
        for (double Value : {F,R,U,Y}) if (!FMath::IsFinite(Value) || FMath::Abs(Value)>1) return Fail(TEXT("Manual inputs must be finite and within [-1,1]"));
        Demo.SetManualInput(float(F),float(R),float(U),float(Y));
        LastManualInput=FPlatformTime::Seconds();
    }
    else if (Command==TEXT("drone.set_model"))
    {
        FString Model,Error;
        if (!Args->TryGetStringField(TEXT("model"),Model) || !Demo.SetDroneModel(Model,Error))
            return Fail(Error.IsEmpty()?TEXT("model is required"):Error);
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
        Demo.ActiveSensor=Mode;
        Demo.RefreshSensors();
    }
    else if (Command==TEXT("sensor.set_active"))
    {
        FString Sensor;
        if (!Args->TryGetStringField(TEXT("sensor"),Sensor) ||
            (Sensor!=TEXT("visible") && Sensor!=TEXT("infrared") && Sensor!=TEXT("lidar")))
            return Fail(TEXT("sensor must be visible, infrared, or lidar"));
        if (Sensor==TEXT("infrared") && !Demo.ThermalInstance) return Fail(TEXT("IR material unavailable"));
        Demo.ActiveSensor=Sensor;
        if (Sensor!=TEXT("lidar")) Demo.InfraredMode=Sensor==TEXT("infrared");
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
        if (Demo.InfraredMode) Demo.InfraredFOV=float(Fov); else Demo.VisibleFOV=float(Fov);
        Demo.RefreshSensors();
    }
    else if (Command==TEXT("camera.capture"))
    {
        FString Sensor=Demo.InfraredMode?TEXT("infrared"):TEXT("visible");
        if (Args->HasField(TEXT("sensor")) && (!Args->TryGetStringField(TEXT("sensor"),Sensor) || (Sensor!=TEXT("visible") && Sensor!=TEXT("infrared")))) return Fail(TEXT("sensor must be visible or infrared"));
        const bool IR=Sensor==TEXT("infrared");
        if (IR?!Demo.InfraredEnabled:!Demo.VisibleEnabled) return Fail(TEXT("Sensor disabled"));
        Demo.ExportSensorFrame(IR);
        if (Demo.LastExportPath.IsEmpty() || !IFileManager::Get().FileExists(*Demo.LastExportPath)) return Reply(Id,Empty,TEXT("capture_failed"),TEXT("PNG export failed"));
        auto R=State();
        R->SetStringField(TEXT("frame_path"),Demo.LastExportPath);
        R->SetStringField(TEXT("frame_sensor"),Sensor);
        R->SetNumberField(TEXT("frame_width"),IR?640:1920);
        R->SetNumberField(TEXT("frame_height"),IR?512:1080);
        return Reply(Id,R);
    }
    else if (Command==TEXT("camera.stream_frame"))
    {
        FString Channel;
        if (!Args->TryGetStringField(TEXT("channel"),Channel) || (Channel!=TEXT("CH1") && Channel!=TEXT("CH2") && Channel!=TEXT("OBS")))
            return Fail(TEXT("channel must be CH1, CH2 or OBS"));
        double RequestedQuality=70;
        Args->TryGetNumberField(TEXT("quality"),RequestedQuality);
        if (!FMath::IsFinite(RequestedQuality) || RequestedQuality<25 || RequestedQuality>95)
            return Fail(TEXT("quality must be within [25,95]"));
        TArray64<uint8> Encoded;
        int32 Width=0,Height=0;
        int64 StreamFrameNumber=0;
        double StreamSimulationTime=0;
        if ((Channel==TEXT("CH1") && !Demo.VisibleEnabled) || (Channel==TEXT("CH2") && !Demo.InfraredEnabled)) return Reply(Id,Empty,TEXT("sensor_disabled"),TEXT("Sensor disabled"));
        if (!(Channel==TEXT("OBS")?Demo.GetObserverFrame(Encoded,Width,Height,StreamFrameNumber,StreamSimulationTime):Demo.GetStreamFrame(Channel==TEXT("CH2"),Encoded,Width,Height,StreamFrameNumber,StreamSimulationTime)))
            return Reply(Id,Empty,TEXT("frame_unavailable"),TEXT("Asynchronous stream frame is warming up"));
        auto R=MakeShared<FJsonObject>();
        R->SetStringField(TEXT("device_id"),Channel==TEXT("OBS")?TEXT("observer"):Demo.GimbalId);
        R->SetStringField(TEXT("sensor_id"),Channel==TEXT("OBS")?FString(TEXT("observer/view")):Demo.GimbalId+(Channel==TEXT("CH2")?TEXT("/infrared"):TEXT("/visible")));
        R->SetStringField(TEXT("channel"),Channel);
        R->SetStringField(TEXT("modality"),Channel==TEXT("OBS")?TEXT("observer"):Channel==TEXT("CH1")?TEXT("visible"):TEXT("infrared"));
        R->SetNumberField(TEXT("frame_number"),StreamFrameNumber);
        R->SetNumberField(TEXT("simulation_time_s"),StreamSimulationTime);
        R->SetNumberField(TEXT("width"),Width);
        R->SetNumberField(TEXT("height"),Height);
        R->SetStringField(TEXT("encoding"),TEXT("jpeg"));
        R->SetNumberField(TEXT("quality"),60);
        R->SetStringField(TEXT("image_base64"),FBase64::Encode(Encoded.GetData(),Encoded.Num()));
        return Reply(Id,R);
    }
    else if (Command==TEXT("sensor.lidar.set_parameters"))
    {
        double Horizontal,Vertical,Range,Rate;
        if (!Args->TryGetNumberField(TEXT("horizontal_fov_deg"),Horizontal) || !Args->TryGetNumberField(TEXT("vertical_fov_deg"),Vertical) ||
            !Args->TryGetNumberField(TEXT("range_m"),Range) || !Args->TryGetNumberField(TEXT("scan_rate_hz"),Rate)) return Fail(TEXT("All lidar parameters are required"));
        if (!FMath::IsFinite(Horizontal) || Horizontal<.1 || Horizontal>60 || !FMath::IsFinite(Vertical) || Vertical<.1 || Vertical>60 ||
            !FMath::IsFinite(Range) || Range<1 || Range>1000 || !FMath::IsFinite(Rate) || Rate<.05 || Rate>10) return Fail(TEXT("Lidar parameters exceed supported limits"));
        Demo.LidarHorizontalFov=Horizontal;
        Demo.LidarVerticalFov=Vertical;
        Demo.LidarRangeMeters=Range;
        Demo.LidarScanRateHz=Rate;
        if (Demo.LidarEnabled) Demo.ScanLidar();
    }
    else if (Command==TEXT("sensor.lidar.set_enabled"))
    {
        bool Enabled=false;
        if (!Args->TryGetBoolField(TEXT("enabled"),Enabled)) return Fail(TEXT("enabled must be a boolean"));
        Demo.LidarEnabled=Enabled;
        if (Enabled) Demo.ScanLidar();
    }
    else if (Command==TEXT("sensor.lidar.capture"))
    {
        if (!Demo.LidarEnabled) return Fail(TEXT("Gimbal lidar is disabled"));
        if (!Demo.ExportLidarPointCloud() || !IFileManager::Get().FileExists(*Demo.LastLidarExportPath))
            return Reply(Id,Empty,TEXT("capture_failed"),TEXT("Lidar point-cloud export failed or contained no hits"));
        auto R=State();
        R->SetStringField(TEXT("point_cloud_path"),Demo.LastLidarExportPath);
        return Reply(Id,R);
    }
    else if (Command==TEXT("sensor.lidar.get_points"))
    {
        auto R=State();
        TArray<TSharedPtr<FJsonValue>> Points;
        constexpr int32 MaxPreviewPoints=768;
        const int32 Count=Demo.LidarEnabled?Demo.LastLidarPointsWorldCm.Num():0;
        const TArray<FVector> Preview=Demo.LidarEnabled?Demo.GetLidarPreviewPoints(MaxPreviewPoints):TArray<FVector>();
        Points.Reserve(Preview.Num());
        for (const FVector& Point : Preview)
            Points.Add(MakeShared<FJsonValueArray>(Vector(Point)));
        R->SetNumberField(TEXT("lidar_point_count"),Count);
        R->SetStringField(TEXT("lidar_coordinate_frame"),TEXT("sensor_local_x_forward_y_right_z_up"));
        R->SetStringField(TEXT("lidar_units"),TEXT("meters"));
        R->SetNumberField(TEXT("lidar_horizontal_samples"),Demo.LidarHorizontalSamples);
        R->SetNumberField(TEXT("lidar_vertical_samples"),Demo.LidarVerticalSamples);
        R->SetNumberField(TEXT("lidar_horizontal_fov_deg"),Demo.LidarHorizontalFov);
        R->SetNumberField(TEXT("lidar_vertical_fov_deg"),Demo.LidarVerticalFov);
        R->SetArrayField(TEXT("lidar_points_m"),Points);
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
            if (Clients.Num()<24) Clients.Add(MoveTemp(C));
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
            if (C.Input.Num()>MaxRequestMessage) { Alive=false; break; }
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
            if (C.Output.Num()-C.Sent>MaxResponseMessage) Alive=false;
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
