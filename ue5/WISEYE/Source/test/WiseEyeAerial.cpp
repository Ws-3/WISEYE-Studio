#include "WiseEyeDemo.h"
#include "WiseEyeStreaming.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Dom/JsonObject.h"
#include "HAL/PlatformTime.h"
#include "Camera/CameraActor.h"
#include "MassLODSubsystem.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/Material.h"
#include "Components/StaticMeshComponent.h"

void AWiseEyeDemo::RecordAerialContext(bool IR) {
    auto* Source=IR?AerialIRCapture.Get():AerialCapture.Get();if (!Source) return;
    auto R=MakeShared<FJsonObject>();
    const auto P=Source->GetComponentLocation();const auto Rotation=Source->GetComponentRotation();
    auto V=[](double X,double Y,double Z){return TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(X),MakeShared<FJsonValueNumber>(Y),MakeShared<FJsonValueNumber>(Z)};};
    R->SetArrayField(TEXT("camera_position_cm"),V(P.X,P.Y,P.Z));R->SetArrayField(TEXT("camera_rotation_pitch_yaw_roll_deg"),V(Rotation.Pitch,Rotation.Yaw,Rotation.Roll));
    R->SetNumberField(TEXT("horizontal_fov_deg"),Source->FOVAngle);R->SetStringField(TEXT("pose_timing"),TEXT("capture_tick"));
    auto* Root=FleetRoot?FleetRoot.Get():this;R->SetObjectField(TEXT("environment"),Root->EnvironmentState());
    R->SetStringField(TEXT("carrier_model_id"),DroneModel);
    auto& History=AerialContexts[IR?1:0];History.Add(GetWorld()->GetTimeSeconds(),R);
    if (History.Num()>64) {TArray<double> Keys;History.GetKeys(Keys);Keys.Sort();History.Remove(Keys[0]);}
}

TSharedPtr<FJsonObject> AWiseEyeDemo::AerialState() const {
    auto R=MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("enabled"),AerialEnabled);R->SetBoolField(TEXT("stabilized"),AerialStabilized);
    R->SetNumberField(TEXT("pitch_deg"),AerialPitch);R->SetNumberField(TEXT("yaw_deg"),AerialYaw);
    R->SetNumberField(TEXT("fov_deg"),AerialFOV);R->SetNumberField(TEXT("sample_hz"),AerialHz);
    AerialFocus.Write(R,AerialFOV);R->SetNumberField(TEXT("vis_blur_px"),AerialVisibleBlur);
    R->SetNumberField(TEXT("width"),1920);R->SetNumberField(TEXT("height"),1080);
    R->SetStringField(TEXT("channel"),TEXT("AERIAL"));R->SetStringField(TEXT("sensor_id"),TEXT("aerial"));
    R->SetBoolField(TEXT("active"),AerialEnabled && FPlatformTime::Seconds()<AerialDemandUntil);
    R->SetBoolField(TEXT("capture_allocated"),IsValid(AerialCapture));
    R->SetStringField(TEXT("mount"),TEXT("body underside, 12 cm below model origin; own airframe hidden"));
    auto IR=MakeShared<FJsonObject>();
    IR->SetBoolField(TEXT("enabled"),AerialIREnabled);IR->SetBoolField(TEXT("active"),AerialIREnabled && FPlatformTime::Seconds()<AerialIRDemandUntil);
    IR->SetBoolField(TEXT("capture_allocated"),IsValid(AerialIRCapture));IR->SetNumberField(TEXT("width"),640);IR->SetNumberField(TEXT("height"),512);
    IR->SetStringField(TEXT("channel"),TEXT("AERIAL_IR"));IR->SetNumberField(TEXT("fov_deg"),AerialIRFOV);
    IR->SetNumberField(TEXT("sample_hz"),AerialIRHz);R->SetNumberField(TEXT("ir_sample_hz"),AerialIRHz);
    IR->SetNumberField(TEXT("blur_px"),AerialIRBlur);IR->SetNumberField(TEXT("noise"),AerialIRNoise);IR->SetBoolField(TEXT("black_hot"),AerialIRBlackHot);
    if (AerialIRStream) {
        const auto Readout=AerialIRStream->ThermalReadoutState();
        IR->SetNumberField(TEXT("agc_low"),Readout.Low);IR->SetNumberField(TEXT("agc_high"),Readout.High);
        IR->SetNumberField(TEXT("readout_ms"),Readout.ProcessingMs);IR->SetNumberField(TEXT("readout_sequence"),Readout.Sequence);
        TArray<TSharedPtr<FJsonValue>> Classes;for (int32 Count:Readout.ClassPixels) Classes.Add(MakeShared<FJsonValueNumber>(Count));
        IR->SetArrayField(TEXT("class_pixels"),Classes);
    }
    IR->SetStringField(TEXT("model"),TEXT("independent HDR synthetic thermal; not radiometric"));
    IR->SetStringField(TEXT("mount"),TEXT("6 cm right of visible, yaw boresight +0.2 deg"));
    R->SetObjectField(TEXT("infrared"),IR);
    R->SetBoolField(TEXT("ir_enabled"),AerialIREnabled);R->SetBoolField(TEXT("ir_black_hot"),AerialIRBlackHot);
    R->SetNumberField(TEXT("ir_fov_deg"),AerialIRFOV);R->SetNumberField(TEXT("ir_blur_px"),AerialIRBlur);R->SetNumberField(TEXT("ir_noise"),AerialIRNoise);
    return R;
}

bool AWiseEyeDemo::ConfigureAerial(const TSharedPtr<FJsonObject>& Args,FString& Error) {
    bool Enabled,Stabilized;double Pitch,Yaw,Fov,Hz;
    if (!OwnsDrone || !Args->TryGetBoolField(TEXT("enabled"),Enabled) || !Args->TryGetBoolField(TEXT("stabilized"),Stabilized) ||
        !Args->TryGetNumberField(TEXT("pitch_deg"),Pitch) || !Args->TryGetNumberField(TEXT("yaw_deg"),Yaw) ||
        !Args->TryGetNumberField(TEXT("fov_deg"),Fov) || !Args->TryGetNumberField(TEXT("sample_hz"),Hz) ||
        !FMath::IsFinite(Pitch) || Pitch< -90 || Pitch>20 || !FMath::IsFinite(Yaw) || FMath::Abs(Yaw)>180 ||
        !FMath::IsFinite(Fov) || Fov<5 || Fov>90 || !FMath::IsFinite(Hz) || Hz<1 || Hz>30) {
        Error=TEXT("Aerial requires drone, enabled/stabilized, pitch -90..20, yaw -180..180, fov 5..90, sample_hz 1..30");return false;
    }
    bool IREnabled=AerialIREnabled,Black=AerialIRBlackHot;double IRFov=AerialIRFOV,Blur=AerialIRBlur,Noise=AerialIRNoise,IRHz=AerialIRHz;
    auto Number=[&](const TCHAR* K,double& V,double L,double H){return !Args->HasField(K) || (Args->Values[K]->Type==EJson::Number && Args->TryGetNumberField(K,V) && FMath::IsFinite(V) && V>=L && V<=H);};
    auto Boolean=[&](const TCHAR* K,bool& V){return !Args->HasField(K) || (Args->Values[K]->Type==EJson::Boolean && Args->TryGetBoolField(K,V));};
    if (!Boolean(TEXT("ir_enabled"),IREnabled) || !Boolean(TEXT("ir_black_hot"),Black) || !Number(TEXT("ir_fov_deg"),IRFov,5,90) || !Number(TEXT("ir_blur_px"),Blur,0,2) || !Number(TEXT("ir_noise"),Noise,0,.1) || !Number(TEXT("ir_sample_hz"),IRHz,1,30)) {Error=TEXT("Invalid aerial IR parameters");return false;}
    auto Focus=AerialFocus;double VisBlur=AerialVisibleBlur;
    if (!Focus.Read(Args) || !Number(TEXT("vis_blur_px"),VisBlur,0,3)) {Error=TEXT("Invalid focus/visible blur settings");return false;}
    AerialFocus=Focus;AerialVisibleBlur=VisBlur;
    AerialIREnabled=IREnabled;AerialIRBlackHot=Black;AerialIRFOV=IRFov;AerialIRBlur=Blur;AerialIRNoise=Noise;AerialIRHz=IRHz;
    if (!IREnabled) AerialIRDemandUntil=0;
    AerialEnabled=Enabled;AerialStabilized=Stabilized;AerialPitch=Pitch;AerialYaw=Yaw;AerialFOV=Fov;AerialHz=Hz;
    if (!Enabled) AerialDemandUntil=0;
    return true;
}

bool AWiseEyeDemo::GetAerialFrame(TArray64<uint8>& Jpeg,int32& Width,int32& Height,int64& Sequence,double& Time,bool IR) {
    if (IR) {AerialIRDemandUntil=FPlatformTime::Seconds()+2;return AerialIRStream && AerialIRStream->GetFrame(true,Jpeg,Width,Height,Sequence,Time);}
    AerialDemandUntil=FPlatformTime::Seconds()+2;
    return AerialStream && AerialStream->GetFrame(false,Jpeg,Width,Height,Sequence,Time);
}

void AWiseEyeDemo::UpdateAerial() {
    const double Now=FPlatformTime::Seconds();
    const bool VIS=AerialEnabled && Now<AerialDemandUntil, IR=AerialIREnabled && Now<AerialIRDemandUntil;
    if (!VIS && AerialCapture) {AerialCapture->DestroyComponent();AerialCapture=nullptr;AerialTarget=nullptr;delete AerialStream;AerialStream=nullptr;}
    if (!IR && AerialIRCapture) {AerialIRCapture->DestroyComponent();AerialIRCapture=nullptr;AerialIRSignal=nullptr;AerialIRTarget=nullptr;AerialIRMaterial=nullptr;delete AerialIRStream;AerialIRStream=nullptr;}
    if (!VIS && !IR) {ReleaseAerial();return;}
    if (VIS && !AerialCapture) {
        AerialTarget=NewObject<UTextureRenderTarget2D>(this);AerialTarget->RenderTargetFormat=RTF_RGBA8;
        AerialTarget->bForceLinearGamma=true;AerialTarget->InitAutoFormat(1920,1080);AerialTarget->TargetGamma=2.2f;
        AerialCapture=NewObject<USceneCaptureComponent2D>(this);AerialCapture->SetupAttachment(GetRootComponent());
        AerialCapture->CaptureSource=ESceneCaptureSource::SCS_FinalColorLDR;AerialCapture->TextureTarget=AerialTarget;
        AerialCapture->bCaptureEveryFrame=false;AerialCapture->bCaptureOnMovement=false;AerialCapture->bAlwaysPersistRenderingState=true;
        AerialCapture->RegisterComponent();AerialStream=new FWiseEyeStreamManager();AerialStream->SetEnabled(true,false);
    }
    if (!AerialViewer) {AerialViewer=GetWorld()->SpawnActor<ACameraActor>();if (AerialViewer) if (auto* LOD=GetWorld()->GetSubsystem<UMassLODSubsystem>()) LOD->RegisterActorViewer(*AerialViewer);}
    const FQuat Physical=Drone->GetActorQuat()*DynamicsVisualRotationOffset.Quaternion().Inverse();
    const FQuat Mount=FRotator(AerialPitch,AerialYaw,0).Quaternion();
    const FQuat Rotation=AerialStabilized?FRotator(AerialPitch,Physical.Rotator().Yaw+AerialYaw,0).Quaternion():Physical*Mount;
    const FVector Position=Drone->GetActorLocation()+Physical.RotateVector(FVector(0,0,-12));
    const auto* Root=FleetRoot?FleetRoot.Get():this;
    if (IR && !AerialIRCapture) {
        if (auto* Material=Root->ThermalMaterial.Get()) {
            AerialIRSignal=NewObject<UTextureRenderTarget2D>(this);AerialIRSignal->RenderTargetFormat=RTF_RGBA16f;AerialIRSignal->bForceLinearGamma=true;AerialIRSignal->TargetGamma=1;AerialIRSignal->InitAutoFormat(640,512);
            AerialIRTarget=NewObject<UTextureRenderTarget2D>(this);AerialIRTarget->RenderTargetFormat=RTF_RGBA8;AerialIRTarget->bForceLinearGamma=true;AerialIRTarget->InitAutoFormat(640,512);
            AerialIRCapture=NewObject<USceneCaptureComponent2D>(this);AerialIRCapture->SetupAttachment(GetRootComponent());AerialIRCapture->TextureTarget=AerialIRSignal;
            AerialIRCapture->CaptureSource=ESceneCaptureSource::SCS_FinalColorLDR;AerialIRCapture->bCaptureEveryFrame=false;AerialIRCapture->bCaptureOnMovement=false;AerialIRCapture->bAlwaysPersistRenderingState=true;
            AerialIRCapture->ShowFlags.SetTemporalAA(false);AerialIRCapture->ShowFlags.SetMotionBlur(false);
            AerialIRMaterial=UMaterialInstanceDynamic::Create(Material,this);AerialIRCapture->PostProcessSettings.AddBlendable(AerialIRMaterial.Get(),1);AerialIRCapture->PostProcessBlendWeight=1;AerialIRCapture->RegisterComponent();
            AerialIRStream=new FWiseEyeStreamManager();AerialIRStream->SetEnabled(false,true);
        }
    }
    if (AerialIRCapture && IR) {
        AerialIRCapture->HiddenActors.Empty();AerialIRCapture->HideActorComponents(Drone);
        TArray<AActor*> Hidden;Drone->GetAttachedActors(Hidden,true,true);for (auto* P:Hidden) AerialIRCapture->HideActorComponents(P);
        for (auto Rig:Root->FleetRigs) for (auto Lamp:Rig->NavigationLamps) if (Lamp) AerialIRCapture->HideComponent(Lamp);
        if (IsValid(Root->PlacementPreview)) AerialIRCapture->HideActorComponents(Root->PlacementPreview);
        AerialIRCapture->SetWorldLocationAndRotation(Position+Physical.RotateVector(FVector(0,6,0)),Rotation*FRotator(0,.2f,0).Quaternion());AerialIRCapture->FOVAngle=AerialIRFOV;
        auto* M=AerialIRMaterial.Get();
        M->SetScalarParameterValue(TEXT("Reference"),1);M->SetScalarParameterValue(TEXT("Classified"),1);M->SetScalarParameterValue(TEXT("Facade"),1);M->SetScalarParameterValue(TEXT("Enhanced"),1);
        M->SetScalarParameterValue(TEXT("BlackHot"),AerialIRBlackHot?1:0);M->SetScalarParameterValue(TEXT("NoiseStrength"),0);M->SetScalarParameterValue(TEXT("Contrast"),1.1);M->SetScalarParameterValue(TEXT("BackgroundDetail"),.65);
        M->SetScalarParameterValue(TEXT("BackgroundHeat"),Root->BackgroundHeat);M->SetScalarParameterValue(TEXT("SkyHeat"),Root->SkyHeat);
        const float Hour=Root->EnvironmentTimeOverride?Root->EnvironmentHour:12;
        const float Day=FMath::Clamp(FMath::Sin((Hour-6)*PI/12)*1.8f,0.f,1.f);
        M->SetScalarParameterValue(TEXT("DayWeight"),Day);
        M->SetVectorParameterValue(TEXT("BatterySpot"),FLinearColor(0,0,.001,0));for(int I=0;I<4;++I) M->SetVectorParameterValue(FName(*FString::Printf(TEXT("MotorSpot%d"),I)),FLinearColor(0,0,.001,0));
        WiseEyeThermal::DetectorSettings D;D.Stable=true;D.Facade=true;D.SensorNoise=true;D.Noise=AerialIRNoise;
        // Independent aerial display calibration: ground-filled night views
        // should not inherit the sky-heavy PTZ curve's crushed midtones.
        // Signal cooling/material response stays in the thermal material.
        D.BackgroundMid=FMath::Lerp(.36f,.60f,Day);D.BackgroundSlope=4.f;
        AerialIRStream->ConfigureThermalReadout(true,true,AerialIRBlackHot,1,1.1,AerialIRBlur,true,D);
        const bool Due=Now>=AerialIRNext;if (Due) {RecordAerialContext(true);AerialIRCapture->CaptureScene();AerialIRNext=Now+1./AerialIRHz;}
        AerialIRStream->Tick(nullptr,Due?AerialIRSignal.Get():nullptr,GetWorld()->GetTimeSeconds(),nullptr,AerialIRTarget);
    }
    if (AerialViewer) AerialViewer->SetActorLocationAndRotation(Position,Rotation);
    if (!VIS) return;
    AerialCapture->HiddenActors.Empty();AerialCapture->HideActorComponents(Drone);
    TArray<AActor*> Parts;Drone->GetAttachedActors(Parts,true,true);
    for (auto* Part:Parts) AerialCapture->HideActorComponents(Part);
    AerialCapture->SetWorldLocationAndRotation(Drone->GetActorLocation()+Physical.RotateVector(FVector(0,0,-12)),Rotation);
    if (AerialViewer) AerialViewer->SetActorLocationAndRotation(AerialCapture->GetComponentLocation(),Rotation);
    AerialCapture->FOVAngle=AerialFOV;
    if (IsValid(Root->PlacementPreview)) AerialCapture->HideActorComponents(Root->PlacementPreview);
    // Reuse visible appearance / weather response, never copy thermal blendables.
    if (Root->Capture) {AerialCapture->PostProcessSettings=Root->Capture->PostProcessSettings;AerialCapture->PostProcessBlendWeight=1;}
    auto& PP=AerialCapture->PostProcessSettings;
    if (!AerialVisibleMaterial && Root->VisibleInstance) AerialVisibleMaterial=UMaterialInstanceDynamic::Create(Root->VisibleInstance->GetMaterial(),this);
    if (AerialVisibleMaterial) {
        PP.WeightedBlendables.Array.RemoveAll([Root](const FWeightedBlendable& B){return B.Object==Root->VisibleInstance;});
        PP.AddBlendable(AerialVisibleMaterial.Get(),1);
        AerialVisibleMaterial->SetScalarParameterValue(TEXT("BlurPixels"),AerialVisibleBlur);
        AerialVisibleMaterial->SetScalarParameterValue(TEXT("Noise"),Root->VisibleNoise);
        AerialVisibleMaterial->SetScalarParameterValue(TEXT("Contrast"),Root->VisibleContrast);
        AerialVisibleMaterial->SetScalarParameterValue(TEXT("Saturation"),Root->VisibleSaturation);
        AerialVisibleMaterial->SetScalarParameterValue(TEXT("LowLight"),Root->EnvironmentNightAmount());
    }
    ApplyVisibleFocus(AerialCapture,AerialFocus);
    PP.bOverride_ReflectionMethod=PerformanceProfile!=TEXT("quality");PP.ReflectionMethod=EReflectionMethod::ScreenSpace;
    PP.bOverride_DynamicGlobalIlluminationMethod=PerformanceProfile==TEXT("economy");PP.DynamicGlobalIlluminationMethod=EDynamicGlobalIlluminationMethod::None;
    const bool Due=Now>=AerialNext;
    if (Due) {RecordAerialContext(false);AerialCapture->CaptureScene();AerialNext=Now+1./AerialHz;}
    AerialStream->Tick(Due?AerialTarget.Get():nullptr,nullptr,GetWorld()->GetTimeSeconds());
}

void AWiseEyeDemo::ReleaseAerial() {
    if (AerialViewer) {
        if (auto* LOD=GetWorld()->GetSubsystem<UMassLODSubsystem>()) LOD->UnregisterActorViewer(*AerialViewer);
        AerialViewer->Destroy();AerialViewer=nullptr;
    }
    if (AerialCapture) {AerialCapture->DestroyComponent();AerialCapture=nullptr;AerialTarget=nullptr;}
    delete AerialStream;AerialStream=nullptr;
    if (AerialIRCapture) AerialIRCapture->DestroyComponent();AerialIRCapture=nullptr;AerialIRSignal=nullptr;AerialIRTarget=nullptr;AerialIRMaterial=nullptr;
    delete AerialIRStream;AerialIRStream=nullptr;
    AerialContexts[0].Empty();AerialContexts[1].Empty();
}
