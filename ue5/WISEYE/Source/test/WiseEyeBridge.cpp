#include "WiseEyeBridge.h"
#include "Components/PrimitiveComponent.h"
#include "EngineUtils.h"
#include "WiseEyeDemo.h"
#include "WiseEyeStreaming.h"
#include "WiseEyeEventCamera.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Components/SceneComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/WorldPartitionStreamingSourceComponent.h"
#include "Engine/World.h"
#include "WorldPartition/WorldPartition.h"
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
#include "Misc/Guid.h"
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

void FWiseEyeSlotLease::Restore() {
    for (int32 I=0;I<Components.Num();++I) if (Components[I].IsValid()) Components[I]->SetCollisionEnabled(Modes[I]);
    if (Actor.IsValid()) Actor->SetActorEnableCollision(ActorCollision);
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
    for (auto& Pair:SlotLeases) Pair.Value.Restore();
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
    R->SetObjectField(TEXT("population"),Demo.PopulationState());
    if (Demo.OwnsDrone) R->SetObjectField(TEXT("aerial"),Demo.AerialState());
    R->SetStringField(TEXT("scene_id"),Demo.SceneId);
    R->SetStringField(TEXT("run_id"),Demo.PlaySessionId);
    R->SetBoolField(TEXT("ue_window_control_supported"),PLATFORM_WINDOWS!=0);
    R->SetBoolField(TEXT("ue_window_visible"),(Demo.FleetRoot?Demo.FleetRoot.Get():&Demo)->SimulationWindowVisible);
    R->SetBoolField(TEXT("training_samples_supported"),true);
    R->SetBoolField(TEXT("paired_training_samples_supported"),true);
    R->SetNumberField(TEXT("gt_max_fps_supported"),20);
    R->SetNumberField(TEXT("gt_max_fps"),Demo.GTSettings.MaxFPS);
    R->SetBoolField(TEXT("live_placement_supported"),true);
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
    Placement->SetBoolField(TEXT("preview_supported"),true);
    Placement->SetBoolField(TEXT("nudge_supported"),true);
    Placement->SetBoolField(TEXT("locked"),PlacementDemo.PlacementLocked);
    Placement->SetArrayField(TEXT("nudge_cm"),Vector(PlacementDemo.PlacementNudge));
    Placement->SetNumberField(TEXT("yaw_deg"),PlacementDemo.PlacementYawDegrees);
    const bool PreviewVisible=IsValid(PlacementDemo.PlacementPreview) && PlacementDemo.PlacementHoverValid && PlacementDemo.PlacementActive;
    Placement->SetBoolField(TEXT("preview_visible"),PreviewVisible);
    Placement->SetArrayField(TEXT("preview_position_cm"),Vector(PlacementDemo.PlacementPreviewPosition));
    if (PreviewVisible) {
        FVector Center,Extent;PlacementDemo.PlacementPreview->GetActorBounds(false,Center,Extent);
        Placement->SetArrayField(TEXT("preview_size_cm"),Vector(Extent*2));
    }
    Placement->SetStringField(TEXT("device_id"),PlacementDemo.PlacementDevice);
    Placement->SetStringField(TEXT("request_token"),PlacementDemo.PlacementToken);
    Placement->SetStringField(TEXT("error"),PlacementDemo.PlacementError);
    Placement->SetNumberField(TEXT("sequence"),PlacementDemo.PlacementSequence);
    Placement->SetArrayField(TEXT("position_cm"),Vector(PlacementDemo.PlacementPosition));
    Placement->SetArrayField(TEXT("surface_cm"),Vector(PlacementDemo.PlacementSurface));
    R->SetObjectField(TEXT("placement"),Placement);
    auto Applied=MakeShared<FJsonObject>();
    Applied->SetStringField(TEXT("request_token"),PlacementDemo.PlacementAppliedToken);
    Applied->SetStringField(TEXT("device_id"),PlacementDemo.PlacementAppliedDevice);
    R->SetObjectField(TEXT("placement_applied"),Applied);
    if (Demo.FreeObserver) R->SetArrayField(TEXT("observer_position_cm"),Vector(Demo.FreeObserver->GetActorLocation()));
    R->SetStringField(TEXT("input_mode"),Demo.FleetRoot?Demo.FleetRoot->ControlMode:Demo.ControlMode);
    R->SetNumberField(TEXT("pitch_min_deg"),Demo.MinPitch);
    R->SetNumberField(TEXT("pitch_max_deg"),Demo.MaxPitch);
    R->SetBoolField(TEXT("coordinate_pointing_supported"),true);
    const auto* StreamingRoot=Demo.FleetRoot?Demo.FleetRoot.Get():&Demo;
    const auto* WorldPartition=Demo.GetWorld()->GetWorldPartition();
    const bool StreamingEnabled=WorldPartition && WorldPartition->IsStreamingEnabled();
    R->SetBoolField(TEXT("world_streaming_enabled"),StreamingEnabled);
    int32 StreamingSources=0;
    bool StreamingReady=true;
    for (auto Rig : StreamingRoot->FleetRigs) {
        auto CheckSource=[&](AActor* Actor) {
            if (IsValid(Actor)) if (auto* Source=Actor->FindComponentByClass<UWorldPartitionStreamingSourceComponent>()) {
                ++StreamingSources;
                StreamingReady=StreamingReady && Source->IsStreamingCompleted();
            }
        };
        CheckSource(Rig);
        if (Rig->OwnsDrone) CheckSource(Rig->Drone);
    }
    R->SetBoolField(TEXT("world_streaming_ready"),StreamingReady && (Demo.SceneId!=TEXT("city_large") || (StreamingEnabled && StreamingSources>=2)));
    R->SetNumberField(TEXT("device_streaming_sources"),StreamingSources);
    if (Demo.SceneId==TEXT("city_large")) R->SetNumberField(TEXT("streaming_radius_m"),250);
    auto Geometry=MakeShared<FJsonObject>();
    Geometry->SetStringField(TEXT("world_unit"),TEXT("centimeter"));
    Geometry->SetStringField(TEXT("angles_reference"),TEXT("relative_to_device_base"));
    Geometry->SetArrayField(TEXT("base_position_cm"),Vector(Demo.Base->GetComponentLocation()));
    Geometry->SetArrayField(TEXT("pivot_position_cm"),Vector(Demo.PitchPivot->GetComponentLocation()));
    const auto BaseRotation=Demo.Base->GetComponentRotation();
    Geometry->SetArrayField(TEXT("base_rotation_pitch_yaw_roll_deg"),Vector(FVector(BaseRotation.Pitch,BaseRotation.Yaw,BaseRotation.Roll)));
    Geometry->SetNumberField(TEXT("yaw_rate_deg_s"),30);Geometry->SetNumberField(TEXT("pitch_rate_deg_s"),20);
    R->SetObjectField(TEXT("gimbal_geometry"),Geometry);
    R->SetNumberField(TEXT("lidar_horizontal_fov_deg"),Demo.LidarHorizontalFov);
    R->SetNumberField(TEXT("lidar_vertical_fov_deg"),Demo.LidarVerticalFov);
    R->SetNumberField(TEXT("lidar_scan_rate_hz"),Demo.LidarScanRateHz);
    R->SetNumberField(TEXT("lidar_range_m"),Demo.LidarRangeMeters);
    R->SetStringField(TEXT("pending_scene"),Demo.PendingScene);
    R->SetBoolField(TEXT("paused"),Demo.Paused);
    R->SetNumberField(TEXT("simulation_time_s"),Demo.SimulationTime);
    R->SetStringField(TEXT("flight_mode"),Demo.AutomaticFlight?TEXT("auto"):TEXT("manual"));
    R->SetBoolField(TEXT("fleet_live_edit_supported"),true);
    R->SetNumberField(TEXT("fleet_revision"),(Demo.FleetRoot?Demo.FleetRoot.Get():&Demo)->RuntimeFleetRevision);
    R->SetStringField(TEXT("flight_backend"),Demo.FlightBackend==EWiseEyeFlightBackend::ProjectAirSim?TEXT("projectairsim"):TEXT("kinematic"));
    R->SetStringField(TEXT("drone_model"),Demo.DroneModel);
    R->SetArrayField(TEXT("drone_models_available"),{
        MakeShared<FJsonValueString>(TEXT("mavic3")),
        MakeShared<FJsonValueString>(TEXT("avata"))});
    R->SetBoolField(TEXT("dynamics_connected"),Demo.DynamicsConnected);
    R->SetStringField(TEXT("dynamics_actor"),IsValid(Demo.DynamicsSource)?Demo.DynamicsSource->GetName():TEXT(""));
    R->SetBoolField(TEXT("tracking"),Demo.TrackingEnabled);
    R->SetBoolField(TEXT("sensor_power_supported"),true);
    R->SetBoolField(TEXT("rotors_running"),Demo.RotorsRunning);
    R->SetNumberField(TEXT("rotor_rpm"),Demo.RotorRPM);
    TArray<TSharedPtr<FJsonValue>> RPMs; for (float RPM:Demo.MotorRPMs) RPMs.Add(MakeShared<FJsonValueNumber>(RPM));
    R->SetArrayField(TEXT("motor_rpm"),RPMs);
    auto TargetHeat=MakeShared<FJsonObject>();
    const auto* ThermalRoot=Demo.FleetRoot?Demo.FleetRoot.Get():&Demo;
    const auto* ThermalOwner=Demo.OwnsDrone?&Demo:ThermalRoot->FindDevice(Demo.DroneId);
    if (ThermalOwner) {
        TargetHeat->SetNumberField(TEXT("motor_warmth"),ThermalOwner->ThermalHeat.Motor);
        TargetHeat->SetNumberField(TEXT("battery_warmth"),ThermalOwner->ThermalHeat.Battery);
        TargetHeat->SetNumberField(TEXT("power_proxy"),ThermalOwner->ThermalPower);
        TargetHeat->SetNumberField(TEXT("body_signal"),ThermalOwner->BodyHeat);
        TargetHeat->SetNumberField(TEXT("motor_signal"),ThermalOwner->MotorHeat);
        TargetHeat->SetStringField(TEXT("units"),TEXT("normalized engineering proxy, not Celsius"));
    }
    R->SetObjectField(TEXT("thermal_target"),TargetHeat);
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
        MakeShared<FJsonValueString>(TEXT("lidar")),MakeShared<FJsonValueString>(TEXT("event"))});
    auto Sensors=MakeShared<FJsonObject>();
    for (const FString Sensor : {FString(TEXT("visible")),FString(TEXT("infrared")),FString(TEXT("lidar"))})
    {
        auto Settings=MakeShared<FJsonObject>();
        const bool IR=Sensor==TEXT("infrared"), Lidar=Sensor==TEXT("lidar");
        Settings->SetBoolField(TEXT("enabled"),Lidar?Demo.LidarEnabled:IR?Demo.InfraredEnabled:Demo.VisibleEnabled);
        if (!Lidar) {
            const double HFov=IR?Demo.InfraredFOV:Demo.VisibleFOV;
            const auto* Capture=IR?Demo.InfraredCapture.Get():Demo.Capture.Get();
            const int32 Width=IR?640:1920,Height=IR?512:1080;
            Settings->SetNumberField(TEXT("fov_deg"),HFov);
            Settings->SetNumberField(TEXT("vertical_fov_deg"),FMath::RadiansToDegrees(2*FMath::Atan(FMath::Tan(FMath::DegreesToRadians(HFov)*.5)*Height/Width)));
            Settings->SetNumberField(TEXT("width_px"),Width);Settings->SetNumberField(TEXT("height_px"),Height);
        }
        if (!Lidar) Settings->SetNumberField(TEXT("capture_sequence"),IR?Demo.ThermalFrameIndex:Demo.VisibleCaptureSequence);
        if (!Lidar) {
            const auto Offset=IR?Demo.InfraredOffsetCm:Demo.VisibleOffsetCm;
            const auto Rotation=IR?Demo.InfraredBoresight:Demo.VisibleBoresight;
            const auto* Source=IR?Demo.InfraredCapture.Get():Demo.Capture.Get();
            Settings->SetBoolField(TEXT("extrinsics_supported"),true);
            Settings->SetNumberField(TEXT("mount_x_cm"),Offset.X);Settings->SetNumberField(TEXT("mount_y_cm"),Offset.Y);Settings->SetNumberField(TEXT("mount_z_cm"),Offset.Z);
            Settings->SetNumberField(TEXT("boresight_pitch_deg"),Rotation.Pitch);Settings->SetNumberField(TEXT("boresight_yaw_deg"),Rotation.Yaw);Settings->SetNumberField(TEXT("boresight_roll_deg"),Rotation.Roll);
            Settings->SetArrayField(TEXT("camera_position_cm"),Vector(Source->GetComponentLocation()));
            const auto WorldRotation=Source->GetComponentRotation();
            Settings->SetArrayField(TEXT("camera_rotation_pitch_yaw_roll_deg"),Vector(FVector(WorldRotation.Pitch,WorldRotation.Yaw,WorldRotation.Roll)));
        }
        if (!IR && !Lidar) {
            Settings->SetBoolField(TEXT("appearance_available"),IsValid(Demo.VisibleInstance));
            Settings->SetNumberField(TEXT("blur_px"),Demo.VisibleBlur);Settings->SetNumberField(TEXT("noise"),Demo.VisibleNoise);
            Demo.VisibleFocus.Write(Settings,Demo.VisibleFOV);
            Settings->SetNumberField(TEXT("contrast"),Demo.VisibleContrast);Settings->SetNumberField(TEXT("saturation"),Demo.VisibleSaturation);
        }
        if (IR) {
            Settings->SetStringField(TEXT("palette"),Demo.BlackHot?TEXT("black_hot"):TEXT("white_hot")); Settings->SetNumberField(TEXT("noise"),Demo.ThermalNoise);
            const bool Experimental=Demo.ThermalMaterial && (Demo.ThermalMaterial->GetName()==TEXT("M_IR_Experimental") || Demo.HasReferenceInfrared());
            Settings->SetStringField(TEXT("thermal_profile"),Experimental?Demo.ThermalProfile:TEXT("legacy"));
            Settings->SetBoolField(TEXT("enhanced_available"),Experimental);
            Settings->SetBoolField(TEXT("reference_available"),Demo.HasReferenceInfrared());
            Settings->SetBoolField(TEXT("classified_available"),Demo.HasClassifiedInfrared());
            Settings->SetBoolField(TEXT("facade_available"),Demo.HasFacadeInfrared());
            Settings->SetBoolField(TEXT("detector_controls_available"),Demo.HasFacadeInfrared());
            const auto& D=Demo.ThermalDetector;
            Settings->SetStringField(TEXT("gain_mode"),D.Mode==1?TEXT("locked"):D.Mode==2?TEXT("manual"):TEXT("auto"));
            Settings->SetBoolField(TEXT("stable_agc"),D.Stable);
            Settings->SetNumberField(TEXT("manual_low"),D.Low);Settings->SetNumberField(TEXT("manual_high"),D.High);
            Settings->SetNumberField(TEXT("brightness"),D.Brightness);Settings->SetNumberField(TEXT("sky_denoise"),D.Denoise);
            Settings->SetNumberField(TEXT("noise_seed"),D.Seed);
            Settings->SetBoolField(TEXT("agc_enabled"),Demo.ThermalAutoGain);
            Settings->SetNumberField(TEXT("agc_response_s"),Demo.ThermalGainResponse);
            Settings->SetNumberField(TEXT("sampling_scale"),Demo.ThermalSamplingScale);
            {
                const auto Readout=Demo.GetThermalReadout();
                Settings->SetNumberField(TEXT("agc_low"),Readout.Low);Settings->SetNumberField(TEXT("agc_high"),Readout.High);
                Settings->SetNumberField(TEXT("readout_ms"),Readout.ProcessingMs);Settings->SetNumberField(TEXT("readout_sequence"),Readout.Sequence);
                TArray<TSharedPtr<FJsonValue>> ClassPixels;for (int32 Count:Readout.ClassPixels) ClassPixels.Add(MakeShared<FJsonValueNumber>(Count));
                Settings->SetArrayField(TEXT("class_pixels"),ClassPixels);
                Settings->SetNumberField(TEXT("target_pixels"),Readout.TargetPixels);
                Settings->SetNumberField(TEXT("motor_region_pixels"),Readout.MotorRegionPixels);
                Settings->SetNumberField(TEXT("sky_pixels"),Readout.SkyPixels);
            }
            Settings->SetStringField(TEXT("signal_model"),TEXT("normalized thermal proxy, FP16 pre-AGC; not radiometric"));
            Settings->SetNumberField(TEXT("blur_px"),Demo.ThermalBlurPixels);
            Settings->SetNumberField(TEXT("contrast"),Demo.ThermalContrast);
            Settings->SetNumberField(TEXT("background_detail"),Demo.ThermalBackgroundDetail);
        }
        if (Lidar) {
            Settings->SetNumberField(TEXT("horizontal_fov_deg"),Demo.LidarHorizontalFov);
            Settings->SetNumberField(TEXT("vertical_fov_deg"),Demo.LidarVerticalFov);
            Settings->SetNumberField(TEXT("range_m"),Demo.LidarRangeMeters);
            Settings->SetNumberField(TEXT("scan_rate_hz"),Demo.LidarScanRateHz);
            Settings->SetNumberField(TEXT("scan_sequence"),Demo.LidarScanSequence);
        }
        Sensors->SetObjectField(Sensor,Settings);
    }
    R->SetObjectField(TEXT("sensors"),Sensors);
    Sensors->SetObjectField(TEXT("event"),Demo.EventSensorState());
    R->SetStringField(TEXT("palette"),Demo.BlackHot?TEXT("black_hot"):TEXT("white_hot"));
    R->SetNumberField(TEXT("fov_deg"),Demo.FieldOfView);
    // Camera specifications remain available while acquisition is off.
    R->SetNumberField(TEXT("width"),Demo.InfraredMode?640:1920);
    R->SetNumberField(TEXT("height"),Demo.InfraredMode?512:1080);
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
        FString RequestedChannel;Args->TryGetStringField(TEXT("channel"),RequestedChannel);
        const bool AerialCommand=Command.StartsWith(TEXT("aerial.")) || (Command==TEXT("camera.stream_frame") && (RequestedChannel==TEXT("AERIAL") || RequestedChannel==TEXT("AERIAL_IR")));
        const bool GimbalCommand=!AerialCommand && (Command.StartsWith(TEXT("gimbal.")) || Command.StartsWith(TEXT("sensor.")) || Command.StartsWith(TEXT("camera.")));
        const bool DroneCommand=Command.StartsWith(TEXT("drone.")) || Command.StartsWith(TEXT("rotors.")) || Command.StartsWith(TEXT("flight.")) || Command==TEXT("sim.pause") || Command==TEXT("sim.resume") || Command==TEXT("sim.reset");
        if (GimbalCommand && DeviceId!=Target->GimbalId) return Fail(TEXT("Command requires a gimbal device_id"));
        if ((DroneCommand || AerialCommand) && (!Target->OwnsDrone || DeviceId!=Target->DroneId)) return Fail(TEXT("Command requires a drone device_id"));
        if (Target!=&Demo && Command!=TEXT("flight.get_local_control") && (GimbalCommand || DroneCommand || AerialCommand || Command==TEXT("sim.get_state") || Command==TEXT("sim.ping"))) return Target->DispatchDevice(Request);
    }
    if (Command==TEXT("aerial.configure")) {
        FString Error;if (!Demo.ConfigureAerial(Args,Error)) return Fail(Error);
        return Reply(Id,State());
    }
    if (Command==TEXT("aerial.get_state")) return Reply(Id,State());
    if (Command==TEXT("population.get_state")) return Reply(Id,State());
    if (Command==TEXT("population.get_agents")) {
        FString Camera;if (Args->HasField(TEXT("from_camera")) && !Args->TryGetStringField(TEXT("from_camera"),Camera)) return Fail(TEXT("from_camera must be a drone ID"));
        return Reply(Id,Demo.PopulationAgents(Camera));
    }
    if (Command==TEXT("population.configure")) {
        FString Error;if (!Demo.ConfigurePopulation(Args,Error)) return Fail(Error);
        return Reply(Id,State());
    }
    if (Command==TEXT("observation.save")) {
        FString Error;if (!Demo.SaveObservation(Error)) return Fail(Error);
        return Reply(Id,State());
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
    if (Command==TEXT("flight.prepare_slot") || Command==TEXT("flight.finish_slot")) {
        FString Run,Slot,Token;
        if (!Args->TryGetStringField(TEXT("run_id"),Run) || Run!=Demo.PlaySessionId || !Args->TryGetStringField(TEXT("slot"),Slot) ||
            (Slot!=TEXT("Drone1") && Slot!=TEXT("Drone2") && Slot!=TEXT("Drone3") && Slot!=TEXT("Drone4")) || !Args->TryGetStringField(TEXT("token"),Token) || Token.IsEmpty() || Token.Len()>64) return Fail(TEXT("Current run, flight slot and lease token required"));
        if (Command==TEXT("flight.prepare_slot")) {
            if (SlotLeases.Contains(Slot)) return Fail(TEXT("Flight slot placement already pending"));
            for (auto Rig:Demo.FleetRigs) if (Rig->OwnsDrone && Rig->DroneModel!=TEXT("fixedwing") && Rig->DynamicsActorName.ToString()==Slot && Rig->RotorsRunning) return Fail(TEXT("Land and stop motors before teleporting this slot"));
            AActor* Source=nullptr;for (TActorIterator<AActor> It(Demo.GetWorld());It;++It) if (It->GetName()==Slot) {Source=*It;break;}
            if (!Source) return Fail(TEXT("Flight slot actor unavailable"));
            FWiseEyeSlotLease Lease;Lease.Actor=Source;Lease.ActorCollision=Source->GetActorEnableCollision();Lease.Token=Token;Lease.Expires=FPlatformTime::Seconds()+5;
            TArray<UPrimitiveComponent*> Components;Source->GetComponents(Components);
            for (auto* Component:Components) {Lease.Components.Add(Component);Lease.Modes.Add(Component->GetCollisionEnabled());Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);}
            Source->SetActorEnableCollision(false);SlotLeases.Add(Slot,MoveTemp(Lease));
        } else {
            auto* Lease=SlotLeases.Find(Slot);
            if (!Lease || Lease->Token!=Token) return Fail(TEXT("Placement lease expired or changed"));
            Lease->Restore();SlotLeases.Remove(Slot);
        }
        return Reply(Id,State());
    }
    if (Command==TEXT("fleet.patch")) {
        FString Error;
        if (!Demo.EditLiveFleet(Args,Error)) return Fail(Error);
        return Reply(Id,State());
    }
    if (Command==TEXT("flight.hide_reserves")) {
        for (TActorIterator<AActor> It(Demo.GetWorld());It;++It) {
            const FString Name=It->GetName();
            if (Name==TEXT("Drone1") || Name==TEXT("Drone2") || Name==TEXT("Drone3") || Name==TEXT("Drone4")) It->SetActorHiddenInGame(true);
        }
        return Reply(Id,State());
    }
    if (Command==TEXT("sim.ping") || Command==TEXT("sim.get_state")) return Reply(Id,State());
    if (Command==TEXT("sim.window.set_visible")) {
        bool Visible=false;
        if (!Args->TryGetBoolField(TEXT("visible"),Visible)) return Fail(TEXT("Boolean visible required"));
        if (!(Demo.FleetRoot?Demo.FleetRoot.Get():&Demo)->SetSimulationWindowVisible(Visible)) return Fail(TEXT("Simulation window unavailable"));
        return Reply(Id,State());
    }
    if (Command==TEXT("environment.configure") || Command==TEXT("environment.reset")) {
        auto& Root=Demo.FleetRoot?*Demo.FleetRoot:Demo;
        if (Command==TEXT("environment.reset")) Root.ResetEnvironment();
        else {
            bool Override=false;double Hour=0,Fog=0,Rain=0;
            if (!Args->TryGetBoolField(TEXT("time_override"),Override) || !Args->TryGetNumberField(TEXT("hour"),Hour) ||
                !Args->TryGetNumberField(TEXT("fog"),Fog) || !Args->TryGetNumberField(TEXT("rain"),Rain) ||
                !FMath::IsFinite(Hour) || Hour<0 || Hour>=24 || !FMath::IsFinite(Fog) || Fog<0 || Fog>1 || !FMath::IsFinite(Rain) || Rain<0 || Rain>1)
                return Fail(TEXT("Environment requires time_override, hour [0,24), fog/rain [0,1]"));
            double Clouds=Root.EnvironmentClouds;
            if (Args->HasField(TEXT("clouds")) && (Args->Values[TEXT("clouds")]->Type!=EJson::Number || !Args->TryGetNumberField(TEXT("clouds"),Clouds) || !FMath::IsFinite(Clouds) || Clouds<0 || Clouds>1)) return Fail(TEXT("clouds must be a number within [0,1]"));
            Root.InitializeEnvironment();
            if (Clouds>0 && !Root.EnvironmentCloudMaterial) return Fail(TEXT("Cloud material unavailable"));
            FString Error;if (!Root.ConfigureEnvironment(Override,Hour,Fog,Rain,Error)) return Fail(Error);
            if (!Root.ConfigureClouds(Clouds,Error)) return Fail(Error);
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
        C->SetBoolField(TEXT("coordinate_pointing_supported"),true);
        C->SetStringField(TEXT("coordinate_frame"),TEXT("ue_world_cm"));
        R->SetObjectField(TEXT("gimbal_capabilities"),C); return Reply(Id,R);
    }
    if (Command==TEXT("gimbal.point_at")) {
        FString Scene,Run,Sensor;
        if (!Args->TryGetStringField(TEXT("scene_id"),Scene) || Scene!=Demo.SceneId ||
            !Args->TryGetStringField(TEXT("run_id"),Run) || Run!=Demo.PlaySessionId ||
            !Args->TryGetStringField(TEXT("sensor"),Sensor) || (Sensor!=TEXT("visible") && Sensor!=TEXT("infrared")))
            return Fail(TEXT("Current scene_id, run_id and visible/infrared sensor required"));
        const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
        if (!Args->TryGetArrayField(TEXT("position_cm"),Values) || Values->Num()!=3) return Fail(TEXT("position_cm needs three world coordinates"));
        FVector Target;
        for (int32 I=0;I<3;++I) {
            double V=0;if ((*Values)[I]->Type!=EJson::Number || !(*Values)[I]->TryGetNumber(V) || !FMath::IsFinite(V) || FMath::Abs(V)>1e7)
                return Fail(TEXT("World coordinates must be finite numbers within 100 km"));
            Target[I]=V;
        }
        auto* Source=Sensor==TEXT("infrared")?Demo.InfraredCapture.Get():Demo.Capture.Get();
        if (!Source || FVector::Distance(Target,Source->GetComponentLocation())<1) return Fail(TEXT("Target must be at least 1 cm from the selected optical center"));
        const FRotator OldYaw=Demo.YawPivot->GetRelativeRotation(),OldPitch=Demo.PitchPivot->GetRelativeRotation();
        // Iterate actual component transforms so independent camera offsets,
        // boresight and rotated/scaled device bases remain in the solution.
        double CandidateYaw=OldYaw.Yaw,CandidatePitch=OldPitch.Pitch;
        for (int32 I=0;I<12;++I) {
            const auto Desired=Demo.Base->GetComponentTransform().InverseTransformVectorNoScale(Target-Source->GetComponentLocation()).Rotation();
            const auto Actual=(Demo.Base->GetComponentQuat().Inverse()*Source->GetComponentQuat()).Rotator();
            CandidateYaw=FRotator::NormalizeAxis(CandidateYaw+FMath::FindDeltaAngleDegrees(double(Actual.Yaw),double(Desired.Yaw)));
            CandidatePitch+=FMath::FindDeltaAngleDegrees(double(Actual.Pitch),double(Desired.Pitch));
            Demo.YawPivot->SetRelativeRotation(FRotator(0,CandidateYaw,0));Demo.PitchPivot->SetRelativeRotation(FRotator(CandidatePitch,0,0));
        }
        const double Error=FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct((Target-Source->GetComponentLocation()).GetSafeNormal(),Source->GetForwardVector()),-1.0,1.0)));
        if (!FMath::IsFinite(CandidatePitch) || CandidatePitch<Demo.MinPitch-1e-6 || CandidatePitch>Demo.MaxPitch+1e-6 || Error>.01) {
            Demo.YawPivot->SetRelativeRotation(OldYaw);Demo.PitchPivot->SetRelativeRotation(OldPitch);
            return Fail(TEXT("Target outside pitch limits or selected optical axis cannot converge; previous pose preserved"));
        }
        Demo.TrackingEnabled=false;Demo.RemoteGimbalInput=FVector2D::ZeroVector;
        auto R=State();auto Pointing=MakeShared<FJsonObject>();
        Pointing->SetStringField(TEXT("sensor"),Sensor);Pointing->SetArrayField(TEXT("position_cm"),Vector(Target));
        Pointing->SetNumberField(TEXT("error_deg"),Error);
        Pointing->SetNumberField(TEXT("slant_range_m"),FVector::Distance(Target,Source->GetComponentLocation())/100.);
        R->SetObjectField(TEXT("coordinate_pointing"),Pointing);return Reply(Id,R);
    }
    if (Command==TEXT("placement.validate") || Command==TEXT("placement.apply")) {
        FString Scene,Run,Token,Device,Error;double Yaw=0;const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
        if (!Args->TryGetStringField(TEXT("scene_id"),Scene) || Scene!=Demo.SceneId ||
            !Args->TryGetStringField(TEXT("run_id"),Run) || Run!=Demo.PlaySessionId ||
            !Args->TryGetStringField(TEXT("request_token"),Token) || Token.IsEmpty() || Token.Len()>64 ||
            !Args->TryGetStringField(TEXT("device_id"),Device) || !Demo.FindDevice(Device) ||
            !Args->TryGetNumberField(TEXT("yaw_deg"),Yaw) || !FMath::IsFinite(Yaw) || FMath::Abs(Yaw)>180 ||
            !Args->TryGetArrayField(TEXT("position_cm"),Values) || Values->Num()!=3)
            return Fail(TEXT("Current scene/run, device, token and finite position/yaw required"));
        double XYZ[3];for (int32 I=0;I<3;++I) if (!(*Values)[I]->TryGetNumber(XYZ[I]) || !FMath::IsFinite(XYZ[I]) || FMath::Abs(XYZ[I])>1e7) return Fail(TEXT("Invalid position_cm"));
        if (Command==TEXT("placement.apply")) {
            if (!Demo.ApplyDevicePlacement(Device,FVector(XYZ[0],XYZ[1],XYZ[2]),Yaw,Error)) return Fail(Error);
            Demo.PlacementAppliedToken=Token;Demo.PlacementAppliedDevice=Device;
        }
        return Reply(Id,State());
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
    if (Command==TEXT("sensor.event.get_packet") || Command==TEXT("sensor.event.capture")) {
        if (!Demo.EventEnabled || !Demo.StreamManager) return Reply(Id,Empty,TEXT("sensor_disabled"),TEXT("Event camera disabled"));
        FString Run;
        if (Args->TryGetStringField(TEXT("run_id"),Run) && Run!=Demo.PlaySessionId) return Fail(TEXT("Event session changed"));
        double After=0,Limit=5000;bool Latest=false;
        if ((Args->HasField(TEXT("after_sequence")) && !Args->TryGetNumberField(TEXT("after_sequence"),After)) ||
            (Args->HasField(TEXT("max_events")) && !Args->TryGetNumberField(TEXT("max_events"),Limit)) ||
            (Args->HasField(TEXT("latest")) && !Args->TryGetBoolField(TEXT("latest"),Latest)) ||
            !FMath::IsFinite(After) || After<0 || After>9007199254740991. || FMath::FloorToDouble(After)!=After ||
            !FMath::IsFinite(Limit) || Limit<1 || Limit>20000 || FMath::FloorToDouble(Limit)!=Limit) return Fail(TEXT("Invalid event cursor/limit"));
        auto Data=Demo.StreamManager->EventCamera->Packet(int64(After),int32(Limit),Latest || Command==TEXT("sensor.event.capture"));
        Data->SetStringField(TEXT("device_id"),Demo.GimbalId);Data->SetStringField(TEXT("sensor_id"),Demo.GimbalId+TEXT("/event"));
        Data->SetStringField(TEXT("run_id"),Demo.PlaySessionId);Data->SetStringField(TEXT("scene_id"),Demo.SceneId);
        Data->SetNumberField(TEXT("simulation_time_s"),Demo.SimulationTime);
        Data->SetObjectField(TEXT("sensor_state"),Demo.EventSensorState());
        if (Command==TEXT("sensor.event.get_packet")) return Reply(Id,Data);
        FString Json;FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Json));
        Demo.LastEventExportPath=FPaths::Combine(Demo.OutputDirectory,FString::Printf(TEXT("EVENT_%s.json"),*FGuid::NewGuid().ToString(EGuidFormats::Digits)));
        if (!FFileHelper::SaveStringToFile(Json,*Demo.LastEventExportPath)) return Fail(TEXT("Could not save event window"));
        auto Result=State();Result->SetStringField(TEXT("event_last_export_path"),Demo.LastEventExportPath);return Reply(Id,Result);
    }
    if (Command==TEXT("sensor.set_enabled")) {
        FString Sensor;bool Enabled=false;
        if (!Args->TryGetStringField(TEXT("sensor"),Sensor) || !Args->HasField(TEXT("enabled")) || Args->Values[TEXT("enabled")]->Type!=EJson::Boolean || !Args->TryGetBoolField(TEXT("enabled"),Enabled)) return Fail(TEXT("sensor and Boolean enabled required"));
        if (Sensor==TEXT("event")) { Demo.EventEnabled=Enabled;Demo.RefreshEventSensor();return Reply(Id,State()); }
        if (Sensor==TEXT("visible")) Demo.VisibleEnabled=Enabled;
        else if (Sensor==TEXT("infrared")) Demo.InfraredEnabled=Enabled;
        else if (Sensor==TEXT("lidar")) {
            Demo.LidarEnabled=Enabled;
            if (!Enabled) { Demo.LastLidarPointsWorldCm.Reset();Demo.LastLidarRangesMeters.Reset();Demo.LidarHitCount=0;Demo.LidarNearestRangeMeters=0; }
        } else return Fail(TEXT("Unknown sensor"));
        Demo.RefreshSensors();
        return Reply(Id,State());
    }
    if (Command==TEXT("sensor.configure"))
    {
        FString Sensor,Palette; bool Enabled=false;
        if (!Args->TryGetStringField(TEXT("sensor"),Sensor) || !Args->TryGetBoolField(TEXT("enabled"),Enabled)) return Fail(TEXT("sensor and enabled required"));
        if (Sensor==TEXT("event")) {
            double Fov,Hz,On,Off,Refractory;
            if (!Args->TryGetNumberField(TEXT("fov_deg"),Fov) || !Args->TryGetNumberField(TEXT("sample_hz"),Hz) ||
                !Args->TryGetNumberField(TEXT("positive_threshold"),On) || !Args->TryGetNumberField(TEXT("negative_threshold"),Off) ||
                !Args->TryGetNumberField(TEXT("refractory_us"),Refractory)) return Fail(TEXT("Event camera parameters required"));
            for (double V:{Fov,Hz,On,Off,Refractory}) if (!FMath::IsFinite(V)) return Fail(TEXT("Event parameters must be finite"));
            if (Fov<5 || Fov>120 || Hz<1 || Hz>120 || On<.01 || On>1 || Off<.01 || Off>1 || Refractory<0 || Refractory>100000 || FMath::FloorToDouble(Refractory)!=Refractory) return Fail(TEXT("Event parameters exceed limits"));
            FVector Offset=Demo.EventOffsetCm;FRotator Rotation=Demo.EventBoresight;
            const TArray<TPair<FString,double*>> Fields={{TEXT("mount_x_cm"),&Offset.X},{TEXT("mount_y_cm"),&Offset.Y},{TEXT("mount_z_cm"),&Offset.Z},{TEXT("boresight_pitch_deg"),&Rotation.Pitch},{TEXT("boresight_yaw_deg"),&Rotation.Yaw},{TEXT("boresight_roll_deg"),&Rotation.Roll}};
            for (int32 I=0;I<Fields.Num();++I) if (Args->HasField(Fields[I].Key) && (!Args->TryGetNumberField(Fields[I].Key,*Fields[I].Value) || !FMath::IsFinite(*Fields[I].Value) || FMath::Abs(*Fields[I].Value)>(I<3?100:15))) return Fail(TEXT("Invalid event camera extrinsics"));
            Demo.EventEnabled=Enabled;Demo.EventFOV=Fov;Demo.EventSampleHz=Hz;Demo.EventOn=On;Demo.EventOff=Off;Demo.EventRefractoryUs=int64(Refractory);
            Demo.EventOffsetCm=Offset;Demo.EventBoresight=Rotation;Demo.RefreshEventSensor();return Reply(Id,State());
        }
        if (Sensor==TEXT("visible") || Sensor==TEXT("infrared")) {
            auto Offset=Sensor==TEXT("infrared")?Demo.InfraredOffsetCm:Demo.VisibleOffsetCm;
            auto Rotation=Sensor==TEXT("infrared")?Demo.InfraredBoresight:Demo.VisibleBoresight;
            auto CalibrationNumber=[&](const TCHAR* Key,double& Value,double Limit) {
                return !Args->HasField(Key) || (Args->Values[Key]->Type==EJson::Number && Args->TryGetNumberField(Key,Value) && FMath::IsFinite(Value) && FMath::Abs(Value)<=Limit);
            };
            if (!CalibrationNumber(TEXT("mount_x_cm"),Offset.X,100) || !CalibrationNumber(TEXT("mount_y_cm"),Offset.Y,100) || !CalibrationNumber(TEXT("mount_z_cm"),Offset.Z,100) ||
                !CalibrationNumber(TEXT("boresight_pitch_deg"),Rotation.Pitch,15) || !CalibrationNumber(TEXT("boresight_yaw_deg"),Rotation.Yaw,15) || !CalibrationNumber(TEXT("boresight_roll_deg"),Rotation.Roll,15)) return Fail(TEXT("Invalid camera extrinsics: position +/-100cm, boresight +/-15deg"));
            double Fov,Noise=0;
            if (!Args->TryGetNumberField(TEXT("fov_deg"),Fov) || !FMath::IsFinite(Fov) || Fov<5 || Fov>120) return Fail(TEXT("fov_deg must be within [5,120]"));
            if (Sensor==TEXT("infrared")) {
                if (!Args->TryGetStringField(TEXT("palette"),Palette) || (Palette!=TEXT("white_hot") && Palette!=TEXT("black_hot")) || !Args->TryGetNumberField(TEXT("noise"),Noise) || !FMath::IsFinite(Noise) || Noise<0 || Noise>1) return Fail(TEXT("Invalid infrared palette/noise"));
                FString Profile=Demo.ThermalProfile;
                bool AutoGain=Demo.ThermalAutoGain;
                double Response=Demo.ThermalGainResponse,Scale=Demo.ThermalSamplingScale;
                double Blur=Demo.ThermalBlurPixels,Contrast=Demo.ThermalContrast,Detail=Demo.ThermalBackgroundDetail;
                if (Args->HasField(TEXT("thermal_profile")) && (!Args->TryGetStringField(TEXT("thermal_profile"),Profile) || (Profile!=TEXT("legacy") && Profile!=TEXT("enhanced") && Profile!=TEXT("reference") && Profile!=TEXT("classified") && Profile!=TEXT("facade")))) return Fail(TEXT("Invalid thermal_profile"));
                auto OptionalNumber=[&](const TCHAR* Key,double& Value,double Low,double High) {
                    return !Args->HasField(Key) || (Args->Values[Key]->Type==EJson::Number && Args->TryGetNumberField(Key,Value) && FMath::IsFinite(Value) && Value>=Low && Value<=High);
                };
                if (!OptionalNumber(TEXT("blur_px"),Blur,0,2) || !OptionalNumber(TEXT("contrast"),Contrast,.3,3) || !OptionalNumber(TEXT("background_detail"),Detail,0,1)) return Fail(TEXT("Invalid thermal appearance parameters"));
                if (!OptionalNumber(TEXT("agc_response_s"),Response,.1,10) || !OptionalNumber(TEXT("sampling_scale"),Scale,1,2) || (Scale!=1 && Scale!=2) ||
                    (Args->HasField(TEXT("agc_enabled")) && (Args->Values[TEXT("agc_enabled")]->Type!=EJson::Boolean || !Args->TryGetBoolField(TEXT("agc_enabled"),AutoGain)))) return Fail(TEXT("Invalid reference camera parameters"));
                auto Detector=Demo.ThermalDetector;
                FString GainMode=Detector.Mode==1?TEXT("locked"):Detector.Mode==2?TEXT("manual"):TEXT("auto");
                double Low=Detector.Low,High=Detector.High,Brightness=Detector.Brightness,Denoise=Detector.Denoise,Seed=Detector.Seed;
                if (Args->HasField(TEXT("gain_mode"))) {
                    if (!Args->TryGetStringField(TEXT("gain_mode"),GainMode) || (GainMode!=TEXT("auto") && GainMode!=TEXT("locked") && GainMode!=TEXT("manual"))) return Fail(TEXT("Invalid gain_mode"));
                    if (Args->HasField(TEXT("agc_enabled")) && AutoGain!=(GainMode==TEXT("auto"))) return Fail(TEXT("gain_mode conflicts with agc_enabled"));
                    Detector.Mode=GainMode==TEXT("locked")?1:GainMode==TEXT("manual")?2:0;
                } else if (Args->HasField(TEXT("agc_enabled"))) Detector.Mode=AutoGain?0:2;
                if (!OptionalNumber(TEXT("manual_low"),Low,0,1) || !OptionalNumber(TEXT("manual_high"),High,0,1) || High-Low<.009999 ||
                    !OptionalNumber(TEXT("brightness"),Brightness,-.3,.3) || !OptionalNumber(TEXT("sky_denoise"),Denoise,0,1) || !OptionalNumber(TEXT("noise_seed"),Seed,0,2147483647.) || Seed!=FMath::FloorToDouble(Seed)) return Fail(TEXT("Invalid detector range/brightness/denoise/seed"));
                if (Args->HasField(TEXT("stable_agc")) && (Args->Values[TEXT("stable_agc")]->Type!=EJson::Boolean || !Args->TryGetBoolField(TEXT("stable_agc"),Detector.Stable))) return Fail(TEXT("stable_agc must be Boolean"));
                for (const TCHAR* Key:{TEXT("gain_mode"),TEXT("stable_agc"),TEXT("manual_low"),TEXT("manual_high"),TEXT("brightness"),TEXT("sky_denoise"),TEXT("noise_seed")})
                    if (Args->HasField(Key) && !Demo.HasFacadeInfrared()) return Fail(TEXT("Detector material is not installed"));
                Detector.Low=Low;Detector.High=High;Detector.Brightness=Brightness;Detector.Denoise=Denoise;Detector.Seed=uint32(Seed);
                AutoGain=Detector.Mode==0;
                if (Profile==TEXT("reference") && !Demo.HasReferenceInfrared()) return Fail(TEXT("Reference infrared material is not installed"));
                if (Profile==TEXT("classified") && !Demo.HasClassifiedInfrared()) return Fail(TEXT("Classified infrared material is not installed"));
                if (Profile==TEXT("facade") && !Demo.HasFacadeInfrared()) return Fail(TEXT("Facade infrared material is not installed"));
                if (Profile==TEXT("enhanced") && (!Demo.ThermalMaterial || (Demo.ThermalMaterial->GetName()!=TEXT("M_IR_Experimental") && !Demo.HasReferenceInfrared()))) return Fail(TEXT("Enhanced infrared material is not installed"));
                Demo.ThermalDetector=Detector;Demo.ThermalAutoGain=AutoGain;Demo.ThermalGainResponse=Response;Demo.ThermalSamplingScale=int32(Scale);
                Demo.ThermalProfile=Profile; Demo.ThermalBlurPixels=Blur; Demo.ThermalContrast=Contrast; Demo.ThermalBackgroundDetail=Detail;
                Demo.InfraredEnabled=Enabled; Demo.InfraredFOV=Fov; Demo.BlackHot=Palette==TEXT("black_hot"); Demo.ThermalNoise=Noise;
            } else {
                double Blur=Demo.VisibleBlur,Grain=Demo.VisibleNoise,Contrast=Demo.VisibleContrast,Saturation=Demo.VisibleSaturation;
                auto Focus=Demo.VisibleFocus;if (!Focus.Read(Args)) return Fail(TEXT("Invalid focus mode, distance or aperture"));
                auto Number=[&](const TCHAR* Key,double& Value,double Low,double High) {
                    return !Args->HasField(Key) || (Args->Values[Key]->Type==EJson::Number && Args->TryGetNumberField(Key,Value) && FMath::IsFinite(Value) && Value>=Low && Value<=High);
                };
                if (!Number(TEXT("blur_px"),Blur,0,3) || !Number(TEXT("noise"),Grain,0,.08) || !Number(TEXT("contrast"),Contrast,.5,1.5) || !Number(TEXT("saturation"),Saturation,0,1.5)) return Fail(TEXT("Invalid visible appearance parameters"));
                for (const TCHAR* Key:{TEXT("blur_px"),TEXT("noise"),TEXT("contrast"),TEXT("saturation")}) if (Args->HasField(Key) && !IsValid(Demo.VisibleInstance)) return Fail(TEXT("Visible camera material is not installed"));
                Demo.VisibleFocus=Focus;Demo.VisibleBlur=Blur;Demo.VisibleNoise=Grain;Demo.VisibleContrast=Contrast;Demo.VisibleSaturation=Saturation;
                Demo.VisibleEnabled=Enabled; Demo.VisibleFOV=Fov;
            }
            if (Sensor==TEXT("infrared")) { Demo.InfraredOffsetCm=Offset;Demo.InfraredBoresight=Rotation; }
            else { Demo.VisibleOffsetCm=Offset;Demo.VisibleBoresight=Rotation; }
            Demo.RefreshSensors();
        } else if (Sensor==TEXT("lidar")) {
            double H,V,R,Rate;
            if (!Args->TryGetNumberField(TEXT("horizontal_fov_deg"),H) || !Args->TryGetNumberField(TEXT("vertical_fov_deg"),V) || !Args->TryGetNumberField(TEXT("range_m"),R) || !Args->TryGetNumberField(TEXT("scan_rate_hz"),Rate)) return Fail(TEXT("All lidar parameters required"));
            if (!FMath::IsFinite(H) || H<.1 || H>60 || !FMath::IsFinite(V) || V<.1 || V>60 || !FMath::IsFinite(R) || R<1 || R>1000 || !FMath::IsFinite(Rate) || Rate<.05 || Rate>10) return Fail(TEXT("Invalid lidar parameters"));
            Demo.LidarHorizontalFov=H; Demo.LidarVerticalFov=V; Demo.LidarRangeMeters=R; Demo.LidarScanRateHz=Rate; Demo.LidarEnabled=Enabled;
            Demo.ScanLidar(); // Disabled scans only clear caches and return before tracing.
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
    else if (Command==TEXT("flight.fixedwing"))
    {
        FString Error;
        if (!Demo.ControlFixedwing(Args,Error)) return Fail(Error);
    }
    else if (Command==TEXT("drone.set_model"))
    {
        FString Model,Error;
        Args->TryGetStringField(TEXT("model"),Model);
        if ((Model==TEXT("fixedwing"))!=(Demo.DroneModel==TEXT("fixedwing"))) return Fail(TEXT("Change airframe in Devices, save and reload the scene"));
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
    else if (Command==TEXT("camera.gt_configure")) {
        auto Policy=Demo.GTSettings;
        for (const auto& Pair:TArray<TPair<FString,bool*>>{{TEXT("keep_partial_occlusion"),&Policy.KeepPartialOcclusion},{TEXT("keep_partial_outside"),&Policy.KeepPartialOutside}}) {
            if (Args->HasField(Pair.Key) && (Args->TryGetField(Pair.Key)->Type!=EJson::Boolean || !Args->TryGetBoolField(Pair.Key,*Pair.Value))) return Fail(TEXT("GT switches must be booleans"));
        }
        double Pixels=Policy.MinVisiblePixels,Fraction=Policy.MinVisibleFraction,MaxFPS=Policy.MaxFPS;
        if (Args->HasField(TEXT("max_fps")) && (Args->Values[TEXT("max_fps")]->Type!=EJson::Number || !Args->TryGetNumberField(TEXT("max_fps"),MaxFPS) || !FMath::IsFinite(MaxFPS) || MaxFPS<.1 || MaxFPS>20)) return Fail(TEXT("max_fps must be finite within [0.1,20]"));
        if (Args->HasField(TEXT("min_visible_pixels")) && (Args->Values[TEXT("min_visible_pixels")]->Type!=EJson::Number || !Args->TryGetNumberField(TEXT("min_visible_pixels"),Pixels))) return Fail(TEXT("Invalid min_visible_pixels"));
        if (Args->HasField(TEXT("min_visible_fraction")) && (Args->Values[TEXT("min_visible_fraction")]->Type!=EJson::Number || !Args->TryGetNumberField(TEXT("min_visible_fraction"),Fraction))) return Fail(TEXT("Invalid min_visible_fraction"));
        if (!FMath::IsFinite(Pixels) || Pixels<1 || Pixels>2073600 || Pixels!=FMath::FloorToDouble(Pixels) || !FMath::IsFinite(Fraction) || Fraction<0 || Fraction>1) return Fail(TEXT("GT pixels must be integer 1..2073600; fraction 0..1"));
        Policy.MinVisiblePixels=int32(Pixels);Policy.MinVisibleFraction=float(Fraction);Policy.MaxFPS=float(MaxFPS);Demo.GTSettings=Policy;
        auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("keep_partial_occlusion"),Policy.KeepPartialOcclusion);R->SetBoolField(TEXT("keep_partial_outside"),Policy.KeepPartialOutside);
        R->SetNumberField(TEXT("min_visible_pixels"),Policy.MinVisiblePixels);R->SetNumberField(TEXT("min_visible_fraction"),Policy.MinVisibleFraction);R->SetNumberField(TEXT("max_fps"),Policy.MaxFPS);return Reply(Id,R);
    }
    else if (Command==TEXT("camera.sample_pair_request") || Command==TEXT("camera.sample_pair_frame")) {
        if (!Demo.VisibleEnabled || !Demo.InfraredEnabled) return Reply(Id,Empty,TEXT("sensor_disabled"),TEXT("Both visible and infrared must be enabled for paired samples"));
        if (Command==TEXT("camera.sample_pair_request")) {
            const double Now=FPlatformTime::Seconds();
            for (int32 I=0;I<2;++I) {
                if (Now-Demo.GTSampleRequestedAt[I]<1./Demo.GTSettings.MaxFPS) return Reply(Id,Empty,TEXT("rate_limited"),TEXT("GT sampling rate limit reached"));
                if (!Demo.GTSampleTokens[I].IsEmpty() && Now-Demo.GTSampleRequestedAt[I]<5) return Reply(Id,Empty,TEXT("sample_busy"),TEXT("A sample is pending"));
            }
            const FString Token=FGuid::NewGuid().ToString(EGuidFormats::Digits);
            for (int32 I=0;I<2;++I) { Demo.GTSampleTokens[I]=Token;Demo.GTSampleRequestedAt[I]=Now; }
            Demo.GTPairPending=true;
            auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("sample_token"),Token);R->SetStringField(TEXT("run_id"),Demo.PlaySessionId);return Reply(Id,R);
        }
        FString Token;
        if (!Args->TryGetStringField(TEXT("sample_token"),Token) || Token.IsEmpty()) return Fail(TEXT("sample_token required"));
        auto Samples=MakeShared<FJsonObject>();double PairTime=-1;
        for (int32 I=0;I<2;++I) {
            FString Metadata;TArray64<uint8> Image;TSharedPtr<FJsonObject> Item;
            if (!Demo.StreamManager || !Demo.StreamManager->GetSample(I==1,Metadata,Image) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Metadata),Item) || !Item || Item->GetStringField(TEXT("sample_token"))!=Token)
                return Reply(Id,Empty,TEXT("frame_unavailable"),TEXT("Paired sample pending or superseded"));
            const double Time=Item->GetNumberField(TEXT("simulation_time_s"));
            if (PairTime>=0 && PairTime!=Time) return Reply(Id,Empty,TEXT("frame_unavailable"),TEXT("Pair capture times do not match"));
            PairTime=Time;Item->SetStringField(TEXT("encoding"),TEXT("jpeg"));Item->SetStringField(TEXT("image_base64"),FBase64::Encode(Image.GetData(),Image.Num()));
            Samples->SetObjectField(I==0?TEXT("visible"):TEXT("infrared"),Item);
        }
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("pair_id"),Token);R->SetStringField(TEXT("run_id"),Demo.PlaySessionId);
        R->SetNumberField(TEXT("simulation_time_s"),PairTime);R->SetObjectField(TEXT("samples"),Samples);return Reply(Id,R);
    }
    else if (Command==TEXT("camera.sample_request") || Command==TEXT("camera.sample_frame")) {
        FString Sensor;
        if (!Args->TryGetStringField(TEXT("sensor"),Sensor) || (Sensor!=TEXT("visible") && Sensor!=TEXT("infrared"))) return Fail(TEXT("sensor must be visible or infrared"));
        const bool IR=Sensor==TEXT("infrared");const int32 Index=IR?1:0;
        if (IR?!Demo.InfraredEnabled:!Demo.VisibleEnabled) return Reply(Id,Empty,TEXT("sensor_disabled"),TEXT("Sensor disabled"));
        if (Command==TEXT("camera.sample_request")) {
            const double Now=FPlatformTime::Seconds();
            if (Demo.GTPairPending && Now-FMath::Max(Demo.GTSampleRequestedAt[0],Demo.GTSampleRequestedAt[1])<5) return Reply(Id,Empty,TEXT("sample_busy"),TEXT("A paired sample is pending"));
            if (Demo.GTPairPending) { Demo.GTPairPending=false;Demo.GTSampleTokens[0].Empty();Demo.GTSampleTokens[1].Empty(); }
            if (Now-Demo.GTSampleRequestedAt[Index]<1./Demo.GTSettings.MaxFPS) return Reply(Id,Empty,TEXT("rate_limited"),TEXT("GT sampling rate limit reached"));
            if (!Demo.GTSampleTokens[Index].IsEmpty() && Now-Demo.GTSampleRequestedAt[Index]<5) return Reply(Id,Empty,TEXT("sample_busy"),TEXT("A sample is pending"));
            Demo.GTSampleTokens[Index]=FGuid::NewGuid().ToString(EGuidFormats::Digits);Demo.GTSampleRequestedAt[Index]=Now;
            auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("sample_token"),Demo.GTSampleTokens[Index]);R->SetStringField(TEXT("run_id"),Demo.PlaySessionId);return Reply(Id,R);
        }
        FString Token;
        if (!Args->TryGetStringField(TEXT("sample_token"),Token) || Token.IsEmpty()) return Fail(TEXT("sample_token required"));
        FString Metadata;TArray64<uint8> Image;TSharedPtr<FJsonObject> R;
        if (!Demo.StreamManager || !Demo.StreamManager->GetSample(IR,Metadata,Image) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Metadata),R) || !R || R->GetStringField(TEXT("sample_token"))!=Token)
            return Reply(Id,Empty,TEXT("frame_unavailable"),TEXT("Sample pending, superseded or expired; request a fresh sample after timeout"));
        R->SetStringField(TEXT("encoding"),TEXT("jpeg"));R->SetStringField(TEXT("image_base64"),FBase64::Encode(Image.GetData(),Image.Num()));return Reply(Id,R);
    }
    else if (Command==TEXT("camera.signal_recording")) {
        bool Enabled=false;
        if (!Args->HasField(TEXT("enabled")) || Args->Values[TEXT("enabled")]->Type!=EJson::Boolean || !Args->TryGetBoolField(TEXT("enabled"),Enabled)) return Fail(TEXT("Boolean enabled required"));
        if (Enabled && (!Demo.HasFacadeInfrared() || !Demo.UsesThermalReadout() || !Demo.InfraredEnabled)) return Fail(TEXT("Enable a supported infrared readout first"));
        Demo.SetSignalRecording(Enabled);return Reply(Id,State());
    }
    else if (Command==TEXT("camera.signal_frame")) {
        TArray<float> Signal;TArray<uint8> Sky,Target;int64 Sequence=0;
        if (!Demo.GetSignalFrame(Signal,Sky,Target,Sequence)) return Reply(Id,Empty,TEXT("frame_unavailable"),TEXT("Enable signal recording and wait for a fresh infrared frame"));
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("device_id"),Demo.GimbalId);R->SetNumberField(TEXT("frame_number"),Sequence);
        R->SetNumberField(TEXT("width"),640);R->SetNumberField(TEXT("height"),512);R->SetStringField(TEXT("encoding"),TEXT("f32_le"));
        R->SetStringField(TEXT("signal_base64"),FBase64::Encode(reinterpret_cast<const uint8*>(Signal.GetData()),Signal.Num()*sizeof(float)));
        R->SetStringField(TEXT("sky_mask_base64"),FBase64::Encode(Sky));R->SetStringField(TEXT("target_mask_base64"),FBase64::Encode(Target));
        R->SetStringField(TEXT("units"),TEXT("normalized FP16-derived proxy before detector filtering/PSF/noise/AGC, not temperature"));return Reply(Id,R);
    }
    else if (Command==TEXT("camera.stream_frame"))
    {
        FString Channel;
        if (!Args->TryGetStringField(TEXT("channel"),Channel) || (Channel!=TEXT("CH1") && Channel!=TEXT("CH2") && Channel!=TEXT("OBS") && Channel!=TEXT("AERIAL") && Channel!=TEXT("AERIAL_IR")))
            return Fail(TEXT("channel must be CH1, CH2, OBS, AERIAL or AERIAL_IR"));
        double RequestedQuality=70;
        Args->TryGetNumberField(TEXT("quality"),RequestedQuality);
        if (!FMath::IsFinite(RequestedQuality) || RequestedQuality<25 || RequestedQuality>95)
            return Fail(TEXT("quality must be within [25,95]"));
        TArray64<uint8> Encoded;
        int32 Width=0,Height=0;
        int64 StreamFrameNumber=0;
        double StreamSimulationTime=0;
        if ((Channel==TEXT("CH1") && !Demo.VisibleEnabled) || (Channel==TEXT("CH2") && !Demo.InfraredEnabled)) return Reply(Id,Empty,TEXT("sensor_disabled"),TEXT("Sensor disabled"));
        if (Channel==TEXT("AERIAL") && (!Demo.OwnsDrone || !Demo.AerialEnabled)) return Reply(Id,Empty,TEXT("sensor_disabled"),TEXT("Aerial camera disabled"));
        const bool Aerial=Channel==TEXT("AERIAL") || Channel==TEXT("AERIAL_IR");
        if (Channel==TEXT("AERIAL_IR") && (!Demo.OwnsDrone || !Demo.AerialIREnabled)) return Reply(Id,Empty,TEXT("sensor_disabled"),TEXT("Aerial infrared disabled"));
        if (!(Aerial?Demo.GetAerialFrame(Encoded,Width,Height,StreamFrameNumber,StreamSimulationTime,Channel==TEXT("AERIAL_IR")):Channel==TEXT("OBS")?Demo.GetObserverFrame(Encoded,Width,Height,StreamFrameNumber,StreamSimulationTime):Demo.GetStreamFrame(Channel==TEXT("CH2"),Encoded,Width,Height,StreamFrameNumber,StreamSimulationTime)))
            return Reply(Id,Empty,TEXT("frame_unavailable"),TEXT("Asynchronous stream frame is warming up"));
        auto R=MakeShared<FJsonObject>();
        R->SetStringField(TEXT("device_id"),Aerial?Demo.DroneId:Channel==TEXT("OBS")?TEXT("observer"):Demo.GimbalId);
        R->SetStringField(TEXT("sensor_id"),Aerial?Demo.DroneId+(Channel==TEXT("AERIAL_IR")?TEXT("/aerial_infrared"):TEXT("/aerial")):Channel==TEXT("OBS")?FString(TEXT("observer/view")):Demo.GimbalId+(Channel==TEXT("CH2")?TEXT("/infrared"):TEXT("/visible")));
        R->SetStringField(TEXT("channel"),Channel);
        R->SetStringField(TEXT("modality"),Aerial?(Channel==TEXT("AERIAL_IR")?TEXT("infrared"):TEXT("visible")):Channel==TEXT("OBS")?TEXT("observer"):Channel==TEXT("CH1")?TEXT("visible"):TEXT("infrared"));
        R->SetStringField(TEXT("run_id"),Demo.PlaySessionId);R->SetStringField(TEXT("scene_id"),Demo.SceneId);
        if (Aerial) {
            R->SetStringField(TEXT("annotation_status"),TEXT("unavailable"));R->SetBoolField(TEXT("training_eligible"),false);
            R->SetStringField(TEXT("annotation_error"),TEXT("Aerial ground-truth labels are not available; raw image requires annotation"));
            const auto* Context=Demo.AerialContexts[Channel==TEXT("AERIAL_IR")?1:0].Find(StreamSimulationTime);
            if (Context && Context->IsValid()) for (const auto& Field:(*Context)->Values) R->SetField(Field.Key,Field.Value);
            else R->SetStringField(TEXT("pose_timing"),TEXT("unavailable"));
        }
        R->SetNumberField(TEXT("frame_number"),StreamFrameNumber);
        R->SetNumberField(TEXT("simulation_time_s"),StreamSimulationTime);
        R->SetNumberField(TEXT("width"),Width);
        R->SetNumberField(TEXT("height"),Height);
        R->SetStringField(TEXT("encoding"),TEXT("jpeg"));
        R->SetNumberField(TEXT("quality"),90);
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
        Demo.ScanLidar();
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
    else if (Command==TEXT("sensor.lidar.get_points") || Command==TEXT("sensor.lidar.get_scan"))
    {
        auto R=State();
        TArray<TSharedPtr<FJsonValue>> Points;
        const bool Full=Command==TEXT("sensor.lidar.get_scan");const int32 MaxPreviewPoints=Full?8192:768;
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
        R->SetNumberField(TEXT("lidar_capture_time_s"),Demo.LastLidarCaptureTime);
        R->SetNumberField(TEXT("lidar_scan_sequence"),Demo.LidarScanSequence);
        R->SetStringField(TEXT("lidar_sensor_id"),Demo.GimbalId+TEXT("/lidar"));
        R->SetStringField(TEXT("lidar_model"),TEXT("ideal rectangular angular-grid snapshot, first collision return; no intensity or rolling scan"));
        R->SetBoolField(TEXT("lidar_downsampled"),Preview.Num()<Count);
        if (Full) {
            TArray<TSharedPtr<FJsonValue>> Ranges;for (float Value:Demo.LastLidarRangesMeters) Ranges.Add(MakeShared<FJsonValueNumber>(Value));
            R->SetArrayField(TEXT("lidar_ranges_m"),Ranges);R->SetNumberField(TEXT("lidar_no_return_value"),-1);
            R->SetStringField(TEXT("lidar_ray_order"),TEXT("row-major pitch -vfov/2..+vfov/2, yaw -hfov/2..+hfov/2"));
        }
        return Reply(Id,R);
    }
    else return Reply(Id,Empty,TEXT("unknown_command"),TEXT("Command is not supported"));
    return Reply(Id,State());
}

void FWiseEyeBridge::Tick()
{
    for (auto It=SlotLeases.CreateIterator();It;++It) if (FPlatformTime::Seconds()>It.Value().Expires) {It.Value().Restore();It.RemoveCurrent();}
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
