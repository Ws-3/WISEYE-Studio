#include "WiseEyeDemo.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"

bool AWiseEyeDemo::UpdateWorldRain(int32 Index)
{
    if (!EnvironmentRainMaterial || !EnvironmentRainActors.IsValidIndex(Index) || !EnvironmentRainActors[Index].IsValid() || !EnvironmentRainTargets[Index].IsValid()) return false;
    auto* Actor=EnvironmentRainActors[Index].Get();auto* Target=EnvironmentRainTargets[Index].Get();
    auto* Mesh=Actor->FindComponentByClass<UInstancedStaticMeshComponent>();
    if (!Mesh) {
        auto* Plane=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Plane.Plane"));if (!Plane) return false;
        Mesh=NewObject<UInstancedStaticMeshComponent>(Actor);Mesh->ComponentTags.Add(TEXT("WISEYE_WorldRain"));
        Mesh->SetupAttachment(Actor->GetRootComponent());Mesh->SetStaticMesh(Plane);Mesh->SetMobility(EComponentMobility::Movable);
        Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCastShadow(false);
        Mesh->SetMaterial(0,UMaterialInstanceDynamic::Create(EnvironmentRainMaterial,Mesh));Mesh->RegisterComponent();
    }
    const FVector Eye=Target->GetComponentLocation();
    const int32 CellX=FMath::FloorToInt(Eye.X/800),CellY=FMath::FloorToInt(Eye.Y/800);
    const double HeightBase=FMath::FloorToDouble(Eye.Z/2000)*2000-2000;
    const double Time=GetWorld()->GetTimeSeconds();
    const int32 PerCell=FMath::CeilToInt(180*EnvironmentRain);
    TArray<FTransform> Transforms;Transforms.Reserve(PerCell*25);
    const FVector Along=FVector(-60,-25,1100).GetSafeNormal();
    for (int32 CY=CellY-2;CY<=CellY+2;++CY) for (int32 CX=CellX-2;CX<=CellX+2;++CX) {
        const uint32 Seed=HashCombine(GetTypeHash(CX),GetTypeHash(CY));FRandomStream Random{int32(Seed)};
        for (int32 I=0;I<PerCell;++I) {
            const double X=CX*800+Random.FRand()*800,Y=CY*800+Random.FRand()*800;
            const double Phase=FMath::Fmod(Random.FRand()*6000-Time*1100,6000.);
            FVector Position(X,Y,HeightBase+(Phase<0?Phase+6000:Phase));
            const double Distance=(Eye-Position).Size();
            // No oversized water drops directly in front of the lens.
            if (Distance<250) continue;
            const FVector Facing=(Eye-Position).GetSafeNormal();
            const FQuat Rotation=FRotationMatrix::MakeFromYZ(Along,Facing).ToQuat();
            const float Width=FMath::Clamp(float(Distance*.0005),.15f,1.5f);
            Transforms.Add(FTransform(Rotation,Position,FVector(Width/100.f,.08f+.10f*EnvironmentRain,1)));
        }
    }
    if (Mesh->GetInstanceCount()!=Transforms.Num()) { Mesh->ClearInstances();Mesh->AddInstances(Transforms,false,true,false); }
    else if (!Transforms.IsEmpty()) Mesh->BatchUpdateInstancesTransforms(0,Transforms,true,true,true);
    if (auto* Material=Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(0)))
        Material->SetVectorParameterValue(TEXT("RainTint"),FLinearColor(.8f,.85f,.9f)*FMath::Lerp(1.f,.12f,EnvironmentNightAmount()));
    return true;
}
