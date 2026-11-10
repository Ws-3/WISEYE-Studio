#include "WiseEyeDemo.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "HAL/PlatformTime.h"
#include "WiseEyeRuntimePaths.h"
#include "Engine/StaticMesh.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

void AWiseEyeDemo::InitializeFixedwingVisual()
{
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/WISEYE/DroneModels/Fixedwing/FixedwingUAV_gray.FixedwingUAV_gray"));
    if (!Mesh || !IsValid(Drone)) return;
    float Length=80.f,Multiplier=1.f;
    FString Text;TSharedPtr<FJsonObject> Config;
    if (FFileHelper::LoadFileToString(Text,*FPaths::Combine(WiseEyePaths::ConfigRoot(),TEXT("WISEYE/device_dimensions.json"))) && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Config)) {
        const TSharedPtr<FJsonObject>* Model=nullptr;
        if (Config->TryGetObjectField(TEXT("fixedwing"),Model)) {
            double Value;
            if ((*Model)->TryGetNumberField(TEXT("length_cm"),Value) && FMath::IsFinite(Value) && Value>=10 && Value<=10000) Length=Value;
            if ((*Model)->TryGetNumberField(TEXT("uniform_scale_multiplier"),Value) && FMath::IsFinite(Value) && Value>=.1 && Value<=10) Multiplier=Value;
        }
    }
    FixedwingMesh=NewObject<UStaticMeshComponent>(Drone.Get(),TEXT("FixedwingVisual"));
    FixedwingMesh->SetStaticMesh(Mesh);FixedwingMesh->SetMobility(EComponentMobility::Movable);
    FixedwingMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    FixedwingMesh->RegisterComponent();
    FixedwingMesh->AttachToComponent(Drone->GetRootComponent(),FAttachmentTransformRules::KeepRelativeTransform);
    const auto Bounds=Mesh->GetBounds();
    const float Scale=Length*Multiplier/FMath::Max(.001f,float(Bounds.BoxExtent.Y*2));
    const FVector Parent=Drone->GetRootComponent()->GetComponentScale().GetAbs().ComponentMax(FVector(.0001f));
    const FRotator Calibration(0,0,0); // Measured mesh nose +Y; shared visual root -90 aligns it with flight +X.
    FixedwingMesh->SetRelativeScale3D(FVector(Scale)/Parent);
    FixedwingMesh->SetRelativeRotation(Calibration);
    FixedwingMesh->SetRelativeLocation(Calibration.RotateVector(-Bounds.Origin*Scale)/Parent);
    FixedwingMesh->SetVisibility(false);
}

TSharedPtr<FJsonObject> AWiseEyeDemo::FixedwingState() const
{
    auto R=MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("active"),FixedwingActive);
    R->SetBoolField(TEXT("paused"),Paused);
    R->SetStringField(TEXT("mode"),AutomaticFlight?TEXT("auto"):TEXT("manual"));
    R->SetStringField(TEXT("model"),TEXT("jsbsim_6dof"));
    R->SetStringField(TEXT("calibration"),TEXT("uncalibrated_reference_wiseye80"));
    R->SetNumberField(TEXT("integration_hz"),120);
    R->SetNumberField(TEXT("speed_command_mps"),FixedwingSpeed);
    if (FixedwingEngine) {
        const auto& S=FixedwingEngine->State;
        R->SetNumberField(TEXT("throttle"),S.throttle);R->SetNumberField(TEXT("alpha_deg"),S.alpha);R->SetNumberField(TEXT("beta_deg"),S.beta);
        R->SetNumberField(TEXT("roll_rate_rad_s"),S.p);R->SetNumberField(TEXT("pitch_rate_rad_s"),S.q);R->SetNumberField(TEXT("yaw_rate_rad_s"),S.r);
        R->SetNumberField(TEXT("load_factor"),S.load_factor);R->SetBoolField(TEXT("stall_warning"),S.alpha>14 || S.speed<7);
    }
    R->SetNumberField(TEXT("speed_mps"),FixedwingActive && !Paused?FixedwingActualSpeed:0);
    R->SetNumberField(TEXT("yaw_deg"),FixedwingYaw);
    R->SetNumberField(TEXT("route_next_index"),FixedwingWaypoint);
    R->SetStringField(TEXT("route_status"),FixedwingRouteStatus);
    R->SetStringField(TEXT("last_error"),FixedwingError);
    if (IsValid(Drone)) {
        const FRotator Physical=(Drone->GetActorQuat()*DynamicsVisualRotationOffset.Quaternion().Inverse()).Rotator();
        R->SetNumberField(TEXT("roll_deg"),Physical.Roll);
        R->SetNumberField(TEXT("pitch_deg"),Physical.Pitch);
    }
    if (IsValid(FixedwingMesh) && FixedwingMesh->GetStaticMesh()) {
        const FVector Size=FixedwingMesh->GetStaticMesh()->GetBounds().BoxExtent*2.f;
        const FTransform Transform=FixedwingMesh->GetComponentTransform();
        R->SetNumberField(TEXT("length_cm"),Transform.TransformVector(FVector(0,Size.Y,0)).Size());
        R->SetNumberField(TEXT("wingspan_cm"),Transform.TransformVector(FVector(Size.X,0,0)).Size());
        const FVector Forward=Transform.TransformVector(FVector(0,1,0)).GetSafeNormal();
        R->SetArrayField(TEXT("model_forward_world"),{MakeShared<FJsonValueNumber>(Forward.X),MakeShared<FJsonValueNumber>(Forward.Y),MakeShared<FJsonValueNumber>(Forward.Z)});
        R->SetNumberField(TEXT("heading_error_deg"),FMath::Abs(FMath::FindDeltaAngleDegrees(FixedwingYaw,Forward.Rotation().Yaw)));
    }
    return R;
}

bool AWiseEyeDemo::ControlFixedwing(const TSharedPtr<FJsonObject>& Args,FString& Error)
{
    if (DroneModel!=TEXT("fixedwing")) { Error=TEXT("Selected device is not fixed-wing");return false; }
    FString Action,Run;
    if (!Args->TryGetStringField(TEXT("action"),Action) || !Args->TryGetStringField(TEXT("run_id"),Run) || Run!=PlaySessionId)
    { Error=TEXT("Fixed-wing action and current run_id required");return false; }
    if (Action==TEXT("state")) return true;
    if (Action==TEXT("start") || Action==TEXT("reset")) {
        if (!FixedwingEngine) FixedwingEngine=MakeUnique<FWiseEyeFixedwingEngine>();
        if (!FixedwingEngine->Reset(InitialYawDegrees,12,Error)) return false;
        FixedwingYaw=InitialYawDegrees;FixedwingSpeed=FixedwingActualSpeed=12;
        FixedwingHoldAltitude=FlightOrigin.Z+3000;FixedwingInput=FVector::ZeroVector;
        // Explicit airborne initialization; this is not a simulated takeoff.
        Drone->SetActorLocationAndRotation(FlightOrigin+FVector(0,0,3000),FRotator(3,FixedwingYaw,0).Quaternion()*DynamicsVisualRotationOffset.Quaternion(),false,nullptr,ETeleportType::TeleportPhysics);
        FixedwingActive=true;Paused=false;AutomaticFlight=true;
        FixedwingRoute.Reset();FixedwingRouteStatus=TEXT("idle");FixedwingError.Empty();
    } else if (Action==TEXT("stop")) {
        FixedwingActive=false;Paused=true;FixedwingInput=FVector::ZeroVector;
        FixedwingRoute.Reset();FixedwingRouteStatus=TEXT("stopped");
    } else if (Action==TEXT("pause") || Action==TEXT("resume")) {
        if (Action==TEXT("resume") && !FixedwingActive) {Error=TEXT("Cruise is stopped. Reset to the flight origin before resuming after a collision.");return false;}
        Paused=Action==TEXT("pause");FixedwingInput=FVector::ZeroVector;
    } else if (Action==TEXT("loiter")) {
        if (!FixedwingActive) {Error=TEXT("Start airborne cruise first");return false;}
        AutomaticFlight=true;Paused=false;FixedwingRoute.Reset();FixedwingRouteStatus=TEXT("stopped");
    } else if (Action==TEXT("mode")) {
        FString Mode;
        if (!Args->TryGetStringField(TEXT("mode"),Mode) || (Mode!=TEXT("auto") && Mode!=TEXT("manual"))) {Error=TEXT("Invalid fixed-wing mode");return false;}
        AutomaticFlight=Mode==TEXT("auto");FixedwingInput=FVector::ZeroVector;
        if (FixedwingActive) Paused=false;
        FixedwingRouteStatus=FixedwingRoute.Num()?(AutomaticFlight?TEXT("running"):TEXT("stopped")):TEXT("idle");
    } else if (Action==TEXT("input")) {
        double Forward,Right,Up,Yaw;
        if (!Args->TryGetNumberField(TEXT("forward"),Forward) || !Args->TryGetNumberField(TEXT("right"),Right) || !Args->TryGetNumberField(TEXT("up"),Up) || !Args->TryGetNumberField(TEXT("yaw"),Yaw)) {Error=TEXT("Four manual axes required");return false;}
        for (double V:{Forward,Right,Up,Yaw}) if (!FMath::IsFinite(V) || FMath::Abs(V)>1) {Error=TEXT("Manual axes must be finite in [-1,1]");return false;}
        if (Forward==0 && Right==0 && Up==0 && Yaw==0) {FixedwingInput=FVector::ZeroVector;return true;}
        if (AutomaticFlight || !FixedwingActive || Paused) {Error=TEXT("Manual cruise must be active");return false;}
        FixedwingInput=FVector(Forward,FMath::Clamp(Right+Yaw,-1.,1.),Up);FixedwingInputAt=FPlatformTime::Seconds();
    } else if (Action==TEXT("route")) {
        const TArray<TSharedPtr<FJsonValue>>* Points=nullptr;double Speed;bool Repeat;
        if (!FixedwingActive) {Error=TEXT("Start airborne cruise before executing a route");return false;}
        if (!Args->TryGetArrayField(TEXT("waypoints"),Points) || Points->Num()<2 || Points->Num()>128 || !Args->TryGetNumberField(TEXT("speed_mps"),Speed) || !FMath::IsFinite(Speed) || Speed<5 || Speed>15 || !Args->TryGetBoolField(TEXT("repeat"),Repeat)) {Error=TEXT("Fixed-wing route requires 2-128 waypoints and 5-15 m/s");return false;}
        TArray<FVector> Validated;
        for (const auto& Point:*Points) {
            const TArray<TSharedPtr<FJsonValue>>* V=nullptr;
            if (!Point->TryGetArray(V) || V->Num()!=3) {Error=TEXT("Invalid route point");return false;}
            FVector P;
            for (int I=0;I<3;++I) { double N;if (!(*V)[I]->TryGetNumber(N) || !FMath::IsFinite(N) || FMath::Abs(N)>100000) {Error=TEXT("Invalid waypoint coordinate");return false;} P[I]=N*100.; }
            Validated.Add(P);
        }
        FixedwingRoute=MoveTemp(Validated);FixedwingWaypoint=0;FixedwingRepeat=Repeat;
        FixedwingSpeed=Speed;FixedwingRouteStatus=TEXT("running");AutomaticFlight=true;Paused=false;
    } else {Error=TEXT("Unknown fixed-wing action");return false;}
    return true;
}

void AWiseEyeDemo::StepFixedwing(float Dt)
{
    DynamicsConnected=true;
    if (!FixedwingActive || Paused) {StepGimbal(Dt,false);return;}
    const float Step=FMath::Min(Dt,.1f); // Do not jump through buildings after a stall.
    const FVector Old=Drone->GetActorLocation();
    float Turn=0,Climb=FMath::Clamp((FixedwingHoldAltitude-Old.Z)*.8f,-200.f,200.f);
    const bool FreshManual=!AutomaticFlight && FPlatformTime::Seconds()-FixedwingInputAt<.4;
    if (FreshManual) FixedwingSpeed=FMath::Clamp(FixedwingSpeed+float(FixedwingInput.X)*2.f*Step,5.f,15.f);
    const float Speed=FMath::Max(5.f,FixedwingActualSpeed);
    // Guidance commands bank and flight-path angle; JSBSim integrates all six DOFs.
    const float MaxTurn=FMath::Min(25.f,FMath::RadiansToDegrees(9.81f*FMath::Tan(FMath::DegreesToRadians(30.f))/Speed));
    if (AutomaticFlight) {
        if (FixedwingRoute.Num()) {
            const FVector Delta=FixedwingRoute[FixedwingWaypoint]-Old;
            if (Delta.Size2D()<FMath::Max(600.f,Speed*100.f) && FMath::Abs(Delta.Z)<500.f) {
                ++FixedwingWaypoint;
                if (FixedwingWaypoint>=FixedwingRoute.Num()) {
                    FixedwingWaypoint=0;
                    if (!FixedwingRepeat) {FixedwingRoute.Reset();FixedwingRouteStatus=TEXT("completed");}
                }
            }
            if (FixedwingRoute.Num()) {
                const FVector Aim=FixedwingRoute[FixedwingWaypoint]-Old;
                Turn=FMath::Clamp(FMath::FindDeltaAngleDegrees(FixedwingYaw,Aim.Rotation().Yaw)*.7f,-MaxTurn,MaxTurn);
                Climb=FMath::Clamp(float(Aim.Z*.005),-200.f,200.f);
            }
        }
        if (!FixedwingRoute.Num()) Turn=FMath::Min(MaxTurn,FMath::RadiansToDegrees(Speed/80.f));
    } else if (FreshManual) {
        Turn=FixedwingInput.Y*MaxTurn;
        if (FMath::Abs(FixedwingInput.Z)>.01) {Climb=FixedwingInput.Z*200.f;FixedwingHoldAltitude=Old.Z;}
    }
    const float BankCommand=FMath::Clamp(FMath::RadiansToDegrees(FMath::Atan(Speed*FMath::DegreesToRadians(Turn)/9.80665f)),-30.f,30.f);
    const float GammaCommand=FMath::RadiansToDegrees(FMath::Atan2(Climb,Speed*100.f));
    if (!FixedwingEngine || !FixedwingEngine->Step(Step,FixedwingSpeed,BankCommand,GammaCommand,FixedwingError)) {
        FixedwingActive=false;Paused=true;FixedwingRouteStatus=TEXT("stopped");StepGimbal(Dt,false);return;
    }
    const auto& Physical=FixedwingEngine->State;
    FixedwingYaw=FMath::UnwindDegrees(Physical.yaw);FixedwingActualSpeed=Physical.speed;
    const FVector Next=Old+FVector(Physical.dx,Physical.dy,Physical.dz)*100.;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WiseEyeFixedwing),true);
    TArray<AActor*> Own={Drone.Get()};Drone->GetAttachedActors(Own,false,true);
    for (AActor* Actor:Own) Query.AddIgnoredActor(Actor);
    FHitResult Hit;
    FVector Extent(40,31.1,8),Center=Old;FQuat BodyRotation=Drone->GetActorQuat();
    if (FixedwingMesh && FixedwingMesh->GetStaticMesh()) {
        const auto Bounds=FixedwingMesh->GetStaticMesh()->GetBounds();
        Extent=(Bounds.BoxExtent*FixedwingMesh->GetComponentScale().GetAbs()).ComponentMax(FVector(1));
        Center=FixedwingMesh->GetComponentTransform().TransformPosition(Bounds.Origin);
        BodyRotation=FixedwingMesh->GetComponentQuat();
    }
    if (GetWorld()->SweepSingleByChannel(Hit,Center,Center+(Next-Old),BodyRotation,ECC_Visibility,FCollisionShape::MakeBox(Extent),Query)) {
        FixedwingActualSpeed=0;FixedwingInput=FVector::ZeroVector;
        FixedwingActive=false;Paused=true;FixedwingError=TEXT("Cruise stopped at an obstacle; reset or reposition before restarting");
        FixedwingRouteStatus=TEXT("stopped");StepGimbal(Dt,false);return;
    }
    const FQuat Rotation=FRotator(Physical.pitch,FixedwingYaw,Physical.roll).Quaternion()*DynamicsVisualRotationOffset.Quaternion();
    Drone->SetActorLocationAndRotation(Next,Rotation,false,nullptr,ETeleportType::TeleportPhysics);
    StepGimbal(Dt,false);
}
