#pragma once
#include "CoreMinimal.h"
#include "RenderResource.h"

class FJsonObject;
class AWiseEyeDemo;

struct FWiseEyeGTSettings
{
    bool KeepPartialOcclusion=true, KeepPartialOutside=true;
    int32 MinVisiblePixels=1;
    float MinVisibleFraction=0;
    float MaxFPS=2;
};

// Immutable capture-time metadata. Depth planes are copied with the image on
// the render thread; annotations are computed off the game thread.
struct FWiseEyeGTSnapshot
{
    FString Token,RunId,SceneId,DeviceId,SensorId;
    int32 Width=0,Height=0;
    float Fov=0;
    FVector Position;
    FRotator Rotation;
    FWiseEyeGTSettings Settings;
    TArray<FString> TargetIds,Models;
    TArray<FString> ScenarioModels;
    TSharedPtr<FJsonObject> Environment;
    TArray<FTextureRenderTargetResource*> Resources; // scene, then isolated targets
    TArray<TArray<float>> Depths;
    FString Error;
    TSharedPtr<FJsonObject> Annotate(int64 Sequence,double Time) const;
};

TSharedPtr<FWiseEyeGTSnapshot> CaptureWiseEyeGroundTruth(AWiseEyeDemo& Demo,bool Infrared,const FString& Token);
