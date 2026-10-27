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

void AWiseEyeDemo::InitializeEnvironment()
{
    if (EnvironmentInitialized) return;
    EnvironmentInitialized=true;
    for (TActorIterator<AActor> It(GetWorld());It;++It) {
        TArray<UDirectionalLightComponent*> Lights;It->GetComponents(Lights);
        for (auto* Light : Lights)
            if (Light && (!EnvironmentSun.IsValid() || Light->Intensity>EnvironmentSun->Intensity)) EnvironmentSun=Light;
        TArray<USkyLightComponent*> SkyLights;It->GetComponents(SkyLights);
        for (auto* Light : SkyLights) { EnvironmentSkyLights.Add(Light);EnvironmentSkyIntensities.Add(Light->Intensity); }
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
    auto* Parameters=LoadObject<UMaterialParameterCollection>(nullptr,TEXT("/ProjectAirSim/Weather/WeatherFX/WeatherGlobalParams.WeatherGlobalParams"));
    if (Parameters) {
        EnvironmentWeatherParameters=GetWorld()->GetParameterCollectionInstance(Parameters);
        if (EnvironmentWeatherParameters.IsValid()) {
            EnvironmentWeatherParameters->GetScalarParameterValue(TEXT("Rain"),EnvironmentOriginalRain);
            EnvironmentWeatherParameters->GetScalarParameterValue(TEXT("WeatherEnabled"),EnvironmentOriginalWeatherEnabled);
        }
    }
    EnvironmentRainClass=LoadClass<AActor>(nullptr,TEXT("/ProjectAirSim/Weather/WeatherFX/WeatherActor.WeatherActor_C"));
}

TSharedPtr<FJsonObject> AWiseEyeDemo::EnvironmentState()
{
    InitializeEnvironment();
    auto State=MakeShared<FJsonObject>();
    State->SetBoolField(TEXT("time_supported"),EnvironmentSun.IsValid());
    State->SetBoolField(TEXT("fog_supported"),true);
    State->SetBoolField(TEXT("rain_supported"),EnvironmentRainClass.IsValid() && EnvironmentWeatherParameters.IsValid());
    State->SetBoolField(TEXT("time_override"),EnvironmentTimeOverride);
    State->SetNumberField(TEXT("hour"),EnvironmentHour);
    State->SetNumberField(TEXT("fog"),EnvironmentFog);
    State->SetNumberField(TEXT("rain"),EnvironmentRain);
    State->SetNumberField(TEXT("rain_view_volumes"),EnvironmentRainActors.Num());
    State->SetStringField(TEXT("model"),TEXT("visual daylight / exponential fog / rain particles; no weather physics or thermal calibration"));
    return State;
}

bool AWiseEyeDemo::ConfigureEnvironment(bool OverrideTime,float Hour,float Fog,float Rain,FString& Error)
{
    InitializeEnvironment();
    if (OverrideTime && !EnvironmentSun.IsValid()) { Error=TEXT("Scene has no supported directional light");return false; }
    if (Rain>0 && (!EnvironmentRainClass.IsValid() || !EnvironmentWeatherParameters.IsValid())) { Error=TEXT("Rain assets are unavailable in this scene/build");return false; }
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
            EnvironmentRainActors.Add(Actor);EnvironmentRainTargets.Add(Target);
        }
    }
    if (EnvironmentSun.IsValid()) {
        EnvironmentSun->SetMobility(EComponentMobility::Movable);
        if (OverrideTime) {
            // Artistic, fixed latitude-like path, not an ephemeris/location model.
            const float Elevation=75.f*FMath::Sin((Hour-6.f)*PI/12.f);
            EnvironmentSun->SetWorldRotation(FRotator(-Elevation,(Hour-12.f)*15.f+EnvironmentSunRotation.Yaw,0));
            EnvironmentSun->SetIntensity(EnvironmentSunIntensity*FMath::Max(0.f,FMath::Sin(FMath::DegreesToRadians(Elevation))));
            const float SkyScale=FMath::Lerp(.025f,1.f,FMath::Clamp((Elevation+8.f)/35.f,0.f,1.f));
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
    if (EnvironmentWeatherParameters.IsValid()) {
        EnvironmentWeatherParameters->SetScalarParameterValue(TEXT("WeatherEnabled"),Rain>0?1.f:EnvironmentOriginalWeatherEnabled);
        EnvironmentWeatherParameters->SetScalarParameterValue(TEXT("Rain"),Rain>0?Rain:EnvironmentOriginalRain);
    }
    if (Rain==0) {
        for (auto& Actor : EnvironmentRainActors) if (Actor.IsValid()) Actor->Destroy();
        EnvironmentRainActors.Reset();EnvironmentRainTargets.Reset();
    }
    EnvironmentTimeOverride=OverrideTime;EnvironmentHour=Hour;EnvironmentFog=Fog;EnvironmentRain=Rain;
    return true;
}

void AWiseEyeDemo::UpdateRainVolumes()
{
    for (int32 Index=0;Index<EnvironmentRainActors.Num();++Index)
        if (EnvironmentRainActors[Index].IsValid() && EnvironmentRainTargets[Index].IsValid())
            EnvironmentRainActors[Index]->SetActorLocation(EnvironmentRainTargets[Index]->GetComponentLocation()+FVector(0,0,500));
}

void AWiseEyeDemo::ResetEnvironment()
{
    FString Error;ConfigureEnvironment(false,12,0,0,Error);
    if (EnvironmentCreatedFog.IsValid()) {
        EnvironmentCreatedFog->Destroy();EnvironmentCreatedFog.Reset();EnvironmentFogComponent.Reset();
    }
}
