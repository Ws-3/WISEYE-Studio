#include "WiseEyeDemo.h"
#include "Camera/CameraComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureRenderTarget2D.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"

void AWiseEyeDemo::InitializeSensors()
{
    if (!RenderTarget) RenderTarget = NewObject<UTextureRenderTarget2D>(this);
    if (!InfraredTarget) InfraredTarget = NewObject<UTextureRenderTarget2D>(this);
    for (UTextureRenderTarget2D* Target : {RenderTarget.Get(),InfraredTarget.Get()})
    {
        Target->RenderTargetFormat = RTF_RGBA8;
        Target->bForceLinearGamma = true;
    }
    RenderTarget->InitAutoFormat(1920,1080);
    InfraredTarget->InitAutoFormat(640,512);
    Capture->TextureTarget = RenderTarget;
    InfraredCapture->TextureTarget = InfraredTarget;
    if (!ThermalMaterial)
        ThermalMaterial = LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WISEYE/Sensors/M_IR_Minimal.M_IR_Minimal"));
    if (ThermalMaterial)
    {
        ThermalInstance = UMaterialInstanceDynamic::Create(ThermalMaterial,this);
        InfraredCapture->PostProcessSettings.AddBlendable(ThermalInstance.Get(),1.f);
        InfraredCapture->PostProcessBlendWeight = 1.f;
    }
    else UE_LOG(LogTemp,Error,TEXT("WISEYE: missing IR material; run configure_sensors.py outside PIE"));
    // The optical mount and physical PTZ should not obstruct their own capture.
    InfraredCapture->HiddenActors = Capture->HiddenActors;
    InfraredCapture->HiddenComponents = Capture->HiddenComponents;
    RefreshSensors();
}

void AWiseEyeDemo::ConfigureThermalActors()
{
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
            if (!Mesh->GetStaticMesh()) continue;
            const FString Name = Mesh->GetStaticMesh()->GetName();
            float Heat = BodyHeat;
            if (IsPTZ) Heat = .55f;
            else if (Blades.Contains(Name)) Heat = RotorHeat;
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
    ConfigureThermalActors();
    Capture->FOVAngle = FieldOfView;
    InfraredCapture->FOVAngle = FieldOfView;
    Camera->SetFieldOfView(FieldOfView);
    Camera->AspectRatio = InfraredMode ? 640.f/512.f : 1920.f/1080.f;
    if (ThermalInstance)
    {
        ThermalInstance->SetScalarParameterValue(TEXT("BlackHot"),BlackHot?1.f:0.f);
        ThermalInstance->SetScalarParameterValue(TEXT("BackgroundHeat"),BackgroundHeat);
        ThermalInstance->SetScalarParameterValue(TEXT("SkyHeat"),SkyHeat);
        ThermalInstance->SetScalarParameterValue(TEXT("NoiseStrength"),ThermalNoise);
        Camera->PostProcessSettings.AddBlendable(ThermalInstance.Get(),InfraredMode?1.f:0.f);
    }
}

void AWiseEyeDemo::ToggleSensorMode()
{
    if (!ThermalInstance) return;
    InfraredMode = !InfraredMode;
    RefreshSensors();
}
void AWiseEyeDemo::ToggleThermalPalette()
{
    BlackHot = !BlackHot;
    RefreshSensors();
}
UTextureRenderTarget2D* AWiseEyeDemo::GetSensorTarget() const
{
    return InfraredMode ? InfraredTarget.Get() : RenderTarget.Get();
}
