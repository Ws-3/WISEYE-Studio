#include "WiseEyeDemo.h"

#include "EngineUtils.h"
#include "GameFramework/Actor.h"
#include "Components/StaticMeshComponent.h"

bool AWiseEyeDemo::TryBindDynamicsSource()
{
    if (FlightBackend!=EWiseEyeFlightBackend::ProjectAirSim) return false;
    if (IsValid(DynamicsSource))
    {
        DynamicsConnected=true;
        return true;
    }
    DynamicsConnected=false;
    for (TActorIterator<AActor> It(GetWorld()); It; ++It)
    {
        AActor* Candidate=*It;
        if (Candidate==Drone || Candidate==this) continue;
        if (Candidate->GetFName()==DynamicsActorName || Candidate->GetName()==DynamicsActorName.ToString())
        {
            DynamicsSource=Candidate;
            DynamicsConnected=true;
            if (HideDynamicsVisual) Candidate->SetActorHiddenInGame(true);
            SetVisualAssemblyCollision(false);
            // AirSim scene initialization assigns segmentation stencils globally.
            // Restore WISEYE's thermal classes after that world load.
            ConfigureThermalActors();
            UE_LOG(LogTemp,Display,TEXT("WISEYE: Project AirSim dynamics source bound to %s"),*Candidate->GetName());
            return true;
        }
    }
    return false;
}

void AWiseEyeDemo::SetVisualAssemblyCollision(bool Enabled)
{
    if (!IsValid(Drone)) return;
    TArray<AActor*> AttachedActors;
    AttachedActors.Add(Drone);
    Drone->GetAttachedActors(AttachedActors,false,true);
    for (AActor* Child : AttachedActors)
    {
        if (!IsValid(Child)) continue;
        Child->SetActorEnableCollision(true);
        TArray<UStaticMeshComponent*> Meshes;
        Child->GetComponents(Meshes);
        for (UStaticMeshComponent* Mesh : Meshes)
        {
            if (Enabled) continue;
            if (Mesh->ComponentHasTag(TEXT("RotorBlur"))) continue;
            // Query-only geometry lets the gimbal see the selected model without
            // introducing a second physics body or blocking AirSim's motion.
            Mesh->SetSimulatePhysics(false);
            Mesh->SetCollisionResponseToAllChannels(ECR_Ignore);
            Mesh->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
            Mesh->SetCollisionEnabled(Mesh->IsVisible() ? ECollisionEnabled::QueryOnly : ECollisionEnabled::NoCollision);
        }
    }
}

void AWiseEyeDemo::StepProjectAirSim(float Dt)
{
    if (!TryBindDynamicsSource())
    {
        StepGimbal(Dt,false);
        return;
    }
    // AirSim may finish its global stencil assignment after the source actor spawns.
    // A single sentinel avoids reclassifying the world on every frame.
    const int32 BodyStencil=FMath::Clamp(FMath::RoundToInt(BodyHeat*255.f),1,255);
    if (IsValid(AlternateDroneMesh) && AlternateDroneMesh->CustomDepthStencilValue!=BodyStencil)
        ConfigureThermalActors();
    // Project AirSim is the only pose authority. WISEYE's imported drone and
    // rotor hierarchy has query-only geometry following that body.
    const FQuat VisualRotation=DynamicsSource->GetActorQuat()*DynamicsVisualRotationOffset.Quaternion();
    Drone->SetActorLocationAndRotation(DynamicsSource->GetActorLocation(),VisualRotation,false,nullptr,ETeleportType::TeleportPhysics);
    StepGimbal(Dt,false);
}
