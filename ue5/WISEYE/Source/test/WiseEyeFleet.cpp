#include "EngineUtils.h"
#include "WiseEyeRuntimePaths.h"
#include "WiseEyeDemo.h"
#include "WiseEyeBridge.h"
#include "WiseEyeStreaming.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Engine/StaticMesh.h"

namespace {
FVector VectorField(const TSharedPtr<FJsonObject>& Item,const TCHAR* Key) {
    const auto& V=Item->GetArrayField(Key); return FVector(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber());
}
UStaticMeshComponent* CopyMesh(UStaticMeshComponent* Source,AActor* MeshOwner,USceneComponent* Parent,const FTransform& Reference) {
    auto* Mesh=NewObject<UStaticMeshComponent>(MeshOwner);
    Mesh->SetStaticMesh(Source->GetStaticMesh());
    for (int32 I=0;I<Source->GetNumMaterials();++I) Mesh->SetMaterial(I,Source->GetMaterial(I));
    Mesh->SetMobility(EComponentMobility::Movable);
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Mesh->SetCollisionResponseToAllChannels(ECR_Ignore);Mesh->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    Mesh->SetRenderCustomDepth(Source->bRenderCustomDepth);Mesh->SetCustomDepthStencilValue(Source->CustomDepthStencilValue);
    Mesh->RegisterComponent();Mesh->AttachToComponent(Parent,FAttachmentTransformRules::KeepRelativeTransform);
    Mesh->SetRelativeTransform(Source->GetComponentTransform().GetRelativeTransform(Reference));
    return Mesh;
}
}

AWiseEyeDemo* AWiseEyeDemo::FindDevice(const FString& Id) const {
    const AWiseEyeDemo* Root=FleetRoot?FleetRoot.Get():this;
    for (auto Rig : Root->FleetRigs) if (IsValid(Rig) && ((!Rig->GimbalId.IsEmpty() && Rig->GimbalId==Id) || (Rig->OwnsDrone && Rig->DroneId==Id))) return Rig;
    return nullptr;
}

TArray<TSharedPtr<FJsonValue>> AWiseEyeDemo::DeviceInventory() const {
    const AWiseEyeDemo* Root=FleetRoot?FleetRoot.Get():this;
    TArray<TSharedPtr<FJsonValue>> Result;
    for (auto Rig : Root->FleetRigs) {
        auto Add=[&](const FString& Id,const FString& Kind,const FString& Model,const FVector& Position) {
            auto Item=MakeShared<FJsonObject>();Item->SetStringField(TEXT("id"),Id);Item->SetStringField(TEXT("kind"),Kind);Item->SetStringField(TEXT("model_id"),Model);
            Item->SetStringField(TEXT("name"),Kind==TEXT("drone")?Rig->DroneName:Rig->GimbalName);Item->SetStringField(TEXT("tracking_target"),Rig->TrackingTargetId);
            Item->SetArrayField(TEXT("position_cm"),{MakeShared<FJsonValueNumber>(Position.X),MakeShared<FJsonValueNumber>(Position.Y),MakeShared<FJsonValueNumber>(Position.Z)});
            Item->SetStringField(TEXT("dynamics_name"),Rig->DynamicsActorName.ToString());
            const double Heading=Kind==TEXT("gimbal")?Rig->GimbalPlacementYaw:Rig->DroneModel==TEXT("fixedwing")?Rig->FixedwingYaw:IsValid(Rig->DynamicsSource)?Rig->DynamicsSource->GetActorRotation().Yaw:Rig->InitialYawDegrees;
            Item->SetArrayField(TEXT("rotation_deg"),{MakeShared<FJsonValueNumber>(0),MakeShared<FJsonValueNumber>(Heading),MakeShared<FJsonValueNumber>(0)});
            Item->SetArrayField(TEXT("initial_position_cm"),{MakeShared<FJsonValueNumber>(Rig->FlightOrigin.X),MakeShared<FJsonValueNumber>(Rig->FlightOrigin.Y),MakeShared<FJsonValueNumber>(Rig->FlightOrigin.Z)});
            Item->SetBoolField(TEXT("rotors_running"),Rig->RotorsRunning);
            if (Model==TEXT("fixedwing")) Item->SetObjectField(TEXT("fixedwing"),Rig->FixedwingState());
            if (Kind==TEXT("drone")) {
                Item->SetObjectField(TEXT("aerial"),Rig->AerialState());
                auto Lights=MakeShared<FJsonObject>();
                Lights->SetBoolField(TEXT("enabled"),Rig->NavigationLightsEnabled);
                Lights->SetBoolField(TEXT("night"),Rig->NavigationNight);
                Lights->SetBoolField(TEXT("red_on"),Rig->NavigationRedOn);
                Lights->SetBoolField(TEXT("green_on"),Rig->NavigationGreenOn);
                Lights->SetNumberField(TEXT("lamp_count"),Rig->NavigationLamps.Num());
                Lights->SetNumberField(TEXT("period_s"),1.6);
                Item->SetObjectField(TEXT("navigation_lights"),Lights);
            }
            Item->SetNumberField(TEXT("initial_yaw_deg"),Rig->InitialYawDegrees);
            Item->SetNumberField(TEXT("placement_yaw_deg"),Kind==TEXT("drone")?Rig->InitialYawDegrees:Rig->GimbalPlacementYaw);
            Result.Add(MakeShared<FJsonValueObject>(Item));
        };
        if (Rig->OwnsDrone && Rig->Drone) Add(Rig->DroneId,TEXT("drone"),Rig->DroneModel,Rig->Drone->GetActorLocation());
        if (!Rig->GimbalId.IsEmpty()) Add(Rig->GimbalId,TEXT("gimbal"),TEXT("eo80"),Rig->GetActorLocation());
    }
    return Result;
}

TSharedPtr<FJsonObject> AWiseEyeDemo::DispatchDevice(const TSharedPtr<FJsonObject>& Request) { return Bridge->Dispatch(Request); }

void AWiseEyeDemo::InitializeFleetChild() {
    DroneInitialRotation=Drone->GetActorRotation();InitialFlightOrigin=FlightOrigin;
    for (auto Rotor : Rotors) RotorInitialRotations.Add(Rotor->GetRootComponent()->GetRelativeRotation().Quaternion());
    if (OwnsDrone) InitializeDroneModels();
    DroneView=GetWorld()->SpawnActor<ACameraActor>();
    InitializeSensors();StreamManager=new FWiseEyeStreamManager();
    OutputDirectory=FPaths::Combine(WiseEyePaths::SavedRoot(),TEXT("WISEYE"),PlaySessionId,GimbalId.IsEmpty()?DroneId:GimbalId);
    IFileManager::Get().MakeDirectory(*OutputDirectory,true);
    if (GimbalId.IsEmpty()) { VisibleEnabled=false;InfraredEnabled=false;LidarEnabled=false;EventEnabled=false;RefreshSensors();SetActorHiddenInGame(true); }
    RefreshSensors();RefreshEventSensor();
    if (OwnsDrone) SetVisualAssemblyCollision(false);
    Bridge=new FWiseEyeBridge(*this);BridgeReady=true;
}

bool AWiseEyeDemo::InitializeFleet(FString& Error) {
    FleetRoot=this;FleetRigs.Add(this);TrackingDrone=Drone;
    const FString Path=FPaths::Combine(WiseEyePaths::ConfigRoot(),TEXT("WISEYE/Fleets"),SceneId+TEXT(".json"));
    if (!FPaths::FileExists(Path)) return true;
    FString Text;TSharedPtr<FJsonObject> Manifest;
    if (!FFileHelper::LoadFileToString(Text,*Path) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Manifest) || !Manifest) { Error=TEXT("Invalid fleet JSON");return false; }
    double Version=0;FString Scene;const TArray<TSharedPtr<FJsonValue>>* Devices=nullptr;
    if (!Manifest->TryGetNumberField(TEXT("version"),Version) || Version!=1 || !Manifest->TryGetStringField(TEXT("scene_id"),Scene) || Scene!=SceneId || !Manifest->TryGetArrayField(TEXT("devices"),Devices) || Devices->Num()>8) { Error=TEXT("Invalid fleet version/scene/devices");return false; }
    TArray<TSharedPtr<FJsonObject>> Drones,Gimbals;TSet<FString> Ids;
    for (auto Value : *Devices) {
        const TSharedPtr<FJsonObject>* Item=nullptr;FString Id,Kind,Model;
        if (!Value->TryGetObject(Item) || !(*Item)->TryGetStringField(TEXT("id"),Id) || !(*Item)->TryGetStringField(TEXT("kind"),Kind) || !(*Item)->TryGetStringField(TEXT("model_id"),Model) || Ids.Contains(Id) || Id.Len()!=6) { Error=TEXT("Invalid or duplicate fleet ID");return false; }
        if ((Kind==TEXT("drone") && (!Id.StartsWith(TEXT("uav-")) || (Model!=TEXT("mavic3") && Model!=TEXT("avata") && Model!=TEXT("fixedwing")))) || (Kind==TEXT("gimbal") && (!Id.StartsWith(TEXT("ptz-")) || Model!=TEXT("eo80"))) || (Kind!=TEXT("drone") && Kind!=TEXT("gimbal")) || Id.EndsWith(TEXT("-00")) || !FChar::IsDigit(Id[4]) || !FChar::IsDigit(Id[5])) { Error=TEXT("Invalid fleet model/kind/ID");return false; }
        for (const TCHAR* Key : {TEXT("position_cm"),TEXT("rotation_deg")}) {
            const TArray<TSharedPtr<FJsonValue>>* V=nullptr;
            if (!(*Item)->TryGetArrayField(Key,V) || V->Num()!=3) { Error=TEXT("Invalid fleet pose");return false; }
            for (auto N : *V) { double Number; if (!N->TryGetNumber(Number) || !FMath::IsFinite(Number) || FMath::Abs(Number)>(FString(Key)==TEXT("position_cm")?1e7:180)) { Error=TEXT("Invalid fleet coordinate");return false; } }
        }
        Ids.Add(Id);(Kind==TEXT("drone")?Drones:Gimbals).Add(*Item);
    }
    if (Drones.Num()<1 || Drones.Num()>4 || Gimbals.Num()<1 || Gimbals.Num()>4 || !Ids.Contains(TEXT("uav-01")) || !Ids.Contains(TEXT("ptz-01"))) { Error=TEXT("Require default IDs and 1-4 instances per kind");return false; }
    auto Sort=[](const auto& A,const auto& B){return A->GetStringField(TEXT("id"))<B->GetStringField(TEXT("id"));};Drones.Sort(Sort);Gimbals.Sort(Sort);
    for (auto Item : Gimbals) { FString Target;if (!Item->TryGetStringField(TEXT("tracking_target"),Target) || !Drones.ContainsByPredicate([&](auto D){return D->GetStringField(TEXT("id"))==Target;})) { Error=TEXT("Unknown tracking drone");return false; } }
    FleetManifest=Manifest;
    AActor* Mount=this;while (Mount->GetAttachParentActor()) Mount=Mount->GetAttachParentActor();
    TArray<AActor*> MountActors={Mount};Mount->GetAttachedActors(MountActors,false,true);
    const FTransform OriginalTransform=GetActorTransform(),OriginalDrone=Drone->GetActorTransform();
    auto Configure=[&](AWiseEyeDemo* Rig,int32 Index) {
        if (Index<Drones.Num()) {
            auto Item=Drones[Index];Rig->DroneId=Item->GetStringField(TEXT("id"));Item->TryGetStringField(TEXT("name"),Rig->DroneName);Rig->FlightOrigin=VectorField(Item,TEXT("position_cm"));Rig->InitialFlightOrigin=Rig->FlightOrigin;
            Rig->DynamicsActorName=FName(*FString::Printf(TEXT("Drone%d"),Index+1));Rig->InitialYawDegrees=VectorField(Item,TEXT("rotation_deg")).Y;
            Rig->Drone->SetActorLocation(Rig->FlightOrigin);
        } else { Rig->OwnsDrone=false;Rig->DroneId=DroneId; }
        if (Index<Gimbals.Num()) {
            auto Item=Gimbals[Index];Rig->GimbalId=Item->GetStringField(TEXT("id"));Rig->TrackingTargetId=Item->GetStringField(TEXT("tracking_target"));
            Item->TryGetStringField(TEXT("name"),Rig->GimbalName);
            const FVector Position=VectorField(Item,TEXT("position_cm")),R=VectorField(Item,TEXT("rotation_deg"));
            Rig->GimbalPlacementYaw=R.Y;
            if (Rig==this) Mount->AddActorWorldOffset(Position-GetActorLocation());else Rig->SetActorLocation(Position);
            Rig->SetActorRotation(OriginalTransform.Rotator()+FRotator(R.X,R.Y,R.Z));
        } else Rig->GimbalId.Empty();
    };
    // Clone the calibrated assemblies in memory; no Content asset is modified.
    for (int32 Index=1;Index<FMath::Max(Drones.Num(),Gimbals.Num());++Index) {
        auto* Rig=GetWorld()->SpawnActorDeferred<AWiseEyeDemo>(StaticClass(),OriginalTransform,this,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        Rig->FleetChild=true;Rig->FleetRoot=this;Rig->SceneId=SceneId;Rig->PlaySessionId=PlaySessionId;Rig->FlightBackend=FlightBackend;Rig->ThermalMaterial=ThermalMaterial;
        Rig->AutoReceiveInput=EAutoReceiveInput::Disabled;
        Rig->MinPitch=MinPitch;Rig->MaxPitch=MaxPitch;Rig->DynamicsVisualRotationOffset=DynamicsVisualRotationOffset;
        Rig->YawPivot->SetRelativeTransform(YawPivot->GetRelativeTransform());Rig->PitchPivot->SetRelativeTransform(PitchPivot->GetRelativeTransform());Rig->Camera->SetRelativeTransform(OpticalMount->GetRelativeTransform());
        Rig->VisibleOffsetCm=VisibleOffsetCm;Rig->InfraredOffsetCm=InfraredOffsetCm;Rig->VisibleBoresight=VisibleBoresight;Rig->InfraredBoresight=InfraredBoresight;
        Rig->LidarMount->SetRelativeTransform(LidarMount->GetRelativeTransform());
        Rig->LidarBody->SetRelativeTransform(LidarBody->GetRelativeTransform());
        if (Index<Drones.Num()) {
            Rig->Drone=GetWorld()->SpawnActor<AActor>();auto* Root=NewObject<USceneComponent>(Rig->Drone);Root->SetMobility(EComponentMobility::Movable);Rig->Drone->SetRootComponent(Root);Root->RegisterComponent();Rig->Drone->SetActorTransform(OriginalDrone);
            TMap<AActor*,AActor*> RotorMap;
            for (auto Rotor : Rotors) { auto* Copy=GetWorld()->SpawnActor<AWiseEyeRotor>();if (auto* Original=Cast<AWiseEyeRotor>(Rotor)) Copy->Direction=Original->Direction;Copy->AttachToActor(Rig->Drone,FAttachmentTransformRules::KeepRelativeTransform);Copy->SetActorRelativeTransform(Rotor->GetActorTransform().GetRelativeTransform(OriginalDrone));Rig->Rotors.Add(Copy);RotorMap.Add(Rotor,Copy); }
            for (auto Component : MavicVisualComponents) if (auto* Mesh=Cast<UStaticMeshComponent>(Component)) {
                AActor* MeshOwner=Rig->Drone;USceneComponent* Parent=Root;FTransform Reference=OriginalDrone;
                for (auto Pair : RotorMap) if (Mesh->GetOwner()==Pair.Key || Mesh->GetOwner()->IsAttachedTo(Pair.Key)) { MeshOwner=Pair.Value;Parent=MeshOwner->GetRootComponent();Reference=Pair.Key->GetActorTransform();break; }
                CopyMesh(Mesh,MeshOwner,Parent,Reference);
            }
        } else { Rig->Drone=Drone;Rig->OwnsDrone=false; }
        if (Index<Gimbals.Num()) for (AActor* Part : MountActors) {
            TArray<UStaticMeshComponent*> Meshes;Part->GetComponents(Meshes);
            for (auto Mesh : Meshes) if (Mesh!=LidarBody && Mesh->GetStaticMesh() && !Mesh->IsEditorOnly()) {
                USceneComponent* SourceAnchor=Base;USceneComponent* Anchor=Rig->Base;
                if (Mesh->IsAttachedTo(PitchPivot)) { SourceAnchor=PitchPivot;Anchor=Rig->PitchPivot; }
                else if (Mesh->IsAttachedTo(YawPivot)) { SourceAnchor=YawPivot;Anchor=Rig->YawPivot; }
                CopyMesh(Mesh,Rig,Anchor,SourceAnchor->GetComponentTransform());
            }
        }
        Configure(Rig,Index);const FTransform Desired=Rig->GetActorTransform();Rig->FinishSpawning(Desired);Rig->SetActorTransform(Desired);
        if (Index<Drones.Num()) { FString ModelError;Rig->SetDroneModel(Drones[Index]->GetStringField(TEXT("model_id")),ModelError); }
        TArray<UPrimitiveComponent*> OwnMeshes;Rig->GetComponents(OwnMeshes);for (auto Mesh : OwnMeshes) { Rig->Capture->HideComponent(Mesh);Rig->InfraredCapture->HideComponent(Mesh); }
        FleetRigs.Add(Rig);
    }
    Configure(this,0);FString ModelError;SetDroneModel(Drones[0]->GetStringField(TEXT("model_id")),ModelError);
    for (auto Rig : FleetRigs) { auto* Target=FindDevice(Rig->TrackingTargetId);Rig->TrackingDrone=Target?Target->Drone.Get():Drone.Get(); }
    return true;
}

AWiseEyeDemo* AWiseEyeDemo::SpawnLiveDevice(const TSharedPtr<FJsonObject>& Item,FString& Error)
{
    const bool IsDrone=Item->GetStringField(TEXT("kind"))==TEXT("drone");
    const FTransform Reference=GetActorTransform(),Body=Drone->GetActorTransform();
    auto* Rig=GetWorld()->SpawnActorDeferred<AWiseEyeDemo>(StaticClass(),Reference,this,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if (!Rig) {Error=TEXT("Could not allocate device");return nullptr;}
    Rig->FleetChild=true;Rig->FleetRoot=this;Rig->SceneId=SceneId;Rig->PlaySessionId=PlaySessionId;
    Rig->FlightBackend=FlightBackend;Rig->ThermalMaterial=ThermalMaterial;Rig->AutoReceiveInput=EAutoReceiveInput::Disabled;
    Rig->MinPitch=MinPitch;Rig->MaxPitch=MaxPitch;Rig->DynamicsVisualRotationOffset=DynamicsVisualRotationOffset;
    Rig->YawPivot->SetRelativeTransform(YawPivot->GetRelativeTransform());Rig->PitchPivot->SetRelativeTransform(PitchPivot->GetRelativeTransform());
    Rig->Camera->SetRelativeTransform(OpticalMount->GetRelativeTransform());
    Rig->VisibleOffsetCm=VisibleOffsetCm;Rig->InfraredOffsetCm=InfraredOffsetCm;
    Rig->VisibleBoresight=VisibleBoresight;Rig->InfraredBoresight=InfraredBoresight;
    Rig->LidarMount->SetRelativeTransform(LidarMount->GetRelativeTransform());Rig->LidarBody->SetRelativeTransform(LidarBody->GetRelativeTransform());
    const FVector Position=VectorField(Item,TEXT("position_cm")),Rotation=VectorField(Item,TEXT("rotation_deg"));
    if (IsDrone) {
        Rig->DroneId=Item->GetStringField(TEXT("id"));Rig->DroneName=Item->GetStringField(TEXT("name"));Rig->GimbalId.Empty();
        Rig->DynamicsActorName=FName(*Item->GetStringField(TEXT("dynamics_name")));
        Rig->InitialYawDegrees=Rotation.Y;Rig->FlightOrigin=Rig->InitialFlightOrigin=Position;
        Rig->Drone=GetWorld()->SpawnActor<AActor>();auto* Anchor=NewObject<USceneComponent>(Rig->Drone);
        Anchor->SetMobility(EComponentMobility::Movable);Rig->Drone->SetRootComponent(Anchor);Anchor->RegisterComponent();Rig->Drone->SetActorTransform(Body);
        TMap<AActor*,AActor*> RotorMap;
        for (auto Rotor:Rotors) if (IsValid(Rotor)) {
            auto* Copy=GetWorld()->SpawnActor<AWiseEyeRotor>();if (auto* Original=Cast<AWiseEyeRotor>(Rotor)) Copy->Direction=Original->Direction;
            Copy->AttachToActor(Rig->Drone,FAttachmentTransformRules::KeepRelativeTransform);Copy->SetActorRelativeTransform(Rotor->GetActorTransform().GetRelativeTransform(Body));
            Rig->Rotors.Add(Copy);RotorMap.Add(Rotor,Copy);
        }
        for (auto Component:MavicVisualComponents) if (auto* Mesh=Cast<UStaticMeshComponent>(Component)) {
            AActor* MeshOwner=Rig->Drone;USceneComponent* Parent=Anchor;FTransform Relative=Body;
            for (auto Pair:RotorMap) if (Mesh->GetOwner()==Pair.Key || Mesh->GetOwner()->IsAttachedTo(Pair.Key)) {MeshOwner=Pair.Value;Parent=MeshOwner->GetRootComponent();Relative=Pair.Key->GetActorTransform();break;}
            CopyMesh(Mesh,MeshOwner,Parent,Relative);
        }
        Rig->Drone->SetActorLocationAndRotation(Position,FRotator(0,Rotation.Y,0).Quaternion()*DynamicsVisualRotationOffset.Quaternion(),false,nullptr,ETeleportType::TeleportPhysics);
    } else {
        Rig->OwnsDrone=false;Rig->Drone=Drone;Rig->DroneId=DroneId;
        Rig->GimbalId=Item->GetStringField(TEXT("id"));Rig->GimbalName=Item->GetStringField(TEXT("name"));
        Rig->TrackingTargetId=Item->GetStringField(TEXT("tracking_target"));Rig->GimbalPlacementYaw=Rotation.Y;
        AActor* Mount=this;while (Mount->GetAttachParentActor()) Mount=Mount->GetAttachParentActor();
        TArray<AActor*> Parts={Mount};Mount->GetAttachedActors(Parts,false,true);
        for (auto* Part:Parts) {
            TArray<UStaticMeshComponent*> Meshes;Part->GetComponents(Meshes);
            for (auto* Mesh:Meshes) if (Mesh!=LidarBody && Mesh->GetStaticMesh() && !Mesh->IsEditorOnly()) {
                USceneComponent* Source=Base;USceneComponent* Target=Rig->Base;
                if (Mesh->IsAttachedTo(PitchPivot)) {Source=PitchPivot;Target=Rig->PitchPivot;}
                else if (Mesh->IsAttachedTo(YawPivot)) {Source=YawPivot;Target=Rig->YawPivot;}
                CopyMesh(Mesh,Rig,Target,Source->GetComponentTransform());
            }
        }
    }
    FTransform Desired=Reference;
    if (!IsDrone) {Desired.SetLocation(Position);Desired.SetRotation((Reference.Rotator()+FRotator(0,Rotation.Y-GimbalPlacementYaw,0)).Quaternion());}
    Rig->FinishSpawning(Desired);Rig->SetActorTransform(Desired);
    if (IsDrone && !Rig->SetDroneModel(Item->GetStringField(TEXT("model_id")),Error)) {
        TArray<AActor*> Parts;Rig->Drone->GetAttachedActors(Parts,false,true);for (auto* Part:Parts) Part->Destroy();Rig->Drone->Destroy();if (Rig->DroneView) Rig->DroneView->Destroy();Rig->Destroy();return nullptr;
    }
    TArray<UPrimitiveComponent*> Meshes;Rig->GetComponents(Meshes);
    for (auto* Mesh:Meshes) {Rig->Capture->HideComponent(Mesh);Rig->InfraredCapture->HideComponent(Mesh);}
    FleetRigs.Add(Rig);return Rig;
}

void AWiseEyeDemo::RemoveLiveDevice(const FString& Id)
{
    auto* Rig=FindDevice(Id);if (!Rig) return;
    if (Id==Rig->DroneId && Rig->OwnsDrone) {
        Rig->ReleaseAerial();Rig->AerialDemandUntil=0;
        TArray<AActor*> Parts;Rig->Drone->GetAttachedActors(Parts,false,true);for (auto* Part:Parts) Part->Destroy();Rig->Drone->Destroy();
        Rig->OwnsDrone=false;Rig->Drone=Drone;Rig->Rotors.Reset();Rig->MavicVisualComponents.Reset();
    } else {
        Rig->GimbalId.Empty();Rig->VisibleEnabled=Rig->InfraredEnabled=Rig->LidarEnabled=Rig->EventEnabled=false;
        Rig->RefreshSensors();Rig->SetActorHiddenInGame(true);
    }
    if (!Rig->OwnsDrone && Rig->GimbalId.IsEmpty() && Rig!=this) {FleetRigs.Remove(Rig);if (Rig->DroneView) Rig->DroneView->Destroy();Rig->Destroy();}
}

bool AWiseEyeDemo::EditLiveFleet(const TSharedPtr<FJsonObject>& Args,FString& Error)
{
    FString Run,Scene;double Revision;const TArray<TSharedPtr<FJsonValue>>* Changes=nullptr;
    if (FleetChild || !Args->TryGetStringField(TEXT("run_id"),Run) || Run!=PlaySessionId || !Args->TryGetStringField(TEXT("scene_id"),Scene) || Scene!=SceneId ||
        !Args->TryGetNumberField(TEXT("expected_revision"),Revision) || Revision!=RuntimeFleetRevision || !Args->TryGetArrayField(TEXT("changes"),Changes) || Changes->Num()>16)
    {Error=TEXT("Current scene/run and fleet revision required; reread devices");return false;}
    TMap<FString,FString> Kinds;TSet<FString> Patched;
    for (const auto& V:DeviceInventory()) {auto D=V->AsObject();Kinds.Add(D->GetStringField(TEXT("id")),D->GetStringField(TEXT("kind")));}
    for (const auto& V:*Changes) {
        const TSharedPtr<FJsonObject>* C=nullptr;FString Action,Id;
        if (!V->TryGetObject(C) || !(*C)->TryGetStringField(TEXT("action"),Action) || !(*C)->TryGetStringField(TEXT("id"),Id) || Patched.Contains(Id)) {Error=TEXT("Invalid/duplicate change");return false;}
        Patched.Add(Id);
        if (Action==TEXT("remove")) {if (Id==TEXT("uav-01") || Id==TEXT("ptz-01")) {Error=TEXT("Default IDs must remain");return false;}Kinds.Remove(Id);}
        else if (Action==TEXT("add")) {
            FString Kind,Name,Model;
            if (Kinds.Contains(Id) || !(*C)->TryGetStringField(TEXT("kind"),Kind) || (Kind!=TEXT("drone") && Kind!=TEXT("gimbal")) || Id.Len()!=6 ||
                !Id.StartsWith(Kind==TEXT("drone")?TEXT("uav-"):TEXT("ptz-")) || !FChar::IsDigit(Id[4]) || !FChar::IsDigit(Id[5]) || Id.EndsWith(TEXT("-00")) ||
                !(*C)->TryGetStringField(TEXT("name"),Name) || Name.IsEmpty() || Name.Len()>60 || !(*C)->TryGetStringField(TEXT("model_id"),Model)) {Error=TEXT("Invalid added device");return false;}
            Kinds.Add(Id,Kind);
        }
    }
    int32 DroneCount=0,GimbalCount=0;for (const auto& Pair:Kinds) {if (Pair.Value==TEXT("drone")) ++DroneCount;else ++GimbalCount;}
    if (DroneCount<1 || DroneCount>4 || GimbalCount<1 || GimbalCount>4) {Error=TEXT("Require 1-4 UAVs and 1-4 gimbals");return false;}
    for (const auto& V:*Changes) {
        const TSharedPtr<FJsonObject>* C=nullptr;FString Action,Id;
        if (!V->TryGetObject(C) || !(*C)->TryGetStringField(TEXT("action"),Action) || !(*C)->TryGetStringField(TEXT("id"),Id)) {Error=TEXT("Invalid device change");return false;}
        auto* Target=FindDevice(Id);
        if (Action==TEXT("remove")) {if (!Target || Id==TEXT("uav-01") || Id==TEXT("ptz-01")) {Error=TEXT("Cannot remove missing/default device");return false;}
            if (Id==Target->DroneId && Target->OwnsDrone && (Target->FixedwingActive || Target->RotorsRunning)) {Error=TEXT("Stop the edited aircraft before removal");return false;}continue;}
        if (Action!=TEXT("add") && Action!=TEXT("update")) {Error=TEXT("Unknown device change");return false;}
        if ((Action==TEXT("add"))==(Target!=nullptr)) {Error=TEXT("Device already exists or disappeared");return false;}
        FString Name,Tracking;
        if ((*C)->HasField(TEXT("name")) && (!(*C)->TryGetStringField(TEXT("name"),Name) || Name.IsEmpty() || Name.Len()>60)) {Error=TEXT("Invalid name");return false;}
        if ((*C)->HasField(TEXT("tracking_target")) && (!(*C)->TryGetStringField(TEXT("tracking_target"),Tracking) || Kinds.FindRef(Id)!=TEXT("gimbal") || Kinds.FindRef(Tracking)!=TEXT("drone"))) {Error=TEXT("Invalid tracking target");return false;}
        if (Action==TEXT("add") && Kinds.FindRef(Id)==TEXT("gimbal") && !(*C)->HasField(TEXT("tracking_target"))) {Error=TEXT("Gimbal tracking target required");return false;}
        if (Action==TEXT("add") || (*C)->HasField(TEXT("position_cm")) || (*C)->HasField(TEXT("rotation_deg"))) {
            for (auto Key:{TEXT("position_cm"),TEXT("rotation_deg")}) if ((*C)->HasField(Key) || Action==TEXT("add")) {
                const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
                if (!(*C)->TryGetArrayField(Key,Values) || Values->Num()!=3) {Error=TEXT("Three pose coordinates required");return false;}
                for (const auto& N:*Values) {double Number;if (!N->TryGetNumber(Number) || !FMath::IsFinite(Number) || FMath::Abs(Number)>(FString(Key)==TEXT("position_cm")?1e7:180)) {Error=TEXT("Invalid pose");return false;}}
            }
            if (Target && Target->OwnsDrone && Id==Target->DroneId && (Target->FixedwingActive || Target->RotorsRunning)) {Error=TEXT("Stop or land the edited UAV before changing pose");return false;}
            if (Kinds.FindRef(Id)==TEXT("drone") && (*C)->HasField(TEXT("rotation_deg"))) {
                const FVector Rotation=VectorField(*C,TEXT("rotation_deg"));
                if (Rotation.X!=0 || Rotation.Z!=0) {Error=TEXT("Initial aircraft pitch/roll must be zero");return false;}
            }
        }
        FString Model;
        if ((*C)->TryGetStringField(TEXT("model_id"),Model)) {
            if (Model!=TEXT("mavic3") && Model!=TEXT("avata") && Model!=TEXT("fixedwing") && Model!=TEXT("eo80")) {Error=TEXT("Invalid model");return false;}
            if ((Model==TEXT("eo80"))!=(Kinds.FindRef(Id)==TEXT("gimbal"))) {Error=TEXT("Model/kind mismatch");return false;}
            if (Model==TEXT("fixedwing") && !LoadObject<UStaticMesh>(nullptr,TEXT("/Game/WISEYE/DroneModels/Fixedwing/FixedwingUAV_gray.FixedwingUAV_gray"))) {Error=TEXT("Fixed-wing asset missing");return false;}
        }
        if (Kinds.FindRef(Id)==TEXT("drone")) {
            FString Slot;
            if (Action==TEXT("add")) {if (!(*C)->TryGetStringField(TEXT("dynamics_name"),Slot) || (Slot!=TEXT("Drone1") && Slot!=TEXT("Drone2") && Slot!=TEXT("Drone3") && Slot!=TEXT("Drone4"))) {Error=TEXT("Reserved flight slot required");return false;}}
            const FString FutureModel=Model.IsEmpty()?(Target?Target->DroneModel:FString()):Model;
            const bool Cross=Target && (FutureModel==TEXT("fixedwing"))!=(Target->DroneModel==TEXT("fixedwing"));
            if (Cross && (Target->FixedwingActive || Target->RotorsRunning)) {Error=TEXT("Stop the aircraft before changing airframe");return false;}
            if (FutureModel!=TEXT("fixedwing") && (Action==TEXT("add") || Cross || (*C)->HasField(TEXT("position_cm")) || (*C)->HasField(TEXT("rotation_deg")))) {
                AActor* Source=nullptr;const FName Desired=Target?Target->DynamicsActorName:FName(*Slot);
                for (TActorIterator<AActor> It(GetWorld());It;++It) if (It->GetFName()==Desired) {Source=*It;break;}
                const FVector Position=(*C)->HasField(TEXT("position_cm"))?VectorField(*C,TEXT("position_cm")):Target->Drone->GetActorLocation();
                const float Yaw=(*C)->HasField(TEXT("rotation_deg"))?VectorField(*C,TEXT("rotation_deg")).Y:Target->InitialYawDegrees;
                if (!Source || !Source->GetActorLocation().Equals(Position,5.f) || FMath::Abs(FMath::FindDeltaAngleDegrees(Source->GetActorRotation().Yaw,Yaw))>1.f) {Error=FString::Printf(TEXT("Apply drone placement through the flight controller first: %s actual=%s desired=%s yaw=%f"),*Desired.ToString(),Source?*Source->GetActorLocation().ToString():TEXT("missing actor"),*Position.ToString(),Yaw);return false;}
            }
        }
    }
    // Allocate additions before changing existing devices; roll back allocations on failure.
    TArray<FString> Added;
    for (const auto& V:*Changes) {auto C=V->AsObject();if (C->GetStringField(TEXT("action"))==TEXT("add")) {
        if (!SpawnLiveDevice(C,Error)) {for (const auto& Id:Added) RemoveLiveDevice(Id);return false;}
        Added.Add(C->GetStringField(TEXT("id")));
    }}
    for (const auto& V:*Changes) {
        auto C=V->AsObject();const FString Id=C->GetStringField(TEXT("id")),Action=C->GetStringField(TEXT("action"));
        if (Action==TEXT("remove")) continue;
        auto* Target=FindDevice(Id);FString Text;
        if (C->TryGetStringField(TEXT("name"),Text)) {if (Id==Target->GimbalId) Target->GimbalName=Text;else Target->DroneName=Text;}
        if (Action==TEXT("update") && C->TryGetStringField(TEXT("model_id"),Text) && Id==Target->DroneId) {
            if (!Target->SetDroneModel(Text,Error)) return false;
            Target->DynamicsSource=nullptr;Target->DynamicsConnected=false;Target->TryBindDynamicsSource();
        }
        if (C->HasField(TEXT("position_cm")) || C->HasField(TEXT("rotation_deg"))) {
            const FVector Position=C->HasField(TEXT("position_cm"))?VectorField(C,TEXT("position_cm")):(Id==Target->GimbalId?Target->GetActorLocation():Target->Drone->GetActorLocation());
            const float Yaw=C->HasField(TEXT("rotation_deg"))?VectorField(C,TEXT("rotation_deg")).Y:(Id==Target->GimbalId?Target->GimbalPlacementYaw:Target->InitialYawDegrees);
            if (Action==TEXT("update") && !ApplyDevicePlacement(Id,Position,Yaw,Error)) return false;
        }
        if (C->TryGetStringField(TEXT("tracking_target"),Text)) Target->TrackingTargetId=Text;
    }
    for (const auto& V:*Changes) {auto C=V->AsObject();if (C->GetStringField(TEXT("action"))==TEXT("remove")) RemoveLiveDevice(C->GetStringField(TEXT("id")));}
    for (auto Rig:FleetRigs) {auto* Target=FindDevice(Rig->TrackingTargetId);Rig->TrackingDrone=Target?Target->Drone.Get():Drone.Get();}
    if (!FindDevice(ControlledDroneId)) ControlledDroneId=TEXT("uav-01");
    if (!FindDevice(ControlledGimbalId)) ControlledGimbalId=TEXT("ptz-01");
    ++RuntimeFleetRevision;SetObserverMode(ObserverMode);return true;
}
