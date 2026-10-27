#include "WiseEyeDemo.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformTime.h"

bool AWiseEyeDemo::TracePlacement(const FVector& Start,const FVector& End,FVector& Point,FString& Error) const
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WiseEyePlacement),true);
    const auto* Root=FleetRoot?FleetRoot.Get():this;
    for (auto Rig : Root->FleetRigs) {
        if (!IsValid(Rig)) continue;
        AActor* Mount=Rig;
        while (Mount->GetAttachParentActor()) Mount=Mount->GetAttachParentActor();
        for (AActor* Assembly : {Mount,Rig->Drone.Get(),Rig->DynamicsSource.Get()}) {
            if (!IsValid(Assembly)) continue;
            Query.AddIgnoredActor(Assembly);
            TArray<AActor*> AttachedParts; Assembly->GetAttachedActors(AttachedParts,true,true);
            Query.AddIgnoredActors(AttachedParts);
        }
    }
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_WorldStatic);
    // City Sample FastGeo static roads are registered as WorldDynamic query
    // objects. Include them explicitly without accepting arbitrary moving props.
    Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    TArray<FHitResult> Hits;
    GetWorld()->LineTraceMultiByObjectType(Hits,Start,End,Objects,Query);
    for (const auto& Hit : Hits) {
        const auto* Component=Hit.GetComponent();
        const auto* Actor=Hit.GetActor();
        const bool Static=Component && Component->GetCollisionObjectType()==ECC_WorldStatic;
        const bool FastGeo=Actor && Actor->GetClass()->GetFName()==FName(TEXT("FastGeoSurrogateActor"));
        if (!Static && !FastGeo) continue;
        if (Hit.ImpactNormal.Z<.25f) { Error=TEXT("Surface too steep; select an upward-facing surface"); return false; }
        Point=Hit.ImpactPoint;
        return true;
    }
    Error=TEXT("No static surface hit; point at ground with collision enabled");
    return false;
}

void AWiseEyeDemo::CancelPlacement()
{
    if (PlacementActive && !PlacementHasResult && PlacementError.IsEmpty()) PlacementError=TEXT("Placement cancelled");
    PlacementActive=false;
    PlacementHoverValid=false;
    if (APlayerController* PC=GetWorld()->GetFirstPlayerController())
    {
        PC->SetInputMode(FInputModeGameOnly());
        PC->bShowMouseCursor=false;
    }
}

bool AWiseEyeDemo::BeginPlacement(const FString& DeviceId,const FString& Token,float Clearance,FString& Error)
{
    if (!FindDevice(DeviceId) || Token.IsEmpty() || Token.Len()>64 || !FMath::IsFinite(Clearance) || Clearance<0 || Clearance>1000)
    { Error=TEXT("Invalid device, request token or clearance (0..1000 cm)"); return false; }
    if (!SetObserverMode(TEXT("free"))) { Error=TEXT("Observer unavailable"); return false; }
    SetControlMode(TEXT("observer"));
    PlacementDevice=DeviceId; PlacementToken=Token; PlacementClearance=Clearance;
    PlacementHasResult=false; PlacementError.Empty(); ++PlacementSequence;
    PlacementActive=true; PlacementStarted=FPlatformTime::Seconds();
    if (APlayerController* PC=GetWorld()->GetFirstPlayerController())
    {
        FInputModeGameAndUI Mode;
        Mode.SetHideCursorDuringCapture(false);
        PC->SetInputMode(Mode);
        PC->bShowMouseCursor=true;
    }
    return true;
}

void AWiseEyeDemo::CommitPlacement(const FVector& Surface)
{
    PlacementSurface=Surface;
    float Offset=PlacementClearance;
    auto* Target=FindDevice(PlacementDevice);
    if (!Target) { PlacementError=TEXT("Placement device no longer exists");PlacementHasResult=false;CancelPlacement();return; }
    if (PlacementDevice==Target->GimbalId)
    {
        // The manifest positions the demo anchor, while the imported housing's
        // lowest point defines the physical base. Preserve the full rig geometry.
        AActor* Mount=Target;
        while (Mount->GetAttachParentActor()) Mount=Mount->GetAttachParentActor();
        TArray<AActor*> Parts; Parts.Add(Mount); Mount->GetAttachedActors(Parts,false,true);
        double Bottom=Target->GetActorLocation().Z; bool Found=false;
        for (AActor* Part : Parts)
        {
            TArray<UStaticMeshComponent*> Meshes; Part->GetComponents(Meshes);
            for (UStaticMeshComponent* Mesh : Meshes)
                if (Mesh->GetStaticMesh() && Mesh->GetStaticMesh()->GetPathName().Contains(TEXT("/PTZRecovered/")))
                {
                    const double MinZ=Mesh->Bounds.GetBox().Min.Z;
                    Bottom=Found?FMath::Min(Bottom,MinZ):MinZ; Found=true;
                }
        }
        if (Found) Offset+=Target->GetActorLocation().Z-Bottom;
    }
    PlacementPosition=Surface+FVector(0,0,Offset);
    PlacementHasResult=true; PlacementError.Empty(); ++PlacementSequence;
    CancelPlacement();
}

bool AWiseEyeDemo::SnapPlacement(const FString& DeviceId,const FString& Token,const FVector& Position,float Clearance,FString& Error)
{
    if (!FindDevice(DeviceId) || Token.IsEmpty() || Token.Len()>64 || !FMath::IsFinite(Clearance) || Clearance<0 || Clearance>1000)
    { Error=TEXT("Invalid device, request token or clearance (0..1000 cm)"); return false; }
    if (Position.ContainsNaN() || Position.GetAbsMax()>1e7)
    { Error=TEXT("Invalid finite position"); return false; }
    // Validate/trace before mutating an existing pick request.
    FVector Surface;
    if (!TracePlacement(Position+FVector(0,0,100000),Position-FVector(0,0,100000),Surface,Error)) return false;
    PlacementDevice=DeviceId; PlacementToken=Token; PlacementClearance=Clearance;
    CommitPlacement(Surface);
    return true;
}

void AWiseEyeDemo::StepPlacement()
{
    APlayerController* PC=GetWorld()->GetFirstPlayerController();
    if (!PC) return;
    if (FPlatformTime::Seconds()-PlacementStarted>45 || PC->WasInputKeyJustPressed(EKeys::RightMouseButton))
    {
        PlacementError=TEXT("Placement cancelled or timed out");
        PlacementHasResult=false; ++PlacementSequence;
        CancelPlacement(); return;
    }
    FVector Origin,Direction,Surface; FString Error;
    PlacementHoverValid=false;
    if (!PC->DeprojectMousePositionToWorld(Origin,Direction) || !TracePlacement(Origin,Origin+Direction*200000,Surface,Error)) return;
    PlacementSurface=Surface;
    PlacementHoverValid=true;
    if (PC->WasInputKeyJustPressed(EKeys::LeftMouseButton)) CommitPlacement(Surface);
}
