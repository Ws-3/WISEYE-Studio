#include "WiseEyeDemo.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformTime.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Materials/MaterialInstanceDynamic.h"

void AWiseEyeDemo::DestroyPlacementPreview()
{
    if (IsValid(PlacementPreview)) {
        const auto* Root=FleetRoot?FleetRoot.Get():this;
        for (auto Rig:Root->FleetRigs) if (IsValid(Rig)) {
            Rig->Capture->HiddenActors.Remove(PlacementPreview);
            Rig->InfraredCapture->HiddenActors.Remove(PlacementPreview);
        }
        PlacementPreview->Destroy();
    }
    PlacementPreview=nullptr;PlacementPreviewMaterial=nullptr;
}

bool AWiseEyeDemo::BuildPlacementPreview(FString& Error)
{
    DestroyPlacementPreview();
    auto* Target=FindDevice(PlacementDevice);
    auto* Material=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WISEYE/Sensors/M_PlacementPreview.M_PlacementPreview"));
    if (!Target || !Material) { Error=TEXT("Placement preview material/device unavailable");return false; }
    const bool Gimbal=PlacementDevice==Target->GimbalId;
    AActor* Source=Gimbal?static_cast<AActor*>(Target):Target->Drone.Get();
    PlacementPreviewReference=Source->GetActorTransform();
    PlacementPreview=GetWorld()->SpawnActor<AActor>();
    PlacementPreview->SetActorHiddenInGame(true);PlacementPreview->SetActorEnableCollision(false);
    auto* GhostRoot=NewObject<USceneComponent>(PlacementPreview);
    GhostRoot->SetMobility(EComponentMobility::Movable);PlacementPreview->SetRootComponent(GhostRoot);GhostRoot->RegisterComponent();
    PlacementPreview->SetActorTransform(PlacementPreviewReference);
    PlacementPreviewMaterial=UMaterialInstanceDynamic::Create(Material,this);
    AActor* Assembly=Source;
    if (Gimbal) while (Assembly->GetAttachParentActor()) Assembly=Assembly->GetAttachParentActor();
    TArray<AActor*> Parts={Assembly};Assembly->GetAttachedActors(Parts,false,true);int32 Count=0;
    for (auto* Part:Parts) {
        if (!IsValid(Part) || Part->IsHidden()) continue;
        TArray<UStaticMeshComponent*> Meshes;Part->GetComponents(Meshes);
        for (auto* Mesh:Meshes) {
            if (!Mesh->GetStaticMesh() || !Mesh->IsVisible() || Mesh->bHiddenInGame) continue;
            if (Gimbal && !Mesh->GetStaticMesh()->GetPathName().Contains(TEXT("/PTZRecovered/")) && Mesh!=Target->LidarBody) continue;
            auto* Copy=NewObject<UStaticMeshComponent>(PlacementPreview);
            Copy->bDisallowNanite=true; // Translucent ghosts use the mesh fallback, never alter the source asset.
            Copy->SetMobility(EComponentMobility::Movable);Copy->SetStaticMesh(Mesh->GetStaticMesh());
            Copy->SetCollisionEnabled(ECollisionEnabled::NoCollision);Copy->SetGenerateOverlapEvents(false);Copy->SetCanEverAffectNavigation(false);
            Copy->SetCastShadow(false);Copy->SetRenderCustomDepth(false);
            Copy->SetupAttachment(GhostRoot);Copy->SetRelativeTransform(Mesh->GetComponentTransform().GetRelativeTransform(PlacementPreviewReference));
            for (int32 I=0;I<Copy->GetNumMaterials();++I) Copy->SetMaterial(I,PlacementPreviewMaterial);
            Copy->RegisterComponent();++Count;
        }
    }
    if (!Count) { Error=TEXT("No visible device geometry for preview");DestroyPlacementPreview();return false; }
    const auto* Root=FleetRoot?FleetRoot.Get():this;
    // Ghosts belong to the operator view, never to training/sensor imagery.
    for (auto Rig:Root->FleetRigs) if (IsValid(Rig)) {
        Rig->Capture->HiddenActors.AddUnique(PlacementPreview);
        Rig->InfraredCapture->HiddenActors.AddUnique(PlacementPreview);
    }
    return true;
}

void AWiseEyeDemo::UpdatePlacementPreview(bool Valid)
{
    if (!IsValid(PlacementPreview)) return;
    PlacementPreview->SetActorHiddenInGame(!Valid);
    if (!Valid) return;
    PlacementPreviewPosition=PlacementAnchor(PlacementSurface);
    FTransform Transform=PlacementPreviewReference;Transform.SetLocation(PlacementPreviewPosition);
    Transform.SetRotation(FRotator(0,PlacementYawDegrees-PlacementBaseYaw,0).Quaternion()*PlacementPreviewReference.GetRotation());
    PlacementPreview->SetActorTransform(Transform);
}

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
    DestroyPlacementPreview();
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
    PlacementNudge=FVector::ZeroVector;PlacementLocked=false;PlacementHoverValid=false;
    PlacementRepeats.Empty();
    auto* Target=FindDevice(DeviceId);
    PlacementBaseYaw=PlacementYawDegrees=DeviceId==Target->GimbalId?Target->GimbalPlacementYaw:Target->InitialYawDegrees;
    if (!BuildPlacementPreview(Error)) return false;
    PlacementHasResult=false; PlacementError.Empty(); ++PlacementSequence;
    PlacementActive=true; PlacementStarted=FPlatformTime::Seconds();
    SetSimulationWindowVisible(true);
    if (APlayerController* PC=GetWorld()->GetFirstPlayerController())
    {
        FInputModeGameAndUI Mode;
        Mode.SetHideCursorDuringCapture(false);
        PC->SetInputMode(Mode);
        PC->bShowMouseCursor=true;
    }
    return true;
}

FVector AWiseEyeDemo::PlacementAnchor(const FVector& Surface) const
{
    float Offset=PlacementClearance;
    auto* Target=FindDevice(PlacementDevice);
    if (!Target) return Surface;
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
    return Surface+FVector(0,0,Offset)+PlacementNudge;
}

void AWiseEyeDemo::CommitPlacement(const FVector& Surface)
{
    PlacementSurface=Surface;
    if (!FindDevice(PlacementDevice)) { PlacementError=TEXT("Placement device no longer exists");PlacementHasResult=false;CancelPlacement();return; }
    PlacementPosition=PlacementAnchor(Surface);
    PlacementHasResult=true; PlacementError.Empty(); ++PlacementSequence;
    CancelPlacement();
}

bool AWiseEyeDemo::ApplyDevicePlacement(const FString& DeviceId,const FVector& Position,float Yaw,FString& Error)
{
    auto* Target=FindDevice(DeviceId);
    if (!Target || Position.ContainsNaN() || Position.GetAbsMax()>1e7 || !FMath::IsFinite(Yaw)) {
        Error=TEXT("Invalid placement pose/device");return false;
    }
    if (DeviceId==Target->GimbalId) {
        AActor* Mount=Target;while (Mount->GetAttachParentActor()) Mount=Mount->GetAttachParentActor();
        const FTransform Old=Target->GetActorTransform();
        FTransform Desired=Old;Desired.SetLocation(Position);
        Desired.SetRotation(FRotator(0,Yaw-Target->GimbalPlacementYaw,0).Quaternion()*Old.GetRotation());
        Mount->SetActorTransform(Mount->GetActorTransform().GetRelativeTransform(Old)*Desired,false,nullptr,ETeleportType::TeleportPhysics);
        Target->GimbalPlacementYaw=Yaw;Target->UpdateSensorTransforms();
        return true;
    }
    if (Target->FixedwingActive) {Error=TEXT("Stop cruise before changing placement");return false;}
    if (Target->RotorsRunning) {Error=TEXT("Land and disarm before changing placement");return false;}
    if (Target->FlightBackend==EWiseEyeFlightBackend::ProjectAirSim && Target->DroneModel!=TEXT("fixedwing")) {
        // The physics authority must have moved first. Never move only the
        // visual assembly, which would snap back on the following tick.
        if (!IsValid(Target->DynamicsSource) || !Target->DynamicsSource->GetActorLocation().Equals(Position,5.f) ||
            FMath::Abs(FMath::FindDeltaAngleDegrees(Target->DynamicsSource->GetActorRotation().Yaw,Yaw))>1.f) {
            Error=TEXT("Apply drone placement through the flight controller first");return false;
        }
        Target->Drone->SetActorLocationAndRotation(Position,Target->DynamicsSource->GetActorQuat()*Target->DynamicsVisualRotationOffset.Quaternion(),false,nullptr,ETeleportType::TeleportPhysics);
    } else if (Target->DroneModel==TEXT("fixedwing")) {
        Target->FixedwingYaw=Yaw;Target->Drone->SetActorLocationAndRotation(Position,FRotator(0,Yaw,0).Quaternion()*Target->DynamicsVisualRotationOffset.Quaternion(),false,nullptr,ETeleportType::TeleportPhysics);
    } else {
        const FQuat Rotation=FRotator(0,Yaw-Target->InitialYawDegrees,0).Quaternion()*Target->Drone->GetActorQuat();
        Target->Drone->SetActorLocationAndRotation(Position,Rotation,false,nullptr,ETeleportType::TeleportPhysics);
    }
    Target->InitialYawDegrees=Yaw;Target->FlightOrigin=Target->InitialFlightOrigin=Position;
    Target->DroneInitialRotation=Target->Drone->GetActorRotation();
    return true;
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
    PlacementNudge=FVector::ZeroVector;PlacementLocked=false;
    auto* Target=FindDevice(DeviceId);
    PlacementBaseYaw=PlacementYawDegrees=DeviceId==Target->GimbalId?Target->GimbalPlacementYaw:Target->InitialYawDegrees;
    CommitPlacement(Surface);
    return true;
}

void AWiseEyeDemo::StepPlacement()
{
    APlayerController* PC=GetWorld()->GetFirstPlayerController();
    if (!PC) return;
    if (FPlatformTime::Seconds()-PlacementStarted>120 || PC->WasInputKeyJustPressed(EKeys::RightMouseButton) || PC->WasInputKeyJustPressed(EKeys::Escape))
    {
        PlacementError=TEXT("Placement cancelled or timed out");
        PlacementHasResult=false; ++PlacementSequence;
        CancelPlacement(); return;
    }
    if (PC->WasInputKeyJustPressed(EKeys::SpaceBar) && PlacementHoverValid) PlacementLocked=!PlacementLocked;
    const double Step=PC->IsInputKeyDown(EKeys::LeftShift) || PC->IsInputKeyDown(EKeys::RightShift)?1.:10.;
    bool Nudged=false;
    const double Now=FPlatformTime::Seconds();
    auto AdjustDue=[&](FKey Key) {
        const FName Name=Key.GetFName();
        if (!PC->IsInputKeyDown(Key)) {PlacementRepeats.Remove(Name);return false;}
        if (PC->WasInputKeyJustPressed(Key)) {PlacementRepeats.Add(Name,Now+.3);return true;}
        double* Next=PlacementRepeats.Find(Name);
        if (!Next) {PlacementRepeats.Add(Name,Now+.3);return false;}
        if (Now<*Next) return false;
        *Next=Now+.1;return true; // Real-time 10 Hz, no catch-up after a stall.
    };
    auto Nudge=[&](FKey Key,const FVector& Delta) {
        if (AdjustDue(Key) && PlacementHoverValid) {PlacementNudge+=Delta*Step;Nudged=true;}
    };
    const FRotator Heading(0,PlacementYawDegrees,0);
    const FVector Forward=Heading.Vector(),Right=FRotationMatrix(Heading).GetUnitAxis(EAxis::Y);
    Nudge(EKeys::W,Forward);Nudge(EKeys::S,-Forward);
    Nudge(EKeys::D,Right);Nudge(EKeys::A,-Right);
    Nudge(EKeys::R,FVector(0,0,1));Nudge(EKeys::F,FVector(0,0,-1));
    const float TurnStep=Step==1?.1f:1.f;
    for (FKey Key:{EKeys::Q,EKeys::E}) if (AdjustDue(Key) && PlacementHoverValid) {
        PlacementYawDegrees=FRotator::NormalizeAxis(PlacementYawDegrees+(Key==EKeys::Q?-TurnStep:TurnStep));Nudged=true;
    }
    PlacementNudge.Z=FMath::Max(PlacementNudge.Z,-double(PlacementClearance));
    if (Nudged) { PlacementLocked=true;PlacementStarted=FPlatformTime::Seconds(); }
    if (PC->WasInputKeyJustPressed(EKeys::Home)) {PlacementNudge=FVector::ZeroVector;PlacementYawDegrees=PlacementBaseYaw;}
    if (PlacementLocked && PlacementHoverValid) {
        UpdatePlacementPreview(true);
        if (PC->WasInputKeyJustPressed(EKeys::LeftMouseButton) || PC->WasInputKeyJustPressed(EKeys::Enter)) CommitPlacement(PlacementSurface);
        return;
    }
    FVector Origin,Direction,Surface; FString Error;
    PlacementHoverValid=false;
    UpdatePlacementPreview(false);
    float MouseX=0,MouseY=0;int32 Width=0,Height=0;PC->GetViewportSize(Width,Height);
    if (!PC->GetMousePosition(MouseX,MouseY) || MouseX<0 || MouseY<0 || MouseX>=Width || MouseY>=Height ||
        !PC->DeprojectMousePositionToWorld(Origin,Direction) || !TracePlacement(Origin,Origin+Direction*200000,Surface,Error)) return;
    PlacementSurface=Surface;
    PlacementHoverValid=true;
    UpdatePlacementPreview(true);
    if (PC->WasInputKeyJustPressed(EKeys::LeftMouseButton)) CommitPlacement(Surface);
}
