#include "WiseEyePopulation.h"
#include "WiseEyeDemo.h"
#include "Components/SceneCaptureComponent2D.h"
#include "WiseEyeRuntimePaths.h"
#if WISEYE_WITH_CITY_POPULATION
#include "MassSpawner.h"
#include "MassEntitySubsystem.h"
#include "MassEntityQuery.h"
#include "MassExecutionContext.h"
#include "MassCommonFragments.h"
#include "MassCrowdFragments.h"
#include "MassTrafficFragments.h"
#include "EngineUtils.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "UObject/UnrealType.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "MassEntityConfigAsset.h"
#include "MassTrafficVehicleVisualizationTrait.h"
#include "MassTrafficParkedVehicleVisualizationTrait.h"
#include "MassCrowdVisualizationTrait.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/UObjectIterator.h"
#include "MassVisualizer.h"

void UWiseEyePopulationWatch::Prepare() {
    if (Prepared || Preparing || !Spawner.IsValid()) return;
    // MassSpawner exposes count but keeps entity types protected; read its
    // reflected array without modifying the map or original config packages.
    auto* Property=FindFProperty<FArrayProperty>(AMassSpawner::StaticClass(),TEXT("EntityTypes"));
    auto* Types=Property?Property->ContainerPtrToValuePtr<TArray<FMassSpawnedEntityType>>(Spawner.Get()):nullptr;
    TArray<FSoftObjectPath> Paths;
    if (Types) for (const auto& Type:*Types) if (!Type.EntityConfig.IsNull()) Paths.AddUnique(Type.EntityConfig.ToSoftObjectPath());
    if (Paths.IsEmpty()) {PreloadError=TEXT("No entity configurations available");Prepared=true;return;}
    Preparing=true;
    AssetHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateWeakLambda(this,[this,Paths]() {
        if (!Spawner.IsValid() || !Spawner->GetWorld() || Spawner->GetWorld()->bIsTearingDown) return;
        for (const auto& Path:Paths) {
            auto* Config=Cast<UMassEntityConfigAsset>(Path.ResolveObject());
            if (!Config) {PreloadError=TEXT("Could not preload ")+Path.ToString();continue;}
            TSet<const UMassEntityConfigAsset*> Visited;
            for (const auto* Parent=Config;Parent && !Visited.Contains(Parent);Parent=Parent->GetConfig().GetParent()) {
                Visited.Add(Parent);
                for (auto* Trait:Parent->GetConfig().GetTraits()) {
                    auto* Visual=Cast<UMassVisualizationTrait>(Trait);
                    if (Visual && (Trait->IsA<UMassCrowdVisualizationTrait>() || Trait->IsA<UMassTrafficVehicleVisualizationTrait>() || Trait->IsA<UMassTrafficParkedVehicleVisualizationTrait>())) {
                        // Passive targets retain native lane simulation, without
                        // converting to expensive vehicle Actors near any viewer.
                        Visual->Params.LODRepresentation[EMassLOD::High]=EMassRepresentationType::StaticMeshInstance;
                        Visual->Params.LODRepresentation[EMassLOD::Medium]=EMassRepresentationType::StaticMeshInstance;
                        Visual->Params.bKeepLowResActors=false;Visual->Params.bKeepActorExtraFrame=false;
                        Visual->Params.bSpreadFirstVisualizationUpdate=true;
                        // Identify only the actual passive population meshes, not
                        // arbitrary city assets. No source package is saved.
                        for (TActorIterator<AWiseEyeDemo> It(Spawner->GetWorld());It;++It) if (!It->FleetChild) {
                            for (const auto& Desc:Visual->StaticMeshInstanceDesc.Meshes) if (Desc.Mesh)
                                It->PopulationThermalMeshes.Add(Desc.Mesh.Get(),Kind==TEXT("pedestrian")?17:16);
                            break;
                        }
                        if (Trait->IsA<UMassCrowdVisualizationTrait>()) {
                            Visual->LODParams.LODMaxCount[EMassLOD::Low]=2000;
                            Visual->LODParams.VisibleLODDistance[EMassLOD::Off]=60000.f;
                        }
                    }
                }
            }
            Config->GetOrCreateEntityTemplate(*Spawner->GetWorld());
        }
        Preparing=false;Prepared=true;
    }));
}

void UWiseEyePopulationWatch::Finished() {
    Pending=false;
    // A disabled population must not reappear when an older async spawn finishes.
    if (Desired==0 && Spawner.IsValid()) Spawner->DoDespawning();
}
void UWiseEyePopulationWatch::Apply() {
    if (!Spawner.IsValid() || (Desired>0 && !Prepared) || Pending || Applied==Desired) return;
    if (!PreloadError.IsEmpty()) {Applied=Desired;return;}
    Spawner->DoDespawning();Applied=Desired;
    Spawner->ScaleSpawningCount(BaseCount>0?float(Desired)/BaseCount:0);
    if (Desired>0) {Pending=true;Spawner->DoSpawning();}
}

void AWiseEyeDemo::InitializeObservation() {
    if (FleetChild) return;
    FString Text;TSharedPtr<FJsonObject> Saved;
    if (FFileHelper::LoadFileToString(Text,*FPaths::Combine(WiseEyePaths::ConfigRoot(),TEXT("WISEYE/Observation"),SceneId+TEXT(".json"))) &&
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Saved) && Saved) {
        const TSharedPtr<FJsonObject>* Pop=nullptr;
        if (Saved->TryGetObjectField(TEXT("population"),Pop)) {FString Error;ConfigurePopulation(*Pop,Error);}
        const TSharedPtr<FJsonObject>* Cameras=nullptr;
        if (Saved->TryGetObjectField(TEXT("aerial"),Cameras)) for (auto Rig:FleetRigs) if (Rig->OwnsDrone) {
            const TSharedPtr<FJsonObject>* CameraSettings=nullptr;
            if ((*Cameras)->TryGetObjectField(Rig->DroneId,CameraSettings)) {FString Error;Rig->ConfigureAerial(*CameraSettings,Error);}
        }
    }
    PopulationNextScan=0;PopulationWarmup=GetWorld()->GetTimeSeconds()+5;
}

TSharedPtr<FJsonObject> AWiseEyeDemo::PopulationState() const {
    const auto* Root=FleetRoot?FleetRoot.Get():this;
    auto R=MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("vehicles_enabled"),Root->PopulationVehicles);R->SetNumberField(TEXT("vehicle_density"),Root->PopulationVehicleDensity);
    R->SetBoolField(TEXT("pedestrians_enabled"),Root->PopulationPedestrians);R->SetNumberField(TEXT("pedestrian_density"),Root->PopulationPedestrianDensity);
    TArray<TSharedPtr<FJsonValue>> Spawners;int32 Cars=0,People=0;bool Pending=false;
    for (auto W:Root->PopulationWatches) if (W && W->Spawner.IsValid()) {
        auto S=MakeShared<FJsonObject>();S->SetStringField(TEXT("kind"),W->Kind);
        S->SetNumberField(TEXT("requested_count"),W->Desired);S->SetBoolField(TEXT("pending"),W->Preparing || W->Pending || W->Applied!=W->Desired);
        S->SetBoolField(TEXT("preloading"),W->Preparing);S->SetStringField(TEXT("preload_error"),W->PreloadError);
        S->SetNumberField(TEXT("applied_count"),W->Applied);S->SetStringField(TEXT("spawner"),W->Spawner->GetName());
        S->SetNumberField(TEXT("base_count"),W->BaseCount);
        Spawners.Add(MakeShared<FJsonValueObject>(S));
        if (W->Kind==TEXT("pedestrian")) People++;else Cars++;
        Pending|=W->Preparing || W->Pending || W->Applied!=W->Desired;
    }
    R->SetNumberField(TEXT("thermal_body_proxy_components"),Root->PopulationThermalComponents);
    R->SetNumberField(TEXT("thermal_people_components"),Root->PopulationThermalPeople);R->SetNumberField(TEXT("thermal_vehicle_components"),Root->PopulationThermalVehicles);
    R->SetArrayField(TEXT("spawners"),Spawners);R->SetBoolField(TEXT("vehicles_supported"),Cars>0);R->SetBoolField(TEXT("pedestrians_supported"),People>0);
    if (auto* Scale=IConsoleManager::Get().FindConsoleVariable(TEXT("ai.mass.scalability.SpawnDensityMultiplier"))) R->SetNumberField(TEXT("engine_density_scale"),Scale->GetFloat());
    R->SetBoolField(TEXT("pending"),Pending || Root->GetWorld()->GetTimeSeconds()<FMath::Max(Root->PopulationWarmup,Root->PopulationApplyAt));
    R->SetStringField(TEXT("count_semantics"),TEXT("requested/applied spawn budget, not observed agent count; density is relative to bounded map capacity"));
    return R;
}

bool AWiseEyeDemo::ConfigurePopulation(const TSharedPtr<FJsonObject>& Args,FString& Error) {
    auto* Root=FleetRoot?FleetRoot.Get():this;
    bool Cars,People;double CarDensity,PeopleDensity;
    if (!Args->TryGetBoolField(TEXT("vehicles_enabled"),Cars) || !Args->TryGetBoolField(TEXT("pedestrians_enabled"),People) ||
        !Args->TryGetNumberField(TEXT("vehicle_density"),CarDensity) || !Args->TryGetNumberField(TEXT("pedestrian_density"),PeopleDensity) ||
        !FMath::IsFinite(CarDensity) || CarDensity<0 || CarDensity>1 || !FMath::IsFinite(PeopleDensity) || PeopleDensity<0 || PeopleDensity>1) {
        Error=TEXT("Population requires vehicles_enabled/pedestrians_enabled and vehicle_density/pedestrian_density 0..1");return false;
    }
    Root->PopulationVehicles=Cars;Root->PopulationPedestrians=People;
    Root->PopulationVehicleDensity=CarDensity;Root->PopulationPedestrianDensity=PeopleDensity;
    Root->PopulationApplyAt=Root->GetWorld()->GetTimeSeconds()+.4;
    return true;
}

void AWiseEyeDemo::UpdatePopulation() {
    const double Now=GetWorld()->GetTimeSeconds();
    if (Now>=PopulationThermalNext) {
        PopulationThermalNext=Now+2;PopulationThermalComponents=PopulationThermalPeople=PopulationThermalVehicles=0;
        for (TObjectIterator<UInstancedStaticMeshComponent> It;It;++It) {
            if (It->GetWorld()!=GetWorld() || !It->GetStaticMesh() || It->GetInstanceCount()==0) continue;
            const auto* Code=PopulationThermalMeshes.Find(It->GetStaticMesh());
            // Crowd VAT descriptions are assembled per entity, after template
            // construction. Classify only the Mass visualizer's known VAT path.
            const bool Person=It->GetOwner() && It->GetOwner()->IsA<AMassVisualizer>() && It->GetStaticMesh()->GetPathName().StartsWith(TEXT("/Game/Crowd/VAT/Meshes/"));
            uint8 Heat=Person?17:Code?*Code:0;if (!Heat) continue;
            if (It->bRenderCustomDepth && !It->ComponentHasTag(TEXT("WISEYE_PopulationHeat"))) continue;
            if (!It->ComponentHasTag(TEXT("WISEYE_PopulationHeat"))) {It->ComponentTags.Add(TEXT("WISEYE_PopulationHeat"));It->SetRenderCustomDepth(true);It->SetCustomDepthStencilValue(Heat);}
            ++PopulationThermalComponents;
            if (Person) ++PopulationThermalPeople;else ++PopulationThermalVehicles;
        }
    }
    if (Now>=PopulationNextScan) {
        PopulationNextScan=Now+2;
        for (TActorIterator<AMassSpawner> It(GetWorld());It;++It) {
            const FString Name=It->GetClass()->GetName();FString Kind;
            if (Name.Contains(TEXT("CrowdSpawner"))) Kind=TEXT("pedestrian");
            else if (Name.Contains(TEXT("ParkedVehicleSpawner"))) Kind=TEXT("parked_vehicle");
            else if (Name.Contains(TEXT("TrafficVehicleSpawner"))) Kind=TEXT("vehicle");
            else continue; // Do not modify intersections / traffic signal logic.
            if (PopulationWatches.ContainsByPredicate([&](auto W){return W && W->Spawner.Get()==*It;})) continue;
            auto* W=NewObject<UWiseEyePopulationWatch>(this);W->Spawner=*It;W->Kind=Kind;W->BaseCount=FMath::Max(1,It->GetCount());
            It->OnSpawningFinishedEvent.AddDynamic(W,&UWiseEyePopulationWatch::Finished);
            PopulationWatches.Add(W);
        }
    }
    int32 CarSpawners=0,PedSpawners=0,ParkSpawners=0;
    for (auto W:PopulationWatches) if (W->Spawner.IsValid()) {
        if (W->Kind==TEXT("pedestrian")) PedSpawners++;else if (W->Kind==TEXT("parked_vehicle")) ParkSpawners++;else CarSpawners++;
    }
    for (auto W:PopulationWatches) if (W->Spawner.IsValid()) {
        const bool Ped=W->Kind==TEXT("pedestrian"),Park=W->Kind==TEXT("parked_vehicle");
        const int32 Capacity=Ped?1200:600,Divisor=Ped?PedSpawners:Park?ParkSpawners:CarSpawners;
        W->Desired=(Ped?PopulationPedestrians:PopulationVehicles)?FMath::RoundToInt(Capacity*(Ped?PopulationPedestrianDensity:PopulationVehicleDensity)/FMath::Max(1,Divisor)):0;
        if (W->Desired>0) W->Prepare();
        if (Now>=PopulationWarmup && Now>=PopulationApplyAt) W->Apply();
    }
}

bool AWiseEyeDemo::SaveObservation(FString& Error) const {
    const auto* Root=FleetRoot?FleetRoot.Get():this;
    auto R=MakeShared<FJsonObject>(),Cameras=MakeShared<FJsonObject>();
    for (auto Rig:Root->FleetRigs) if (Rig->OwnsDrone) Cameras->SetObjectField(Rig->DroneId,Rig->AerialState());
    R->SetObjectField(TEXT("aerial"),Cameras);R->SetObjectField(TEXT("population"),Root->PopulationState());
    FString Text;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Text));
    const FString Path=FPaths::Combine(WiseEyePaths::ConfigRoot(),TEXT("WISEYE/Observation"),SceneId+TEXT(".json"));
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);
    if (!FFileHelper::SaveStringToFile(Text,*Path)) {Error=TEXT("Could not save observation settings");return false;}
    return true;
}

TSharedPtr<FJsonObject> AWiseEyeDemo::PopulationAgents(const FString& FromCamera) const {
    auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("run_id"),PlaySessionId);
    const auto* Root=FleetRoot?FleetRoot.Get():this;const auto* CameraRig=FromCamera.IsEmpty()?nullptr:Root->FindDevice(FromCamera);
    auto* Lens=CameraRig?CameraRig->AerialCapture.Get():nullptr;
    FCollisionQueryParams Visibility(SCENE_QUERY_STAT(WiseEyePopulationVisibility),true,this);
    if (CameraRig) {if (CameraRig->Drone) Visibility.AddIgnoredActor(CameraRig->Drone);if (CameraRig->DynamicsSource) Visibility.AddIgnoredActor(CameraRig->DynamicsSource);}
    R->SetBoolField(TEXT("los_camera_available"),Lens!=nullptr);
    auto* Sub=GetWorld()->GetSubsystem<UMassEntitySubsystem>();
    if (!Sub) return R;
    auto& Manager=Sub->GetMutableEntityManager();
    auto Gather=[&](UScriptStruct* Tag,const TCHAR* Kind) {
        FMassEntityQuery Query(Manager.AsShared());Query.AddTagRequirement(*Tag,EMassFragmentPresence::All);
        Query.AddRequirement<FTransformFragment>(EMassFragmentAccess::ReadOnly);
        auto Context=Manager.CreateExecutionContext(0);int32 Count=0;TArray<TSharedPtr<FJsonValue>> Samples;
        Query.ForEachEntityChunk(Context,[&](FMassExecutionContext& Chunk) {
            const auto Transforms=Chunk.GetFragmentView<FTransformFragment>();Count+=Chunk.GetNumEntities();
            for (int32 I=0;I<Chunk.GetNumEntities() && Samples.Num()<256;++I) {
                const auto P=Transforms[I].GetTransform().GetLocation();auto S=MakeShared<FJsonObject>();
                S->SetNumberField(TEXT("entity_index"),Chunk.GetEntity(I).Index);
                S->SetNumberField(TEXT("entity_serial"),Chunk.GetEntity(I).SerialNumber);
                S->SetStringField(TEXT("target_id"),PlaySessionId+TEXT("/")+Kind+FString::Printf(TEXT("/%d/%d"),Chunk.GetEntity(I).Index,Chunk.GetEntity(I).SerialNumber));
                S->SetStringField(TEXT("class_name"),FString(Kind)==TEXT("pedestrian")?TEXT("person"):TEXT("vehicle"));
                S->SetArrayField(TEXT("position_cm"),{MakeShared<FJsonValueNumber>(P.X),MakeShared<FJsonValueNumber>(P.Y),MakeShared<FJsonValueNumber>(P.Z)});
                if (Lens) {
                    const FVector Origin=Lens->GetComponentLocation(),Aim=P+FVector(0,0,100);FHitResult Hit;
                    const bool Blocked=GetWorld()->LineTraceSingleByChannel(Hit,Origin,Aim,ECC_Visibility,Visibility) && Hit.Distance<FVector::Distance(Origin,Aim)-300;
                    S->SetBoolField(TEXT("los_clear"),!Blocked);
                    S->SetStringField(TEXT("los_model"),TEXT("collision ray to position+1m, 3m end tolerance; not pixel visibility or GT"));
                }
                Samples.Add(MakeShared<FJsonValueObject>(S));
            }
        });
        auto S=MakeShared<FJsonObject>();S->SetNumberField(TEXT("active_entities"),Count);S->SetBoolField(TEXT("samples_truncated"),Count>Samples.Num());S->SetArrayField(TEXT("samples"),Samples);R->SetObjectField(Kind,S);
    };
    Gather(FMassTrafficVehicleTag::StaticStruct(),TEXT("vehicle"));Gather(FMassTrafficParkedVehicleTag::StaticStruct(),TEXT("parked_vehicle"));Gather(FMassCrowdTag::StaticStruct(),TEXT("pedestrian"));
    return R;
}

#else

#include "WiseEyeRuntimePaths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
void UWiseEyePopulationWatch::Prepare() { Prepared=true; }
void UWiseEyePopulationWatch::Finished() { Pending=false; }
void UWiseEyePopulationWatch::Apply() {}
TSharedPtr<FJsonObject> AWiseEyeDemo::PopulationState() const {
    auto R=MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("vehicles_supported"),false);
    R->SetBoolField(TEXT("pedestrians_supported"),false);
    R->SetBoolField(TEXT("vehicles_enabled"),false);
    R->SetBoolField(TEXT("pedestrians_enabled"),false);
    R->SetNumberField(TEXT("vehicle_density"),0);
    R->SetNumberField(TEXT("pedestrian_density"),0);
    R->SetBoolField(TEXT("pending"),false);
    R->SetArrayField(TEXT("spawners"),{});
    R->SetStringField(TEXT("unavailable_reason"),TEXT("City Sample population adapter not installed"));
    return R;
}
bool AWiseEyeDemo::ConfigurePopulation(const TSharedPtr<FJsonObject>& Args,FString& Error) {
    bool Cars=false,People=false;double CarDensity=0,PeopleDensity=0;
    if (!Args->TryGetBoolField(TEXT("vehicles_enabled"),Cars) || !Args->TryGetBoolField(TEXT("pedestrians_enabled"),People) ||
        !Args->TryGetNumberField(TEXT("vehicle_density"),CarDensity) || !Args->TryGetNumberField(TEXT("pedestrian_density"),PeopleDensity) ||
        !FMath::IsFinite(CarDensity) || CarDensity<0 || CarDensity>1 || !FMath::IsFinite(PeopleDensity) || PeopleDensity<0 || PeopleDensity>1) {
        Error=TEXT("Population requires enabled flags and finite densities in 0..1");return false;
    }
    if (Cars || People) {Error=TEXT("City Sample population adapter not installed");return false;}
    PopulationVehicles=PopulationPedestrians=false;return true;
}
void AWiseEyeDemo::UpdatePopulation() {}
TSharedPtr<FJsonObject> AWiseEyeDemo::PopulationAgents(const FString&) const {
    auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("run_id"),PlaySessionId);
    R->SetBoolField(TEXT("supported"),false);
    R->SetStringField(TEXT("unavailable_reason"),TEXT("City Sample population adapter not installed"));
    return R;
}
void AWiseEyeDemo::InitializeObservation() {
    if (FleetChild) return;
    FString Text;TSharedPtr<FJsonObject> Saved;
    if (FFileHelper::LoadFileToString(Text,*FPaths::Combine(WiseEyePaths::ConfigRoot(),TEXT("WISEYE/Observation"),SceneId+TEXT(".json"))) &&
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Saved) && Saved) {
        const TSharedPtr<FJsonObject>* Pop=nullptr;
        if (Saved->TryGetObjectField(TEXT("population"),Pop)) {FString Error;ConfigurePopulation(*Pop,Error);}
        const TSharedPtr<FJsonObject>* Cameras=nullptr;
        if (Saved->TryGetObjectField(TEXT("aerial"),Cameras)) for (auto Rig:FleetRigs) if (Rig->OwnsDrone) {
            const TSharedPtr<FJsonObject>* CameraSettings=nullptr;
            if ((*Cameras)->TryGetObjectField(Rig->DroneId,CameraSettings)) {FString Error;Rig->ConfigureAerial(*CameraSettings,Error);}
        }
    }
    PopulationNextScan=0;PopulationWarmup=GetWorld()->GetTimeSeconds()+5;
}

bool AWiseEyeDemo::SaveObservation(FString& Error) const {
    const auto* Root=FleetRoot?FleetRoot.Get():this;
    auto R=MakeShared<FJsonObject>(),Cameras=MakeShared<FJsonObject>();
    for (auto Rig:Root->FleetRigs) if (Rig->OwnsDrone) Cameras->SetObjectField(Rig->DroneId,Rig->AerialState());
    R->SetObjectField(TEXT("aerial"),Cameras);R->SetObjectField(TEXT("population"),Root->PopulationState());
    FString Text;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Text));
    const FString Path=FPaths::Combine(WiseEyePaths::ConfigRoot(),TEXT("WISEYE/Observation"),SceneId+TEXT(".json"));
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);
    if (!FFileHelper::SaveStringToFile(Text,*Path)) {Error=TEXT("Could not save observation settings");return false;}
    return true;
}


#endif
