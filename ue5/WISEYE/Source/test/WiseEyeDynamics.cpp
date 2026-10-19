#include "WiseEyeDemo.h"

#include "EngineUtils.h"
#include "GameFramework/Actor.h"

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
            UE_LOG(LogTemp,Display,TEXT("WISEYE: Project AirSim dynamics source bound to %s"),*Candidate->GetName());
            return true;
        }
    }
    return false;
}

void AWiseEyeDemo::SetVisualAssemblyCollision(bool Enabled)
{
    if (!IsValid(Drone)) return;
    Drone->SetActorEnableCollision(Enabled);
    TArray<AActor*> AttachedActors;
    Drone->GetAttachedActors(AttachedActors,true,true);
    for (AActor* Child : AttachedActors)
        if (IsValid(Child)) Child->SetActorEnableCollision(Enabled);
}

void AWiseEyeDemo::StepProjectAirSim(float Dt)
{
    if (!TryBindDynamicsSource())
    {
        StepGimbal(Dt,false);
        return;
    }
    // Project AirSim is the only pose authority. WISEYE's imported drone and
    // rotor hierarchy is a collision-free visual assembly following that body.
    const FQuat VisualRotation=DynamicsSource->GetActorQuat()*DynamicsVisualRotationOffset.Quaternion();
    Drone->SetActorLocationAndRotation(DynamicsSource->GetActorLocation(),VisualRotation,false,nullptr,ETeleportType::TeleportPhysics);
    StepGimbal(Dt,false);
}
