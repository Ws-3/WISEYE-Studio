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
    ++LidarScanSequence;
    LastLidarCaptureTime=GetWorld()->GetTimeSeconds();

    const int32 H=FMath::Clamp(LidarHorizontalSamples,1,128);
    const int32 V=FMath::Clamp(LidarVerticalSamples,1,64);
    const float MaxRangeCm=FMath::Max(1.f,LidarRangeMeters)*100.f;
    LastLidarRangesMeters.Reserve(H*V);
    LastLidarPointsWorldCm.Reserve(H*V);
    LastLidarPose=LidarMount->GetComponentTransform();
    // Sensor coordinates are rigid, metric coordinates, independent of model scale.
    LastLidarPose.SetScale3D(FVector::OneVector);
    const FVector Start=LastLidarPose.GetLocation()+LastLidarPose.GetUnitAxis(EAxis::X)*4.f;
    LastLidarPose.SetLocation(Start);

    FCollisionQueryParams Query(SCENE_QUERY_STAT(WiseEyeGimbalLidar),true,this);
    Query.AddIgnoredActor(this);
    // Ignore the sensor housing and hidden physics proxy, not the observed UAV.
    if (IsValid(DynamicsSource)) Query.AddIgnoredActor(DynamicsSource);
    AActor* Housing=this;
    while (Housing->GetAttachParentActor()) Housing=Housing->GetAttachParentActor();
    TArray<AActor*> HousingActors;
    HousingActors.Add(Housing);
    Housing->GetAttachedActors(HousingActors,false,true);
    TArray<AActor*> DroneActors;
    DroneActors.Add(Drone);
    if (IsValid(Drone)) Drone->GetAttachedActors(DroneActors,false,true);
    for (AActor* Actor : HousingActors)
    {
        if (IsValid(Actor) && !DroneActors.Contains(Actor)) Query.AddIgnoredActor(Actor);
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
    const FString Meta=FString::Printf(TEXT("{\"device_id\":\"%s\",\"sensor_id\":\"%s/lidar\",\"scene_id\":\"%s\",\"run_id\":\"%s\",\"simulation_time_s\":%.6f,\"frame\":\"sensor_local_x_forward_y_right_z_up\",\"units\":\"meters\"}"),*GimbalId,*GimbalId,*SceneId,*PlaySessionId,LastLidarCaptureTime);
    FFileHelper::SaveStringToFile(Meta,*(LastLidarExportPath+TEXT(".json")));
    return true;
}

TArray<FVector> AWiseEyeDemo::GetLidarPreviewPoints(int32 MaxPoints) const
{
    TArray<FVector> Points;
    const int32 Count=LastLidarPointsWorldCm.Num();
    if (!LidarEnabled || Count<=0 || MaxPoints<=0) return Points;
    const int32 Step=FMath::Max(1,FMath::CeilToInt(float(Count)/MaxPoints));
    const FTransform SensorFromWorld=LastLidarPose.Inverse();
    Points.Reserve(FMath::Min(Count,MaxPoints));
    for (int32 I=0; I<Count; I+=Step)
        Points.Add(SensorFromWorld.TransformPosition(LastLidarPointsWorldCm[I])/100.f);
    return Points;
}
