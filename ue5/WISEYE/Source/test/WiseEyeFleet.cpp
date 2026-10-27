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
            Item->SetArrayField(TEXT("initial_position_cm"),{MakeShared<FJsonValueNumber>(Rig->FlightOrigin.X),MakeShared<FJsonValueNumber>(Rig->FlightOrigin.Y),MakeShared<FJsonValueNumber>(Rig->FlightOrigin.Z)});
            Item->SetBoolField(TEXT("rotors_running"),Rig->RotorsRunning);
            Item->SetNumberField(TEXT("initial_yaw_deg"),Rig->InitialYawDegrees);
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
    if (GimbalId.IsEmpty()) { VisibleEnabled=false;InfraredEnabled=false;LidarEnabled=false;RefreshSensors();SetActorHiddenInGame(true); }
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
        if ((Kind==TEXT("drone") && (!Id.StartsWith(TEXT("uav-")) || (Model!=TEXT("mavic3") && Model!=TEXT("avata")))) || (Kind==TEXT("gimbal") && (!Id.StartsWith(TEXT("ptz-")) || Model!=TEXT("eo80"))) || (Kind!=TEXT("drone") && Kind!=TEXT("gimbal")) || Id.EndsWith(TEXT("-00")) || !FChar::IsDigit(Id[4]) || !FChar::IsDigit(Id[5])) { Error=TEXT("Invalid fleet model/kind/ID");return false; }
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
        Rig->YawPivot->SetRelativeTransform(YawPivot->GetRelativeTransform());Rig->PitchPivot->SetRelativeTransform(PitchPivot->GetRelativeTransform());Rig->Camera->SetRelativeTransform(Camera->GetRelativeTransform());
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
