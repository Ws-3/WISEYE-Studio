#include "WiseEyeDemo.h"
#include "Camera/CameraComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureRenderTarget2D.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "WiseEyeThermalMath.h"
#include "WiseEyeStreaming.h"
#include "WiseEyeEventCamera.h"
#include "Dom/JsonObject.h"

void AWiseEyeDemo::InitializeSensors()
{
    // Preserve the calibrated lens-head anchor from existing maps, then give
    // each camera a sibling mount. The UE view follows the selected camera.
    OpticalMount->SetRelativeTransform(Camera->GetRelativeTransform());
    Camera->AttachToComponent(OpticalMount,FAttachmentTransformRules::KeepRelativeTransform);
    Camera->SetRelativeTransform(FTransform::Identity);
    Capture->AttachToComponent(OpticalMount,FAttachmentTransformRules::KeepWorldTransform);
    InfraredCapture->AttachToComponent(OpticalMount,FAttachmentTransformRules::KeepWorldTransform);
    LidarMount->AttachToComponent(OpticalMount,FAttachmentTransformRules::KeepRelativeTransform);
    VisibleFOV=InfraredFOV=FieldOfView;
    if (!RenderTarget) RenderTarget = NewObject<UTextureRenderTarget2D>(this);
    if (!InfraredTarget) InfraredTarget = NewObject<UTextureRenderTarget2D>(this);
    for (UTextureRenderTarget2D* Target : {RenderTarget.Get(),InfraredTarget.Get()})
    {
        Target->RenderTargetFormat = RTF_RGBA8;
        Target->bForceLinearGamma = true;
    }
    RenderTarget->InitAutoFormat(1920,1080);
    // FinalColorLDR bytes are displayed/encoded as sRGB, rather than linear light.
    RenderTarget->TargetGamma = 2.2f;
    InfraredTarget->InitAutoFormat(640,512);
    Capture->TextureTarget = RenderTarget;
    InfraredCapture->TextureTarget = InfraredTarget;
    // Conservative surveillance-camera response inspired by daylight reference
    // photographs. No crop/warp or spatial blur: tiny targets retain their GT.
    // Weather remains world-controlled, rather than baking haze into every day.
    auto& VisiblePP=Capture->PostProcessSettings;
    Capture->PostProcessBlendWeight=1.f;
    VisiblePP.bOverride_ColorSaturation=true;VisiblePP.ColorSaturation=FVector4(1,1,1,.88f);
    VisiblePP.bOverride_ColorContrast=true;VisiblePP.ColorContrast=FVector4(1,1,1,.96f);
    VisiblePP.bOverride_ColorGamma=true;VisiblePP.ColorGamma=FVector4(1,1,1,1.03f);
    VisiblePP.bOverride_BloomIntensity=true;VisiblePP.BloomIntensity=.08f;
    VisiblePP.bOverride_VignetteIntensity=true;VisiblePP.VignetteIntensity=.08f;
    VisiblePP.bOverride_FilmGrainIntensity=true;VisiblePP.FilmGrainIntensity=.04f;
    // Independent asset keeps the original material available for rollback.
    if (auto* Facade = LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WISEYE/Sensors/M_IR_Facade.M_IR_Facade"))) {
        ThermalMaterial=Facade;ThermalProfile=TEXT("facade");ThermalDetector.Stable=true;ThermalContrast=1.1f;
    } else if (auto* Classified = LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WISEYE/Sensors/M_IR_Classified.M_IR_Classified"))) {
        ThermalMaterial=Classified;ThermalProfile=TEXT("reference");
    } else if (auto* Reference = LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WISEYE/Sensors/M_IR_Reference.M_IR_Reference"))) {
        ThermalMaterial=Reference;ThermalProfile=TEXT("reference");
    } else if (auto* Experimental = LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WISEYE/Sensors/M_IR_Experimental.M_IR_Experimental")))
        ThermalMaterial = Experimental;
    if (!ThermalMaterial)
        ThermalMaterial = LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WISEYE/Sensors/M_IR_Minimal.M_IR_Minimal"));
    if (ThermalMaterial && ThermalMaterial->GetName()!=TEXT("M_IR_Experimental") && !HasReferenceInfrared()) ThermalProfile=TEXT("legacy");
    if (ThermalMaterial)
    {
        ThermalInstance = UMaterialInstanceDynamic::Create(ThermalMaterial,this);
        InfraredCapture->PostProcessSettings.AddBlendable(ThermalInstance.Get(),1.f);
        InfraredCapture->PostProcessBlendWeight = 1.f;
    }
    else UE_LOG(LogTemp,Error,TEXT("WISEYE: missing IR material; run configure_sensors.py outside PIE"));
    // The optical mount and physical PTZ should not obstruct their own capture.
    AActor* Mount=this;while (Mount->GetAttachParentActor()) Mount=Mount->GetAttachParentActor();
    TArray<AActor*> Parts={Mount};Mount->GetAttachedActors(Parts,false,true);
    TArray<AActor*> Targets;
    if (IsValid(Drone)) { Targets.Add(Drone);Drone->GetAttachedActors(Targets,false,true); }
    for (auto* Part:Parts) if (Part && !Targets.Contains(Part)) Capture->HiddenActors.AddUnique(Part);
    InfraredCapture->HiddenActors = Capture->HiddenActors;
    InfraredCapture->HiddenComponents = Capture->HiddenComponents;
    RefreshSensors();
}

void AWiseEyeDemo::ConfigureThermalActors()
{
    if (!OwnsDrone || !IsValid(Drone)) return;
    TArray<AActor*> DroneActors;
    DroneActors.Add(Drone);
    Drone->GetAttachedActors(DroneActors,false,true);
    const TSet<FString> Blades = {TEXT("Mesh_ncl_92"),TEXT("Mesh_ncl_94"),TEXT("Mesh_ncl_110"),TEXT("Mesh_ncl_111"),TEXT("Mesh_ncl_119"),TEXT("Mesh_ncl_120"),TEXT("Mesh_ncl_99"),TEXT("Mesh_ncl_100")};
    for (TActorIterator<AActor> It(GetWorld()); It; ++It)
    {
        AActor* Actor = *It;
        const bool IsDrone = DroneActors.Contains(Actor);
        const bool IsPTZ = Actor->ActorHasTag(TEXT("WISEYE_ThermalPTZ"));
        if (!IsDrone && !IsPTZ) continue;
        TArray<UStaticMeshComponent*> Meshes;
        Actor->GetComponents(Meshes);
        for (UStaticMeshComponent* Mesh : Meshes)
        {
            if (!Mesh->GetStaticMesh() || Mesh->ComponentHasTag(TEXT("NavigationLamp"))) continue;
            const FString Name = Mesh->GetStaticMesh()->GetName();
            float Heat = BodyHeat;
            if (IsPTZ) Heat = .55f;
            else if (Blades.Contains(Name) || Name.StartsWith(TEXT("AvataRotor")) || Mesh->ComponentHasTag(TEXT("RotorBlur"))) Heat = RotorHeat;
            else
            {
                FString Prefix, Number;
                if (Name.Split(TEXT("Mesh_ncl_"),&Prefix,&Number))
                {
                    const int32 Index = FCString::Atoi(*Number);
                    if (Index>=89 && Index<=128) Heat = MotorHeat;
                }
            }
            Mesh->SetRenderCustomDepth(true);
            Mesh->SetCustomDepthStencilValue(FMath::Clamp(FMath::RoundToInt(Heat*255.f),1,255));
        }
    }
}

void AWiseEyeDemo::RefreshSensors()
{
    UpdateSensorTransforms();
    ConfigureThermalActors();
    FieldOfView=InfraredMode?InfraredFOV:VisibleFOV;
    Capture->FOVAngle = VisibleFOV;
    InfraredCapture->FOVAngle = InfraredFOV;
    Capture->bCaptureEveryFrame=false;
    InfraredCapture->bCaptureEveryFrame=false;
    Capture->bCaptureOnMovement=false;InfraredCapture->bCaptureOnMovement=false;
    if (StreamManager) StreamManager->SetEnabled(VisibleEnabled,InfraredEnabled);
    Capture->SetComponentTickEnabled(VisibleEnabled);
    InfraredCapture->SetComponentTickEnabled(InfraredEnabled);
    Camera->SetFieldOfView(FieldOfView);
    Camera->AspectRatio = InfraredMode ? 640.f/512.f : 1920.f/1080.f;
    if (ThermalInstance)
    {
        ThermalInstance->SetScalarParameterValue(TEXT("BlackHot"),BlackHot?1.f:0.f);
        ThermalInstance->SetScalarParameterValue(TEXT("BackgroundHeat"),BackgroundHeat);
        ThermalInstance->SetScalarParameterValue(TEXT("SkyHeat"),SkyHeat);
        ThermalInstance->SetScalarParameterValue(TEXT("NoiseStrength"),HasFacadeInfrared() && UsesThermalReadout()?0.f:ThermalNoise);
        const bool Reference=UsesThermalReadout();
        ThermalInstance->SetScalarParameterValue(TEXT("Enhanced"),ThermalProfile!=TEXT("legacy")?1.f:0.f);
        ThermalInstance->SetScalarParameterValue(TEXT("Reference"),Reference?1.f:0.f);
        ThermalInstance->SetScalarParameterValue(TEXT("Classified"),(ThermalProfile==TEXT("classified") || ThermalProfile==TEXT("facade"))?1.f:0.f);
        ThermalInstance->SetScalarParameterValue(TEXT("Facade"),ThermalProfile==TEXT("facade")?1.f:0.f);
        ThermalInstance->SetScalarParameterValue(TEXT("BlurPixels"),ThermalBlurPixels);
        ThermalInstance->SetScalarParameterValue(TEXT("Contrast"),ThermalContrast);
        ThermalInstance->SetScalarParameterValue(TEXT("BackgroundDetail"),ThermalBackgroundDetail);
        Camera->PostProcessSettings.RemoveBlendable(ThermalInstance.Get());
        if (ThermalDisplayInstance) Camera->PostProcessSettings.RemoveBlendable(ThermalDisplayInstance.Get());
        if (Reference) {
            if (!ThermalDisplayInstance) ThermalDisplayInstance=UMaterialInstanceDynamic::Create(ThermalMaterial,this);
            // Main UE optical view uses the same processed detector image as HUD/export/JPEG.
            ThermalDisplayInstance->SetScalarParameterValue(TEXT("DisplayReadout"),1.f);
            ThermalDisplayInstance->SetTextureParameterValue(TEXT("DisplayTexture"),InfraredTarget);
        }
        Camera->PostProcessSettings.AddBlendable(Reference?ThermalDisplayInstance.Get():ThermalInstance.Get(),InfraredMode && InfraredEnabled?1.f:0.f);
        if (Reference) {
            if (!InfraredSignalTarget) {
                InfraredSignalTarget=NewObject<UTextureRenderTarget2D>(this);
                InfraredSignalTarget->RenderTargetFormat=RTF_RGBA16f;
                InfraredSignalTarget->bForceLinearGamma=true;InfraredSignalTarget->TargetGamma=1.f;
            }
            if (InfraredSignalTarget->SizeX!=640*ThermalSamplingScale || InfraredSignalTarget->SizeY!=512*ThermalSamplingScale)
                InfraredSignalTarget->InitAutoFormat(640*ThermalSamplingScale,512*ThermalSamplingScale);
            InfraredCapture->TextureTarget=InfraredSignalTarget;
            InfraredCapture->ShowFlags.SetTemporalAA(false);
            InfraredCapture->ShowFlags.SetMotionBlur(false);
        } else {
            InfraredCapture->TextureTarget=InfraredTarget;
            InfraredCapture->ShowFlags.SetTemporalAA(true);
        }
    }
}

void AWiseEyeDemo::UpdateSensorTransforms()
{
    const FTransform Mount=OpticalMount->GetComponentTransform();
    if (EventCapture) EventCapture->SetWorldLocationAndRotation(Mount.TransformPositionNoScale(EventOffsetCm),Mount.GetRotation()*EventBoresight.Quaternion());
    Capture->SetWorldLocationAndRotation(Mount.TransformPositionNoScale(VisibleOffsetCm),Mount.GetRotation()*VisibleBoresight.Quaternion());
    InfraredCapture->SetWorldLocationAndRotation(Mount.TransformPositionNoScale(InfraredOffsetCm),Mount.GetRotation()*InfraredBoresight.Quaternion());
    const auto* Selected=InfraredMode?InfraredCapture.Get():Capture.Get();
    Camera->SetWorldLocationAndRotation(Selected->GetComponentLocation(),Selected->GetComponentQuat());
}

bool AWiseEyeDemo::HasReferenceInfrared() const
{
    return ThermalMaterial && (ThermalMaterial->GetName()==TEXT("M_IR_Reference") || HasClassifiedInfrared());
}

void AWiseEyeDemo::RefreshEventSensor()
{
    if (StreamManager) StreamManager->ConfigureEvent(false,EventOn,EventOff,EventRefractoryUs);
    if (!EventEnabled) {
        if (EventCapture) EventCapture->DestroyComponent();
        EventCapture=nullptr;EventTarget=nullptr;NextEventCapture=0;return;
    }
    if (!EventCapture) {
        EventTarget=NewObject<UTextureRenderTarget2D>(this);EventTarget->RenderTargetFormat=RTF_RGBA16f;
        EventTarget->bForceLinearGamma=true;EventTarget->TargetGamma=1;EventTarget->InitAutoFormat(640,480);
        EventCapture=NewObject<USceneCaptureComponent2D>(this);EventCapture->SetupAttachment(OpticalMount);
        EventCapture->TextureTarget=EventTarget;EventCapture->CaptureSource=ESceneCaptureSource::SCS_SceneColorHDR;
        EventCapture->bCaptureEveryFrame=false;EventCapture->bCaptureOnMovement=false;EventCapture->bAlwaysPersistRenderingState=true;
        EventCapture->ShowFlags.SetTemporalAA(false);EventCapture->ShowFlags.SetMotionBlur(false);
        EventCapture->HiddenActors=Capture->HiddenActors;EventCapture->HiddenComponents=Capture->HiddenComponents;
        EventCapture->RegisterComponent();
    }
    EventCapture->FOVAngle=EventFOV;
    auto& PP=EventCapture->PostProcessSettings;
    PP.bOverride_AutoExposureMinBrightness=true;PP.bOverride_AutoExposureMaxBrightness=true;
    PP.AutoExposureMinBrightness=PP.AutoExposureMaxBrightness=1;
    PP.bOverride_DynamicGlobalIlluminationMethod=true;PP.DynamicGlobalIlluminationMethod=EDynamicGlobalIlluminationMethod::None;
    PP.bOverride_ReflectionMethod=true;PP.ReflectionMethod=EReflectionMethod::ScreenSpace;
    UpdateSensorTransforms();NextEventCapture=0;
    if (StreamManager) StreamManager->ConfigureEvent(true,EventOn,EventOff,EventRefractoryUs);
}

TSharedPtr<FJsonObject> AWiseEyeDemo::EventSensorState() const
{
    auto R=StreamManager?StreamManager->EventCamera->State():MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("enabled"),EventEnabled);R->SetNumberField(TEXT("width_px"),640);R->SetNumberField(TEXT("height_px"),480);
    R->SetBoolField(TEXT("capture_active"),EventEnabled && IsValid(EventCapture) && IsValid(EventTarget));
    R->SetNumberField(TEXT("fov_deg"),EventFOV);R->SetNumberField(TEXT("sample_hz"),EventSampleHz);
    R->SetNumberField(TEXT("positive_threshold"),EventOn);R->SetNumberField(TEXT("negative_threshold"),EventOff);
    R->SetNumberField(TEXT("refractory_us"),EventRefractoryUs);R->SetBoolField(TEXT("extrinsics_supported"),true);
    R->SetNumberField(TEXT("mount_x_cm"),EventOffsetCm.X);R->SetNumberField(TEXT("mount_y_cm"),EventOffsetCm.Y);R->SetNumberField(TEXT("mount_z_cm"),EventOffsetCm.Z);
    R->SetNumberField(TEXT("boresight_pitch_deg"),EventBoresight.Pitch);R->SetNumberField(TEXT("boresight_yaw_deg"),EventBoresight.Yaw);R->SetNumberField(TEXT("boresight_roll_deg"),EventBoresight.Roll);
    return R;
}
bool AWiseEyeDemo::HasClassifiedInfrared() const { return ThermalMaterial && (ThermalMaterial->GetName()==TEXT("M_IR_Classified") || HasFacadeInfrared()); }
bool AWiseEyeDemo::HasFacadeInfrared() const { return ThermalMaterial && ThermalMaterial->GetName()==TEXT("M_IR_Facade"); }
FWiseEyeThermalReadoutState AWiseEyeDemo::GetThermalReadout() const
{
    return StreamManager?StreamManager->ThermalReadoutState():FWiseEyeThermalReadoutState{};
}
void AWiseEyeDemo::SetSignalRecording(bool Enabled) { if (StreamManager) StreamManager->SetSignalRecording(Enabled); }
bool AWiseEyeDemo::GetSignalFrame(TArray<float>& Signal,TArray<uint8>& Sky,TArray<uint8>& Target,int64& Sequence) const {
    return StreamManager && StreamManager->GetSignalFrame(Signal,Sky,Target,Sequence);
}

void AWiseEyeDemo::UpdateThermalState(float Dt)
{
    if (!OwnsDrone) return;
    ThermalPower=0;
    if (FlightBackend==EWiseEyeFlightBackend::ProjectAirSim) {
        if (RotorTelemetryValid && FPlatformTime::Seconds()-RotorTelemetryTime<1.)
            for (float RPM:MotorRPMs) ThermalPower+=FMath::Square(RPM/12000.f)/4.f;
    } else if (RotorsRunning) ThermalPower=FMath::Square(RotorRPM/12000.f);
    ThermalPower=FMath::Clamp(ThermalPower,0.f,1.f);
    ThermalHeat.Step(ThermalPower,Dt);
    BodyHeat=.38f+.08f*ThermalHeat.Battery;
    MotorHeat=.39f+.50f*ThermalHeat.Motor;
    RotorHeat=.32f+.04f*ThermalPower;
    ThermalNextClassify-=Dt;
    if (ThermalNextClassify<=0) { ConfigureThermalActors();ThermalNextClassify=.25f; }
}

void AWiseEyeDemo::UpdateThermalProjection()
{
    if (!ThermalInstance || !UsesThermalReadout()) return;
    const AWiseEyeDemo* Root=FleetRoot?FleetRoot.Get():this;
    const AWiseEyeDemo* Target=Root->FindDevice(TrackingTargetId);
    if (!Target || !Target->Drone) Target=Root;
    // Cameras inherit imported rig scale. Projection/depth/spot radii use world
    // centimetres, so remove rotation/translation without dividing by that scale.
    const FVector Battery=Target->Drone->GetActorTransform().TransformPositionNoScale(FVector(Target->DroneModel==TEXT("avata")?-2.f:-5.f,0,3));
    const FVector P=InfraredCapture->GetComponentTransform().InverseTransformPositionNoScale(Battery);
    const float Tan=FMath::Tan(FMath::DegreesToRadians(InfraredFOV)*.5f);
    const float Den=FMath::Max(1.f,float(P.X))*2*Tan;
    const float BatteryRadius=Target->DroneModel==TEXT("avata")?3.f:4.f;
    ThermalInstance->SetVectorParameterValue(TEXT("BatterySpot"),FLinearColor(.5f+P.Y/Den,.5f-P.Z/(Den*.8f),FMath::Max(.6f/640,BatteryRadius/Den),P.X>0?1.f:0.f));
    ThermalInstance->SetScalarParameterValue(TEXT("BodyCode"),FMath::RoundToInt(Target->BodyHeat*255.f));
    ThermalInstance->SetScalarParameterValue(TEXT("BatteryWarmth"),Target->ThermalHeat.Battery);
    if (HasClassifiedInfrared()) {
        const float Hour=Root->EnvironmentTimeOverride?Root->EnvironmentHour:12.f;
        const float Day=FMath::Clamp(FMath::Sin((Hour-6.f)*PI/12.f)*1.8f,0.f,1.f);
        ThermalInstance->SetScalarParameterValue(TEXT("DayWeight"),Day);
        ThermalInstance->SetScalarParameterValue(TEXT("TargetDepth"),float(P.X));
        ThermalInstance->SetScalarParameterValue(TEXT("TargetAvata"),Target->DroneModel==TEXT("avata")?1.f:0.f);
        ThermalInstance->SetScalarParameterValue(TEXT("MotorWarmth"),Target->ThermalHeat.Motor);
        for (int I=0;I<4;++I) {
            FLinearColor Spot(0,0,.001f,0);
            if (Target->DroneModel==TEXT("avata") && Target->AvataRotors.IsValidIndex(I) && IsValid(Target->AvataRotors[I])) {
                const FVector Motor=InfraredCapture->GetComponentTransform().InverseTransformPositionNoScale(Target->AvataRotors[I]->GetComponentLocation());
                const float D=FMath::Max(1.f,float(Motor.X))*2*Tan;
                Spot=FLinearColor(.5f+Motor.Y/D,.5f-Motor.Z/(D*.8f),FMath::Max(.45f/640,1.5f/D),Motor.X>0?1.f:0.f);
            }
            else if (Target->DroneModel==TEXT("mavic3") && Target->Rotors.IsValidIndex(I) && IsValid(Target->Rotors[I])) {
                const FVector Motor=InfraredCapture->GetComponentTransform().InverseTransformPositionNoScale(Target->Rotors[I]->GetActorLocation()-FVector(0,0,1));
                const float D=FMath::Max(1.f,float(Motor.X))*2*Tan;
                Spot=FLinearColor(.5f+Motor.Y/D,.5f-Motor.Z/(D*.8f),FMath::Max(.45f/640,1.6f/D),Motor.X>0?1.f:0.f);
            }
            ThermalInstance->SetVectorParameterValue(FName(*FString::Printf(TEXT("MotorSpot%d"),I)),Spot);
        }
    }
}

void AWiseEyeDemo::ToggleSensorMode()
{
    if (!FleetChild) { auto* Selected=FindDevice(ControlledGimbalId); if (Selected && Selected!=this) { Selected->ToggleSensorMode(); return; } }
    if (!ThermalInstance) return;
    InfraredMode = !InfraredMode;
    ActiveSensor = InfraredMode ? TEXT("infrared") : TEXT("visible");
    RefreshSensors();
}
void AWiseEyeDemo::ToggleThermalPalette()
{
    if (!FleetChild) { auto* Selected=FindDevice(ControlledGimbalId); if (Selected && Selected!=this) { Selected->ToggleThermalPalette(); return; } }
    BlackHot = !BlackHot;
    RefreshSensors();
}
UTextureRenderTarget2D* AWiseEyeDemo::GetSensorTarget() const
{
    if (InfraredMode?!InfraredEnabled:!VisibleEnabled) return nullptr;
    return InfraredMode ? InfraredTarget.Get() : RenderTarget.Get();
}
