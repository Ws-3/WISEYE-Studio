#include "WiseEyeDemo.h"

#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

void AWiseEyeDemo::ScanLidar()
{
    LastLidarRangesMeters.Reset();
    LastLidarPointsWorldCm.Reset();
    LidarHitCount=0;
    LidarNearestRangeMeters=0;
    if (!LidarEnabled || !IsValid(LidarMount) || !GetWorld()) return;

    const int32 H=FMath::Clamp(LidarHorizontalSamples,1,128);
    const int32 V=FMath::Clamp(LidarVerticalSamples,1,64);
    const float MaxRangeCm=FMath::Max(1.f,LidarRangeMeters)*100.f;
    LastLidarRangesMeters.Reserve(H*V);
    LastLidarPointsWorldCm.Reserve(H*V);
    LastLidarPose=LidarMount->GetComponentTransform();
    const FVector Start=LastLidarPose.GetLocation()+LastLidarPose.GetUnitAxis(EAxis::X)*4.f;

    FCollisionQueryParams Query(SCENE_QUERY_STAT(WiseEyeGimbalLidar),true,this);
    Query.AddIgnoredActor(this);
    if (IsValid(Drone))
    {
        Query.AddIgnoredActor(Drone);
        TArray<AActor*> VisualChildren;
        Drone->GetAttachedActors(VisualChildren,true,true);
        Query.AddIgnoredActors(VisualChildren);
    }

    float Nearest=TNumericLimits<float>::Max();
    for (int32 Row=0; Row<V; ++Row)
    {
        const float Pitch=V==1 ? 0.f : FMath::Lerp(-.5f*LidarVerticalFov,.5f*LidarVerticalFov,float(Row)/float(V-1));
        for (int32 Col=0; Col<H; ++Col)
        {
            const float Yaw=H==1 ? 0.f : FMath::Lerp(-.5f*LidarHorizontalFov,.5f*LidarHorizontalFov,float(Col)/float(H-1));
            const FVector LocalDirection=FRotator(Pitch,Yaw,0).Vector();
            const FVector Direction=LastLidarPose.TransformVectorNoScale(LocalDirection).GetSafeNormal();
            FHitResult Hit;
            if (GetWorld()->LineTraceSingleByChannel(Hit,Start,Start+Direction*MaxRangeCm,ECC_Visibility,Query))
            {
                const float RangeM=Hit.Distance/100.f;
                LastLidarRangesMeters.Add(RangeM);
                LastLidarPointsWorldCm.Add(Hit.ImpactPoint);
                Nearest=FMath::Min(Nearest,RangeM);
            }
            else LastLidarRangesMeters.Add(-1.f);
        }
    }
    LidarHitCount=LastLidarPointsWorldCm.Num();
    LidarNearestRangeMeters=LidarHitCount>0 ? Nearest : 0.f;
}

bool AWiseEyeDemo::ExportLidarPointCloud()
{
    ScanLidar();
    if (LastLidarPointsWorldCm.IsEmpty())
    {
        LastLidarExportPath.Empty();
        return false;
    }
    FString Ply=FString::Printf(TEXT("ply\nformat ascii 1.0\ncomment WISEYE gimbal lidar, sensor-local meters\nelement vertex %d\nproperty float x\nproperty float y\nproperty float z\nend_header\n"),LastLidarPointsWorldCm.Num());
    const FTransform SensorFromWorld=LastLidarPose.Inverse();
    for (const FVector& WorldPoint : LastLidarPointsWorldCm)
    {
        const FVector P=SensorFromWorld.TransformPosition(WorldPoint)/100.f;
        Ply+=FString::Printf(TEXT("%.6f %.6f %.6f\n"),P.X,P.Y,P.Z);
    }
    const FString Directory=OutputDirectory.IsEmpty() ? FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("WISEYE")) : OutputDirectory;
    IFileManager::Get().MakeDirectory(*Directory,true);
    LastLidarExportPath=FPaths::Combine(Directory,FString::Printf(TEXT("LIDAR_%04d.ply"),FrameNumber++));
    if (!FFileHelper::SaveStringToFile(Ply,*LastLidarExportPath,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
    {
        LastLidarExportPath.Empty();
        return false;
    }
    return true;
}

TArray<FVector> AWiseEyeDemo::GetLidarPreviewPoints(int32 MaxPoints) const
{
    TArray<FVector> Points;
    const int32 Count=LastLidarPointsWorldCm.Num();
    if (Count<=0 || MaxPoints<=0) return Points;
    const int32 Step=FMath::Max(1,FMath::CeilToInt(float(Count)/MaxPoints));
    const FTransform SensorFromWorld=LastLidarPose.Inverse();
    Points.Reserve(FMath::Min(Count,MaxPoints));
    for (int32 I=0; I<Count; I+=Step)
        Points.Add(SensorFromWorld.TransformPosition(LastLidarPointsWorldCm[I])/100.f);
    return Points;
}
