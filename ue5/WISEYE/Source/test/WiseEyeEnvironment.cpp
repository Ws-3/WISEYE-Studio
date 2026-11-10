#include "WiseEyeDemo.h"
#include "Camera/CameraComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Dom/JsonObject.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/SkyLight.h"
#include "EngineUtils.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Components/VolumetricCloudComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Camera/CameraActor.h"
#include "Components/StaticMeshComponent.h"
#include "Particles/ParticleSystemComponent.h"
#include "Components/InstancedStaticMeshComponent.h"

void AWiseEyeDemo::InitializeEnvironment()
{
    if (EnvironmentInitialized) { EnsureEnvironmentRainResources();return; }
    EnvironmentInitialized=true;
    EnvironmentCloudMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WISEYE/Sensors/M_Cloud_Runtime.M_Cloud_Runtime"));
    EnvironmentRainMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WISEYE/Sensors/M_RainStreaks.M_RainStreaks"));
    for (TActorIterator<AActor> It(GetWorld());It;++It) {
        TArray<UDirectionalLightComponent*> Lights;It->GetComponents(Lights);
        for (auto* Light : Lights)
            if (Light && (!EnvironmentSun.IsValid() || Light->Intensity>EnvironmentSun->Intensity)) EnvironmentSun=Light;
        TArray<USkyLightComponent*> SkyLights;It->GetComponents(SkyLights);
        for (auto* Light : SkyLights) { EnvironmentSkyLights.Add(Light);EnvironmentSkyIntensities.Add(Light->Intensity); }
        TArray<UStaticMeshComponent*> Meshes;It->GetComponents(Meshes);
        for (auto* Mesh:Meshes) if (Mesh && Mesh->GetStaticMesh()) {
            const FString Name=Mesh->GetStaticMesh()->GetName().ToLower();
            if (Name==TEXT("sm_dome") || Name==TEXT("sm_sun")) {
                EnvironmentSkyMeshes.Add(Mesh);EnvironmentSkyMeshVisible.Add(Mesh->IsVisible());
            }
        }
    }
    if (EnvironmentSun.IsValid()) {
        EnvironmentSunRotation=EnvironmentSun->GetComponentRotation();
        EnvironmentSunIntensity=EnvironmentSun->Intensity;EnvironmentSunMobility=uint8(EnvironmentSun->Mobility);
    }
    for (TActorIterator<AExponentialHeightFog> It(GetWorld());It;++It) {
        EnvironmentFogComponent=It->GetComponent();
        EnvironmentOriginalFog=EnvironmentFogComponent->FogDensity;EnvironmentFogStart=EnvironmentFogComponent->StartDistance;
        EnvironmentFogFalloff=EnvironmentFogComponent->FogHeightFalloff;EnvironmentFogOpacity=EnvironmentFogComponent->FogMaxOpacity;
        EnvironmentFogColor=EnvironmentFogComponent->FogInscatteringLuminance;EnvironmentFogVisible=EnvironmentFogComponent->IsVisible();EnvironmentFogOwnerHidden=It->IsHidden();break;
    }
    EnsureEnvironmentRainResources();
}

void AWiseEyeDemo::EnsureEnvironmentRainResources()
{
    if (IsValid(EnvironmentRainClass) && IsValid(EnvironmentWeatherCollection) && IsValid(EnvironmentWeatherParameters)) return;
    const double Now=FPlatformTime::Seconds();
    if (Now<EnvironmentRainRetryTime) return;
    EnvironmentRainRetryTime=Now+2;
    if (!IsValid(EnvironmentWeatherCollection))
        EnvironmentWeatherCollection=LoadObject<UMaterialParameterCollection>(nullptr,TEXT("/ProjectAirSim/Weather/WeatherFX/WeatherGlobalParams.WeatherGlobalParams"));
    if (IsValid(EnvironmentWeatherCollection) && GetWorld()) {
        EnvironmentWeatherParameters=GetWorld()->GetParameterCollectionInstance(EnvironmentWeatherCollection);
        if (IsValid(EnvironmentWeatherParameters) && !EnvironmentRainDefaultsCaptured) {
            EnvironmentWeatherParameters->GetScalarParameterValue(TEXT("Rain"),EnvironmentOriginalRain);
            EnvironmentWeatherParameters->GetScalarParameterValue(TEXT("WeatherEnabled"),EnvironmentOriginalWeatherEnabled);
            EnvironmentRainDefaultsCaptured=true;
        }
    }
    if (!IsValid(EnvironmentRainClass))
        EnvironmentRainClass=LoadClass<AActor>(nullptr,TEXT("/ProjectAirSim/Weather/WeatherFX/WeatherActor.WeatherActor_C"));
}

TSharedPtr<FJsonObject> AWiseEyeDemo::EnvironmentState()
{
    InitializeEnvironment();
    auto State=MakeShared<FJsonObject>();
    State->SetBoolField(TEXT("time_supported"),EnvironmentSun.IsValid());
    State->SetBoolField(TEXT("fog_supported"),true);
    State->SetBoolField(TEXT("rain_supported"),IsValid(EnvironmentRainClass) && IsValid(EnvironmentWeatherParameters));
    State->SetStringField(TEXT("rain_unavailable_reason"),!IsValid(EnvironmentRainClass)?TEXT("Rain Blueprint unavailable"):!IsValid(EnvironmentWeatherCollection)?TEXT("Weather parameter asset unavailable"):!IsValid(EnvironmentWeatherParameters)?TEXT("Weather parameter instance unavailable"):TEXT(""));
    State->SetBoolField(TEXT("time_override"),EnvironmentTimeOverride);
    State->SetNumberField(TEXT("hour"),EnvironmentHour);
    State->SetNumberField(TEXT("fog"),EnvironmentFog);
    State->SetNumberField(TEXT("rain"),EnvironmentRain);
    State->SetBoolField(TEXT("clouds_supported"),EnvironmentCloudMaterial!=nullptr);
    State->SetNumberField(TEXT("clouds"),EnvironmentClouds);
    State->SetBoolField(TEXT("cloud_layer_active"),EnvironmentCloudActor.IsValid());
    State->SetBoolField(TEXT("cloud_atmosphere_created"),EnvironmentCloudAtmosphere.IsValid());
    State->SetNumberField(TEXT("rain_view_volumes"),EnvironmentRainActors.Num());
    int32 RainParticles=0;
    for (auto Actor:EnvironmentRainActors) if (Actor.IsValid()) {
        TArray<UParticleSystemComponent*> Systems;Actor->GetComponents(Systems);
        for (auto* System:Systems) if (System && System->GetName().Contains(TEXT("Rain"))) RainParticles+=System->GetNumActiveParticles();
    }
    State->SetNumberField(TEXT("rain_active_particles"),RainParticles);
    int32 Streaks=0;for (auto Actor:EnvironmentRainActors) if (Actor.IsValid()) if (auto* Mesh=Actor->FindComponentByClass<UInstancedStaticMeshComponent>()) Streaks+=Mesh->GetInstanceCount();
    State->SetNumberField(TEXT("rain_active_streaks"),Streaks);State->SetStringField(TEXT("rain_model"),EnvironmentRainMaterial?TEXT("world_space_depth_tested_streaks"):TEXT("legacy_particles"));
    State->SetNumberField(TEXT("night_amount"),EnvironmentNightAmount());
    State->SetNumberField(TEXT("day_sky_meshes"),EnvironmentSkyMeshes.Num());
    State->SetStringField(TEXT("model"),TEXT("visual daylight / exponential fog / bounded world rain; no weather physics or thermal calibration"));
    return State;
}

bool AWiseEyeDemo::ConfigureEnvironment(bool OverrideTime,float Hour,float Fog,float Rain,FString& Error)
{
    InitializeEnvironment();
    if (OverrideTime && !EnvironmentSun.IsValid()) { Error=TEXT("Scene has no supported directional light");return false; }
    if (Rain>0 && (!IsValid(EnvironmentRainClass) || !IsValid(EnvironmentWeatherParameters))) { Error=TEXT("Rain assets are unavailable in this scene/build");return false; }
    if (Fog>0 && !EnvironmentFogComponent.IsValid()) {
        auto* Actor=GetWorld()->SpawnActor<AExponentialHeightFog>();
        if (!Actor) { Error=TEXT("Could not create runtime fog");return false; }
        EnvironmentCreatedFog=Actor;EnvironmentFogComponent=Actor->GetComponent();EnvironmentOriginalFog=0;
        EnvironmentFogStart=EnvironmentFogComponent->StartDistance;EnvironmentFogFalloff=EnvironmentFogComponent->FogHeightFalloff;
        EnvironmentFogOpacity=EnvironmentFogComponent->FogMaxOpacity;EnvironmentFogColor=EnvironmentFogComponent->FogInscatteringLuminance;
        EnvironmentFogVisible=EnvironmentFogComponent->IsVisible();EnvironmentFogOwnerHidden=Actor->IsHidden();
    }
    if (Rain>0 && EnvironmentRainActors.IsEmpty()) {
        TArray<USceneComponent*> Targets;
        for (auto Rig : FleetRigs) if (Rig && !Rig->GimbalId.IsEmpty() && Rig->Camera) Targets.Add(Rig->Camera);
        if (Targets.IsEmpty() && Camera) Targets.Add(Camera);
        if (ObserverCapture) Targets.Add(ObserverCapture);
        for (auto* Target : Targets) {
            auto* Actor=GetWorld()->SpawnActor<AActor>(EnvironmentRainClass.Get(),Target->GetComponentLocation()+FVector(0,0,500),FRotator::ZeroRotator);
            if (!Actor) {
                for (auto& Existing : EnvironmentRainActors) if (Existing.IsValid()) Existing->Destroy();
                EnvironmentRainActors.Reset();EnvironmentRainTargets.Reset();Error=TEXT("Could not create rain volumes");return false;
            }
            // Native owns the local view volumes. The blueprint's unrelated
            // robot/player-follow tick must not move/reset these components.
            Actor->SetActorTickEnabled(false);
            EnvironmentRainActors.Add(Actor);EnvironmentRainTargets.Add(Target);
            for (auto Rig:FleetRigs) if (Rig && Rig->InfraredCapture) Rig->InfraredCapture->HiddenActors.AddUnique(Actor);
            if (FleetRigs.IsEmpty() && InfraredCapture) InfraredCapture->HiddenActors.AddUnique(Actor);
        }
    }
    if (EnvironmentSun.IsValid()) {
        EnvironmentSun->SetMobility(EComponentMobility::Movable);
        if (OverrideTime) {
            // Artistic, fixed latitude-like path, not an ephemeris/location model.
            const float Elevation=75.f*FMath::Sin((Hour-6.f)*PI/12.f);
            EnvironmentSun->SetWorldRotation(FRotator(-Elevation,(Hour-12.f)*15.f+EnvironmentSunRotation.Yaw,0));
            EnvironmentSun->SetIntensity(EnvironmentSunIntensity*FMath::Max(0.f,FMath::Sin(FMath::DegreesToRadians(Elevation))));
            const float SkyScale=FMath::Lerp(.04f,1.f,FMath::Clamp((Elevation+8.f)/35.f,0.f,1.f));
            for (int32 Index=0;Index<EnvironmentSkyLights.Num();++Index) if (EnvironmentSkyLights[Index].IsValid()) EnvironmentSkyLights[Index]->SetIntensity(EnvironmentSkyIntensities[Index]*SkyScale);
        } else {
            EnvironmentSun->SetWorldRotation(EnvironmentSunRotation);EnvironmentSun->SetIntensity(EnvironmentSunIntensity);
            EnvironmentSun->SetMobility(EComponentMobility::Type(EnvironmentSunMobility));
            for (int32 Index=0;Index<EnvironmentSkyLights.Num();++Index) if (EnvironmentSkyLights[Index].IsValid()) EnvironmentSkyLights[Index]->SetIntensity(EnvironmentSkyIntensities[Index]);
        }
    }
    if (EnvironmentFogComponent.IsValid()) {
        auto* Component=EnvironmentFogComponent.Get();
        Component->SetFogDensity(FMath::Lerp(EnvironmentOriginalFog,.18f,Fog));
        // A large baked start distance / low fog layer otherwise hides the
        // effect entirely near a ground PTZ. Strength controls density; return
        // the original layer settings exactly when the override is zero.
        Component->SetStartDistance(Fog>0?0.f:EnvironmentFogStart);
        Component->SetFogHeightFalloff(Fog>0?.001f:EnvironmentFogFalloff);
        Component->SetFogMaxOpacity(Fog>0?.98f:EnvironmentFogOpacity);
        Component->SetFogInscatteringColor(FMath::Lerp(EnvironmentFogColor,FLinearColor(.55f,.6f,.65f),Fog));
        Component->SetVisibility(Fog>0?true:EnvironmentFogVisible);
        Component->GetOwner()->SetActorHiddenInGame(Fog>0?false:EnvironmentFogOwnerHidden);
    }
    if (IsValid(EnvironmentWeatherParameters)) {
        EnvironmentWeatherParameters->SetScalarParameterValue(TEXT("WeatherEnabled"),Rain>0?1.f:EnvironmentOriginalWeatherEnabled);
        EnvironmentWeatherParameters->SetScalarParameterValue(TEXT("Rain"),Rain>0?Rain:EnvironmentOriginalRain);
    }
    if (Rain==0) {
        for (auto& Actor : EnvironmentRainActors) if (Actor.IsValid()) {
            for (auto Rig:FleetRigs) if (Rig && Rig->InfraredCapture) Rig->InfraredCapture->HiddenActors.Remove(Actor.Get());
            if (FleetRigs.IsEmpty() && InfraredCapture) InfraredCapture->HiddenActors.Remove(Actor.Get());
            Actor->Destroy();
        }
        EnvironmentRainActors.Reset();EnvironmentRainTargets.Reset();
    }
    EnvironmentTimeOverride=OverrideTime;EnvironmentHour=Hour;EnvironmentFog=Fog;EnvironmentRain=Rain;
    const bool HideDaySky=EnvironmentNightAmount()>.95f;
    for (int32 I=0;I<EnvironmentSkyMeshes.Num();++I) if (EnvironmentSkyMeshes[I].IsValid())
        EnvironmentSkyMeshes[I]->SetVisibility(EnvironmentSkyMeshVisible[I] && !HideDaySky);
    UpdateRainVolumes();UpdateEnvironmentViews();
    return true;
}

void AWiseEyeDemo::UpdateRainVolumes()
{
    for (int32 Index=0;Index<EnvironmentRainActors.Num();++Index)
        if (EnvironmentRainActors[Index].IsValid() && EnvironmentRainTargets[Index].IsValid()) {
            EnvironmentRainActors[Index]->SetActorLocation(EnvironmentRainTargets[Index]->GetComponentLocation()+FVector(0,0,500));
            const bool WorldRain=UpdateWorldRain(Index);
            TArray<UParticleSystemComponent*> Systems;EnvironmentRainActors[Index]->GetComponents(Systems);
            for (auto* System:Systems) if (System) {
                if (!WorldRain && System->GetName().Contains(TEXT("Rain"))) {
                    // The stock emitter can exceed 100k particles per view.
                    // Bound the local visual volume while keeping rain strength
                    // and material response under the scene's normalized control.
                    System->SetFloatParameter(TEXT("RainDensity"),EnvironmentRain*.1f);
                    System->SetVisibility(EnvironmentRain>0);System->SecondsBeforeInactive=0;
                    if (!System->IsActive() && EnvironmentRain>0) System->ActivateSystem();
                } else System->DeactivateSystem();
            }
        }
}

float AWiseEyeDemo::EnvironmentNightAmount() const
{
    if (!EnvironmentTimeOverride) return 0;
    const float Elevation=75.f*FMath::Sin((EnvironmentHour-6.f)*PI/12.f);
    return FMath::SmoothStep(0.f,1.f,FMath::Clamp((2.f-Elevation)/12.f,0.f,1.f));
}

void AWiseEyeDemo::UpdateEnvironmentViews()
{
    const float Night=EnvironmentNightAmount();
    if (EnvironmentFogComponent.IsValid()) {
        // Fog has its own additive luminance. Day-coloured fog otherwise makes
        // the night sky bright even after the sky dome and sun are dark.
        const auto DayFog=FMath::Lerp(EnvironmentFogColor,FLinearColor(.55f,.6f,.65f),EnvironmentFog);
        EnvironmentFogComponent->SetFogInscatteringColor(FMath::Lerp(DayFog,FLinearColor(.001f,.002f,.004f),Night));
    }
    const float DeepNight=EnvironmentTimeOverride?FMath::Clamp((FMath::Abs(EnvironmentHour-12.f)-6.f)/2.f,0.f,1.f):0.f;
    auto Apply=[Night,DeepNight](FPostProcessSettings& PP) {
        PP.bOverride_AutoExposureBias=Night>.001f;PP.AutoExposureBias=-.5f*Night;
        PP.bOverride_AutoExposureMinBrightness=Night>.001f;PP.AutoExposureMinBrightness=FMath::Lerp(-10.f,3.f,Night);
        PP.bOverride_AutoExposureMaxBrightness=Night>.001f;PP.AutoExposureMaxBrightness=20.f;
        PP.bOverride_BloomIntensity=true;PP.BloomIntensity=FMath::Lerp(.08f,.015f,Night)+.075f*DeepNight;
    };
    for (auto Rig:FleetRigs) if (Rig && Rig->Camera && Rig->Capture) {
        if (Rig->VisibleInstance) Rig->VisibleInstance->SetScalarParameterValue(TEXT("LowLight"),Night);
        Apply(Rig->Capture->PostProcessSettings);
        // Never inject a visible-light exposure response into the IR view.
        if (!Rig->InfraredMode) Apply(Rig->Camera->PostProcessSettings);
        else {
            auto& PP=Rig->Camera->PostProcessSettings;
            PP.bOverride_AutoExposureBias=false;PP.bOverride_AutoExposureMinBrightness=false;PP.bOverride_AutoExposureMaxBrightness=false;
        }
    }
    if (FleetRigs.IsEmpty()) { if (Capture) Apply(Capture->PostProcessSettings);if (Camera && !InfraredMode) Apply(Camera->PostProcessSettings); }
    if (ObserverCapture) Apply(ObserverCapture->PostProcessSettings);
    for (auto View:{Overview.Get(),FreeObserver.Get(),DroneView.Get()}) if (View) Apply(View->GetCameraComponent()->PostProcessSettings);
}

void AWiseEyeDemo::ResetEnvironment()
{
    FString Error;ConfigureEnvironment(false,12,0,0,Error);
    ConfigureClouds(0,Error);
    if (EnvironmentCreatedFog.IsValid()) {
        EnvironmentCreatedFog->Destroy();EnvironmentCreatedFog.Reset();EnvironmentFogComponent.Reset();
    }
}

bool AWiseEyeDemo::ConfigureClouds(float Coverage,FString& Error)
{
    InitializeEnvironment();
    if (!FMath::IsFinite(Coverage) || Coverage<0 || Coverage>1) { Error=TEXT("clouds must be within [0,1]");return false; }
    if (Coverage>0 && !EnvironmentCloudMaterial) { Error=TEXT("Cloud material is unavailable");return false; }
    if (Coverage==0) {
        if (EnvironmentCloudActor.IsValid() && EnvironmentSun.IsValid()) EnvironmentSun->SetAtmosphereSunLight(EnvironmentCloudSunOriginal);
        if (EnvironmentCloudActor.IsValid()) EnvironmentCloudActor->Destroy();
        if (EnvironmentCloudAtmosphere.IsValid()) EnvironmentCloudAtmosphere->Destroy();
        EnvironmentCloudAtmosphere.Reset();
        EnvironmentCloudActor.Reset();EnvironmentCloudInstance=nullptr;EnvironmentClouds=0;return true;
    }
    if (!EnvironmentCloudActor.IsValid()) {
        auto* Actor=GetWorld()->SpawnActor<AActor>();
        if (!Actor) { Error=TEXT("Cannot create cloud actor");return false; }
        auto* Cloud=NewObject<UVolumetricCloudComponent>(Actor);
        Actor->SetRootComponent(Cloud);Actor->AddInstanceComponent(Cloud);
        EnvironmentCloudInstance=UMaterialInstanceDynamic::Create(EnvironmentCloudMaterial,this);
        Cloud->SetMaterial(EnvironmentCloudInstance);
        Cloud->SetLayerBottomAltitude(1.5f);Cloud->SetLayerHeight(1.5f);
        Cloud->SetViewSampleCountScale(.5f);Cloud->SetShadowViewSampleCountScale(.25f);
        Cloud->RegisterComponent();EnvironmentCloudActor=Actor;
        bool HasAtmosphere=false;
        for (TActorIterator<AActor> It(GetWorld());It;++It) {
            if (!It->IsHidden() && It->FindComponentByClass<USkyAtmosphereComponent>()) { HasAtmosphere=true;break; }
        }
        // The prepared static city has no atmosphere actor. Add only a runtime
        // prerequisite, and remove it again when the optional cloud layer stops.
        if (!HasAtmosphere) {
            auto* Sky=GetWorld()->SpawnActor<AActor>();
            auto* Atmosphere=NewObject<USkyAtmosphereComponent>(Sky);
            Sky->SetRootComponent(Atmosphere);Sky->AddInstanceComponent(Atmosphere);
            Atmosphere->RegisterComponent();EnvironmentCloudAtmosphere=Sky;
        }
        if (EnvironmentSun.IsValid()) {
            EnvironmentCloudSunOriginal=EnvironmentSun->bAtmosphereSunLight;
            EnvironmentSun->SetAtmosphereSunLight(true);
        }
    }
    EnvironmentCloudInstance->SetScalarParameterValue(TEXT("Cloud_GlobalCoverage"),FMath::Lerp(-.4f,.4f,Coverage));
    EnvironmentCloudInstance->SetScalarParameterValue(TEXT("Cloud_GlobalDensity"),.008f);
    EnvironmentClouds=Coverage;return true;
}
