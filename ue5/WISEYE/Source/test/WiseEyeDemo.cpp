#include "WiseEyeDemo.h"
#include "WiseEyeRuntimePaths.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/InputComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "UnrealClient.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshSocket.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "UObject/ConstructorHelpers.h"
#include "WiseEyeBridge.h"
#include "WiseEyeStreaming.h"
#if WITH_EDITOR
#include "Editor.h"
#include "Editor/EditorEngine.h"
#endif

AWiseEyeDemo::~AWiseEyeDemo() { delete Bridge; delete StreamManager; }
void AWiseEyeDemo::EndPlay(const EEndPlayReason::Type Reason)
{
    delete Bridge;
    Bridge = nullptr;
    delete StreamManager;
    StreamManager = nullptr;
    BridgeReady = false;
    Super::EndPlay(Reason);
}

AWiseEyeRotor::AWiseEyeRotor()
{
    Pivot = CreateDefaultSubobject<USceneComponent>(TEXT("RotorPivot"));
    SetRootComponent(Pivot);
    Pivot->SetMobility(EComponentMobility::Movable);
}

AWiseEyeDemo::AWiseEyeDemo()
{
    PrimaryActorTick.bCanEverTick = true;
    Base = CreateDefaultSubobject<USceneComponent>(TEXT("Base"));
    SetRootComponent(Base);
    YawPivot = CreateDefaultSubobject<USceneComponent>(TEXT("YawPivot"));
    YawPivot->SetupAttachment(Base);
    PitchPivot = CreateDefaultSubobject<USceneComponent>(TEXT("PitchPivot"));
    PitchPivot->SetupAttachment(YawPivot);
    Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("EO_Camera"));
    Camera->SetupAttachment(PitchPivot);
    Camera->bConstrainAspectRatio = true;
    Camera->AspectRatio = 16.f/9.f;
    Capture = CreateDefaultSubobject<USceneCaptureComponent2D>(TEXT("EO_Capture"));
    Capture->SetupAttachment(Camera);
    Capture->CaptureSource = ESceneCaptureSource::SCS_FinalColorLDR;
    Capture->bCaptureEveryFrame = true;
    Capture->bCaptureOnMovement = false;
    Capture->bAlwaysPersistRenderingState = true;
    InfraredCapture = CreateDefaultSubobject<USceneCaptureComponent2D>(TEXT("IR_Capture"));
    InfraredCapture->SetupAttachment(Camera);
    InfraredCapture->CaptureSource = ESceneCaptureSource::SCS_FinalColorLDR;
    InfraredCapture->bCaptureEveryFrame = true;
    InfraredCapture->bCaptureOnMovement = false;
    InfraredCapture->bAlwaysPersistRenderingState = true;
    LidarMount = CreateDefaultSubobject<USceneComponent>(TEXT("GimbalLidarMount"));
    LidarMount->SetupAttachment(Camera);
    LidarMount->SetRelativeLocation(FVector(8,3,0));
    LidarBody = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("GimbalLidarBody"));
    LidarBody->SetupAttachment(LidarMount);
    LidarBody->SetRelativeLocation(FVector(-4,0,0));
    LidarBody->SetRelativeRotation(FRotator(0,90,0));
    LidarBody->SetRelativeScale3D(FVector(.025f,.025f,.06f));
    LidarBody->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> LidarMesh(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    if (LidarMesh.Succeeded()) LidarBody->SetStaticMesh(LidarMesh.Object);
    AutoReceiveInput = EAutoReceiveInput::Player0;
}

void AWiseEyeDemo::BeginPlay()
{
    Super::BeginPlay();
    if (FleetChild) { InitializeFleetChild(); return; }
#if WITH_EDITOR
    // The desktop console is normally foreground while UE supplies live sensor
    // frames. Keep editor PIE ticking at full rate in that configuration.
    static bool BackgroundThrottleDisabled = false;
    if (GEditor && !BackgroundThrottleDisabled)
    {
        GEditor->ShouldDisableCPUThrottlingDelegates.Add(
            UEditorEngine::FShouldDisableCPUThrottling::CreateLambda([] { return true; }));
        BackgroundThrottleDisabled = true;
    }
#endif
    FString SceneError;
    if (!ApplySceneConfiguration(SceneError))
        UE_LOG(LogTemp, Warning, TEXT("WISEYE scene configuration: %s"), *SceneError);
    if (!IsValid(Drone))
    {
        UE_LOG(LogTemp, Error, TEXT("WISEYE: assign Drone before playing"));
        SetActorTickEnabled(false);
        return;
    }
    DroneInitialRotation = Drone->GetActorRotation();
    InitialFlightOrigin = FlightOrigin;
    RotorInitialRotations.Reset();
    for (AActor* Rotor : Rotors)
        RotorInitialRotations.Add(IsValid(Rotor) ? Rotor->GetRootComponent()->GetRelativeRotation().Quaternion() : FQuat::Identity);
    InitializeDroneModels();
    DroneView = GetWorld()->SpawnActor<ACameraActor>();
    if (DroneView) DroneView->GetCameraComponent()->SetFieldOfView(65.f);
    InitializeSensors();
    StreamManager = new FWiseEyeStreamManager();
    OutputDirectory = FPaths::Combine(WiseEyePaths::SavedRoot(), TEXT("WISEYE"), FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S")));
    IFileManager::Get().MakeDirectory(*OutputDirectory, true);
    FFileHelper::SaveStringToFile(TEXT("time_s,drone_x_cm,drone_y_cm,drone_z_cm,yaw_deg,pitch_deg,pointing_error_deg,fov_deg,auto_flight,tracking,rotors,rotor_phase_deg\n"), *FPaths::Combine(OutputDirectory,TEXT("telemetry.csv")));

// ----- Real‑time image processing setup -----
// Create a processed render target with the same resolution as the capture component (1280×720)
ProcessedRenderTarget = NewObject<UTextureRenderTarget2D>(this, UTextureRenderTarget2D::StaticClass(), NAME_None, RF_NoFlags);
if (ProcessedRenderTarget)
{
    int32 W = Capture->TextureTarget ? Capture->TextureTarget->SizeX : 1280;
    int32 H = Capture->TextureTarget ? Capture->TextureTarget->SizeY : 720;
    ProcessedRenderTarget->InitAutoFormat(W, H);
    ProcessedRenderTarget->UpdateResource();
}

// Create a dynamic material instance from the assigned ThermalMaterial (if any)
if (ThermalMaterial)
{
    MatInst = UMaterialInstanceDynamic::Create(ThermalMaterial, this);
    if (MatInst)
    {
        // Try to set the texture parameter named "ProcessedTex"; if the base material does not have it, it will be silently ignored.
        MatInst->SetTextureParameterValue(TEXT("ProcessedTex"), ProcessedRenderTarget);
    }
}
else
{
    UE_LOG(LogTemp, Warning, TEXT("ThermalMaterial not assigned; MatInst not created."));
}

// -----------------------------------------------------------------------------
    PlaySessionId = FGuid::NewGuid().ToString();
    EnsurePlayerInput();
    if (FlightBackend==EWiseEyeFlightBackend::Kinematic) StepSimulation(0, true);
    else
    {
        SetVisualAssemblyCollision(false);
        TryBindDynamicsSource();
        StepGimbal(0,true);
    }
    ScanLidar();
    UpdateDroneView();
    FString FleetError;
    if (!InitializeFleet(FleetError)) { UE_LOG(LogTemp,Error,TEXT("WISEYE fleet: %s"),*FleetError); SetActorTickEnabled(false); return; }
    Bridge = new FWiseEyeBridge(*this);
    BridgeReady = Bridge->Start(ControlPort,BridgeError);
    if (!BridgeReady) UE_LOG(LogTemp,Error,TEXT("WISEYE control bridge: %s"),*BridgeError);
    UE_LOG(LogTemp, Display, TEXT("WISEYE: simulation started, output %s"), *OutputDirectory);
}

void AWiseEyeDemo::Tick(float Dt)
{
    Super::Tick(Dt);
    ++TickSequence;
    if (!FleetChild) { UpdateRuntimeStatus(); UpdateRainVolumes(); }
    if (FleetChild) { PerformanceProfile=FleetRoot->PerformanceProfile; VisibleCaptureHz=FleetRoot->VisibleCaptureHz; InfraredCaptureHz=FleetRoot->InfraredCaptureHz; ObserverCaptureHz=FleetRoot->ObserverCaptureHz; }
    else if (TickSequence==1) SetPerformanceProfile(SceneId==TEXT("city")?TEXT("economy"):PerformanceProfile);
    if (!FleetChild) { EnsurePlayerInput(); StepObserver(Dt); PollLocalFlightInput(); }
    else {
        ControlMode=FleetRoot->ControlMode;ObserverMode=FleetRoot->ObserverMode;
        StepObserver(Dt);
    }
    if (!IsValid(Drone)) return;
    if (!FleetChild) UpdateObserverCapture();
    const double CaptureNow=FPlatformTime::Seconds();
    auto CaptureDue=[&](USceneCaptureComponent2D* Component,bool Enabled,double& Next,float Hz) {
        if (!Enabled || CaptureNow<Next || !Component) return false;
        Component->bCaptureEveryFrame=false; Component->bCaptureOnMovement=false;
        Component->bUseRayTracingIfEnabled=PerformanceProfile==TEXT("quality");
        auto& PP=Component->PostProcessSettings;
        PP.bOverride_ReflectionMethod=PerformanceProfile!=TEXT("quality");
        PP.ReflectionMethod=EReflectionMethod::ScreenSpace;
        PP.bOverride_DynamicGlobalIlluminationMethod=PerformanceProfile==TEXT("economy");
        PP.DynamicGlobalIlluminationMethod=EDynamicGlobalIlluminationMethod::None;
        if (Component==InfraredCapture && ThermalInstance)
            ThermalInstance->SetScalarParameterValue(TEXT("NoiseFrame"),float((++ThermalFrameIndex)%4096));
        Component->CaptureScene();
        Next=FMath::Max(Next+1.0/Hz,CaptureNow+.001);
        return true;
    };
    const bool NewVisible=CaptureDue(Capture,VisibleEnabled,NextVisibleCapture,VisibleCaptureHz);
    const bool NewInfrared=CaptureDue(InfraredCapture,InfraredEnabled,NextInfraredCapture,InfraredCaptureHz);
    if (StreamManager) StreamManager->Tick(NewVisible?RenderTarget.Get():nullptr,NewInfrared?InfraredTarget.Get():nullptr,SimulationTime,ObserverCaptured?ObserverTarget.Get():nullptr);
    if (Bridge && !FleetChild) Bridge->Tick();
    if (FlightBackend==EWiseEyeFlightBackend::ProjectAirSim)
    {
        // AirSim pause is physical hover, not a stopped physics clock. Keep
        // following its pose during hover, takeoff and landing as well.
        if (!Paused) SimulationTime += Dt;
        if (OwnsDrone) { StepProjectAirSim(Dt); StepRotors(Dt); }
        else StepGimbal(Dt,false);
    }
    else if (!Paused)
    {
        if (AutomaticFlight)
        {
            SimulationTime += Dt;
            StepSimulation(Dt,false);
        }
        else
        {
            StepManualFlight(Dt);
            StepGimbal(Dt,false);
        }
        StepRotors(Dt);
    }
    LidarClock += Dt;
    if (LidarEnabled && LidarClock >= 1.f/FMath::Max(.05f,LidarScanRateHz))
    {
        LidarClock = 0;
        ScanLidar();
    }
    UpdateDroneView();

    // Continuous camera publishing performs demand-driven readback. Avoid a second
    // full-resolution GPU readback every Tick, which would halve streaming headroom.
    TelemetryClock += Dt;
    if (TelemetryClock >= 1)
    {
        TelemetryClock = 0;
        WriteTelemetry();
    }
}

bool AWiseEyeDemo::GetStreamFrame(bool bInfrared, TArray64<uint8>& Jpeg, int32& Width, int32& Height,
                                  int64& StreamFrameNumber, double& StreamSimulationTime) const
{
    return StreamManager && StreamManager->GetFrame(bInfrared,Jpeg,Width,Height,StreamFrameNumber,StreamSimulationTime);
}

void AWiseEyeDemo::GetStreamStatistics(bool bInfrared, int64& Sequence, int64& Completed, double& CaptureTime) const
{
    Sequence=Completed=0; CaptureTime=0;
    if (StreamManager) StreamManager->GetStatistics(bInfrared,Sequence,Completed,CaptureTime);
}

void AWiseEyeDemo::InitializeDroneModels()
{
    MavicVisualComponents.Reset();
    auto AddActorVisuals=[this](AActor* Actor)
    {
        if (!IsValid(Actor)) return;
        TArray<UPrimitiveComponent*> Components;
        Actor->GetComponents<UPrimitiveComponent>(Components);
        for (UPrimitiveComponent* Component : Components)
            if (IsValid(Component)) MavicVisualComponents.AddUnique(Component);
    };
    AddActorVisuals(Drone);
    TArray<AActor*> AttachedDroneActors;
    Drone->GetAttachedActors(AttachedDroneActors,true,true);
    for (AActor* Actor : AttachedDroneActors) AddActorVisuals(Actor);
    for (AActor* Rotor : Rotors) AddActorVisuals(Rotor);

    UStaticMesh* DiscMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    UMaterialInterface* BlurMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WISEYE/DroneModels/Avata/Animated/M_RotorBlur.M_RotorBlur"));
    auto MakeBlur=[DiscMesh,BlurMaterial](AActor* BlurOwner,USceneComponent* Parent,const FVector& Center,float Radius)
    {
        if (!DiscMesh || !BlurMaterial) return static_cast<UStaticMeshComponent*>(nullptr);
        UStaticMeshComponent* Blur=NewObject<UStaticMeshComponent>(BlurOwner);
        Blur->ComponentTags.Add(TEXT("RotorBlur"));
        Blur->SetStaticMesh(DiscMesh);
        Blur->SetMaterial(0,BlurMaterial);
        Blur->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Blur->SetCastShadow(false);
        Blur->SetMobility(EComponentMobility::Movable);
        Blur->RegisterComponent();
        Blur->AttachToComponent(Parent,FAttachmentTransformRules::KeepRelativeTransform);
        Blur->SetRelativeLocation(Center);
        Blur->SetRelativeScale3D(FVector(Radius/50.f,Radius/50.f,.0001f));
        Blur->SetVisibility(false);
        return Blur;
    };
    MavicRotorBlurs.Reset();
    const TSet<FString> BladeMeshNames={TEXT("Mesh_ncl_92"),TEXT("Mesh_ncl_94"),TEXT("Mesh_ncl_110"),TEXT("Mesh_ncl_111"),TEXT("Mesh_ncl_119"),TEXT("Mesh_ncl_120"),TEXT("Mesh_ncl_99"),TEXT("Mesh_ncl_100")};
    for (AActor* Rotor : Rotors)
    {
        if (!IsValid(Rotor)) continue;
        // The persisted rotor pivot owns no geometry: hub/blades are child actors.
        FBox Bounds(ForceInit);
        float RadiusSquared=0.f;
        TArray<AActor*> Parts;
        Parts.Add(Rotor);
        Rotor->GetAttachedActors(Parts,false,true);
        for (AActor* Part : Parts)
        {
            TArray<UStaticMeshComponent*> Meshes;
            Part->GetComponents(Meshes);
            for (UStaticMeshComponent* Mesh : Meshes)
                if (Mesh->GetStaticMesh() && BladeMeshNames.Contains(Mesh->GetStaticMesh()->GetName()))
                {
                    const FBox Box=Mesh->GetStaticMesh()->GetBoundingBox();
                    const FTransform ToRotor=Mesh->GetComponentTransform().GetRelativeTransform(Rotor->GetActorTransform());
                    Bounds+=Box.TransformBy(ToRotor);
                    for (int32 Corner=0; Corner<8; ++Corner)
                    {
                        const FVector P=ToRotor.TransformPosition(Box.GetCenter()+Box.GetExtent()*
                            FVector((Corner&1)?1:-1,(Corner&2)?1:-1,(Corner&4)?1:-1));
                        RadiusSquared=FMath::Max(RadiusSquared,float(P.X*P.X+P.Y*P.Y));
                    }
                }
        }
        if (!Bounds.IsValid)
        {
            MavicRotorBlurs.Add(nullptr);
            continue;
        }
        MavicRotorBlurs.Add(MakeBlur(Rotor,Rotor->GetRootComponent(),FVector(0,0,Bounds.GetCenter().Z),FMath::Sqrt(RadiusSquared)));
    }

    UStaticMesh* ReferenceMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/WISEYE/DroneModels/Avata/Avata_black.Avata_black"));
    UStaticMesh* AvataMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/WISEYE/DroneModels/Avata/Animated/AvataBody.AvataBody"));
    TArray<UStaticMesh*> RotorMeshes;
    for (int32 I=0; I<4; ++I)
    {
        const FString Path=FString::Printf(TEXT("/Game/WISEYE/DroneModels/Avata/Animated/AvataRotor%d.AvataRotor%d"),I,I);
        UStaticMesh* Mesh=LoadObject<UStaticMesh>(nullptr,*Path);
        if (!Mesh || !AvataMesh || !AvataMesh->FindSocket(FName(*FString::Printf(TEXT("Rotor%d"),I))))
        {
            UE_LOG(LogTemp,Error,TEXT("WISEYE: missing animated Avata assets; rebuild with build_avata_rotors.py"));
            return;
        }
        RotorMeshes.Add(Mesh);
    }
    if (AvataMesh && ReferenceMesh && IsValid(Drone) && Drone->GetRootComponent())
    {
        AlternateDroneMesh=NewObject<UStaticMeshComponent>(Drone.Get(),TEXT("AvataVisual"));
        AlternateDroneMesh->SetStaticMesh(AvataMesh);
        AlternateDroneMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        AlternateDroneMesh->SetMobility(EComponentMobility::Movable);
        AlternateDroneMesh->RegisterComponent();
        AlternateDroneMesh->AttachToComponent(Drone->GetRootComponent(),FAttachmentTransformRules::KeepRelativeTransform);
        // Keep calibration based on the complete original model, including blades.
        const FBoxSphereBounds Bounds=ReferenceMesh->GetBounds();
        // DJI Avata (first generation): 180 x 180 x 80 mm, guards included.
        const FVector Scale=FVector(18.f,18.f,8.f)/(Bounds.BoxExtent*2.f).ComponentMax(FVector(.001f));
        const FVector ParentScale=Drone->GetRootComponent()->GetComponentScale().GetAbs().ComponentMax(FVector(.0001f));
        const FVector RelativeScale=Scale/ParentScale;
        AlternateDroneMesh->SetRelativeScale3D(RelativeScale);
        AlternateDroneMesh->SetRelativeLocation((-Bounds.Origin*Scale)/ParentScale);
        AlternateDroneMesh->SetRelativeRotation(FRotator::ZeroRotator);
        AvataRotors.Reset();
        AvataRotorBlurs.Reset();
        FVector MotorCenter=FVector::ZeroVector;
        for (int32 I=0;I<4;++I) MotorCenter+=AvataMesh->FindSocket(FName(*FString::Printf(TEXT("Rotor%d"),I)))->RelativeLocation*.25;
        const FRotator VehicleYaw(0,Drone->GetActorRotation().Yaw-ModelHeadingOffset,0);
        const FVector VehicleForward=VehicleYaw.Vector(),VehicleRight=FRotationMatrix(VehicleYaw).GetUnitAxis(EAxis::Y);

        for (int32 I=0; I<4; ++I)
        {
            UStaticMeshComponent* Rotor=NewObject<UStaticMeshComponent>(Drone.Get(),FName(*FString::Printf(TEXT("AvataRotor%d"),I)));
            Rotor->SetStaticMesh(RotorMeshes[I]);
            Rotor->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Rotor->SetMobility(EComponentMobility::Movable);
            Rotor->RegisterComponent();
            Rotor->AttachToComponent(AlternateDroneMesh,FAttachmentTransformRules::KeepRelativeTransform);
            // Vertices are centered on the original motor shaft, stored by the asset builder.
            Rotor->SetRelativeLocation(AvataMesh->FindSocket(FName(*FString::Printf(TEXT("Rotor%d"),I)))->RelativeLocation);
            const FVector MotorOffset=AlternateDroneMesh->GetComponentTransform().TransformVector(Rotor->GetRelativeLocation()-MotorCenter);
            AvataMotorIndices[I]=(FVector::DotProduct(MotorOffset,VehicleForward)>=0?0:2)+(FVector::DotProduct(MotorOffset,VehicleRight)>=0?1:0);
            AvataRotors.Add(Rotor);
            AvataRotorBlurs.Add(MakeBlur(Drone.Get(),AlternateDroneMesh,Rotor->GetRelativeLocation()+FVector(0,0,1.5f),17.5f));
        }
        AlternateDroneMesh->SetVisibility(false,true);
    }
}

bool AWiseEyeDemo::SetDroneModel(const FString& ModelId,FString& Error)
{
    const FString Normalized=ModelId.ToLower();
    if (Normalized!=TEXT("mavic3") && Normalized!=TEXT("avata"))
    {
        Error=TEXT("model must be mavic3 or avata");
        return false;
    }
    if (Normalized==TEXT("avata") && !IsValid(AlternateDroneMesh))
    {
        Error=TEXT("Avata asset is not installed; run the drone model import step");
        return false;
    }
    const bool ShowMavic=Normalized==TEXT("mavic3");
    for (UPrimitiveComponent* Component : MavicVisualComponents)
        if (IsValid(Component)) Component->SetVisibility(ShowMavic,true);
    if (IsValid(AlternateDroneMesh)) AlternateDroneMesh->SetVisibility(!ShowMavic,true);
    for (UStaticMeshComponent* Blur : MavicRotorBlurs)
        if (IsValid(Blur)) Blur->SetVisibility(false);
    DroneModel=Normalized;
    if (FlightBackend==EWiseEyeFlightBackend::ProjectAirSim) SetVisualAssemblyCollision(false);
    ConfigureThermalActors();
    return true;
}

FVector AWiseEyeDemo::FlightOffset(float Time) const
{
    const float T = Time*2.f*PI/FMath::Max(1.f,Period);
    return FVector(FlightRadius*FMath::Sin(T),.65f*FlightRadius*FMath::Sin(2.f*T),VerticalAmplitude*FMath::Sin(T));
}

void AWiseEyeDemo::StepSimulation(float Dt, bool Snap)
{
    // Repeatable figure-eight; analytic velocity determines heading.
    const float W = 2*PI/FMath::Max(1.f,Period);
    const float T = SimulationTime*W;
    const FVector P = FlightOrigin + FlightOffset(SimulationTime);
    const FVector V(FlightRadius*W*FMath::Cos(T),1.3f*FlightRadius*W*FMath::Cos(2*T),VerticalAmplitude*W*FMath::Cos(T));
    // Imported model heading offset remains an asset calibration, not a flight-dynamics model.
    FRotator Heading = DroneInitialRotation;
    Heading.Yaw = V.Rotation().Yaw + ModelHeadingOffset;
    Heading.Roll = 4*FMath::Sin(T);
    Drone->SetActorLocationAndRotation(P, Heading, false, nullptr, ETeleportType::TeleportPhysics);
    StepGimbal(Dt,Snap);
}

void AWiseEyeDemo::StepGimbal(float Dt, bool Snap)
{
    const FVector Target = (TrackingDrone?TrackingDrone.Get():Drone.Get())->GetActorTransform().TransformPosition(TargetOffset);
    // Solve from the displaced optical center, not the importer root or mesh bounds.
    const FVector LocalDirection = Base->GetComponentTransform().InverseTransformVectorNoScale(Target-Camera->GetComponentLocation());
    const FRotator Desired = LocalDirection.Rotation();
    const float OldYaw = YawPivot->GetRelativeRotation().Yaw;
    const float OldPitch = PitchPivot->GetRelativeRotation().Pitch;
    const float Yaw = Snap ? Desired.Yaw : FMath::FixedTurn(OldYaw,Desired.Yaw,FMath::Max(0.f,YawRate)*Dt);
    const float DesiredPitch = FMath::Clamp(Desired.Pitch,MinPitch,MaxPitch);
    const float Pitch = Snap ? DesiredPitch : FMath::FInterpConstantTo(OldPitch,DesiredPitch,Dt,FMath::Max(0.f,PitchRate));
    if (TrackingEnabled)
    {
        YawPivot->SetRelativeRotation(FRotator(0,Yaw,0));
        PitchPivot->SetRelativeRotation(FRotator(Pitch,0,0));
    }
    const FVector Sight = (Target-Camera->GetComponentLocation()).GetSafeNormal();
    PointingError = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(Sight,Camera->GetForwardVector()),-1.0,1.0)));
}

void AWiseEyeDemo::SetManualInput(float Forward, float Right, float Up, float Yaw)
{
    ManualInput = FVector(FMath::Clamp(Forward,-1.f,1.f),FMath::Clamp(Right,-1.f,1.f),FMath::Clamp(Up,-1.f,1.f));
    ManualYawInput = FMath::Clamp(Yaw,-1.f,1.f);
}

void AWiseEyeDemo::StepManualFlight(float Dt)
{
    FVector Input = ManualInput;
    float Turn = ManualYawInput;
    float Speed = ManualSpeed;
    if (APlayerController* PC = GetWorld()->GetFirstPlayerController(); PC && ControlMode==TEXT("drone") && GetWorld()->GetGameViewport() && GetWorld()->GetGameViewport()->Viewport && GetWorld()->GetGameViewport()->Viewport->HasFocus())
    {
        Input.X += float(PC->IsInputKeyDown(EKeys::W))-float(PC->IsInputKeyDown(EKeys::S));
        Input.Y += float(PC->IsInputKeyDown(EKeys::D))-float(PC->IsInputKeyDown(EKeys::A));
        Input.Z += float(PC->IsInputKeyDown(EKeys::R))-float(PC->IsInputKeyDown(EKeys::F));
        Turn += float(PC->IsInputKeyDown(EKeys::E))-float(PC->IsInputKeyDown(EKeys::Q));
        if (PC->IsInputKeyDown(EKeys::LeftShift)) Speed *= 2.f;
    }
    Input = Input.GetClampedToMaxSize(1.f);
    FRotator Heading = Drone->GetActorRotation();
    Heading.Yaw += FMath::Clamp(Turn,-1.f,1.f)*ManualYawRate*Dt;
    Heading.Pitch = DroneInitialRotation.Pitch;
    Heading.Roll = 0;
    const FRotator TravelHeading(0,Heading.Yaw-ModelHeadingOffset,0);
    FVector Position = Drone->GetActorLocation() + (TravelHeading.Vector()*Input.X + FRotationMatrix(TravelHeading).GetUnitAxis(EAxis::Y)*Input.Y + FVector::UpVector*Input.Z)*Speed*Dt;
    Position.Z = FMath::Clamp(Position.Z,MinimumAltitude,MaximumAltitude);
    Drone->SetActorLocationAndRotation(Position,Heading,false,nullptr,ETeleportType::TeleportPhysics);
}

void AWiseEyeDemo::StepRotors(float Dt)
{
    if (FlightBackend==EWiseEyeFlightBackend::ProjectAirSim) {
        const bool Fresh=RotorTelemetryValid && FPlatformTime::Seconds()-RotorTelemetryTime<1.5;
        RotorRPM=0;
        for (int32 I=0;I<4;++I) { if (!Fresh) MotorRPMs[I]=0; RotorRPM+=MotorRPMs[I]*.25f; }
        RotorsRunning=RotorRPM>1;
    }
    for (int32 I=0;I<4;++I) MotorPhases[I]=FMath::Fmod(MotorPhases[I]+(FlightBackend==EWiseEyeFlightBackend::ProjectAirSim?MotorRPMs[I]:RotorRPM)*6.f*Dt,360.f);
    // A swept disc prevents high RPM from appearing stationary under frame-rate aliasing.
    const bool BlurRunning=RotorsRunning && RotorRPM>=1200.f;
    for (int32 I=0; I<AvataRotors.Num(); ++I)
    {
        const bool HasBlur=AvataRotorBlurs.IsValidIndex(I) && IsValid(AvataRotorBlurs[I]);
        if (IsValid(AvataRotors[I])) AvataRotors[I]->SetVisibility(DroneModel==TEXT("avata") && !(BlurRunning && HasBlur));
        if (HasBlur) AvataRotorBlurs[I]->SetVisibility(DroneModel==TEXT("avata") && BlurRunning);
    }
    for (UStaticMeshComponent* Blur : MavicRotorBlurs)
        if (IsValid(Blur)) Blur->SetVisibility(DroneModel==TEXT("mavic3") && BlurRunning);
    static const TSet<FString> MavicBlades={TEXT("Mesh_ncl_92"),TEXT("Mesh_ncl_94"),TEXT("Mesh_ncl_110"),TEXT("Mesh_ncl_111"),TEXT("Mesh_ncl_119"),TEXT("Mesh_ncl_120"),TEXT("Mesh_ncl_99"),TEXT("Mesh_ncl_100")};
    const bool HasMavicBlur=MavicRotorBlurs.Num()==Rotors.Num() && MavicRotorBlurs.Num()>0 &&
        !MavicRotorBlurs.Contains(nullptr);
    for (UPrimitiveComponent* Component : MavicVisualComponents)
        if (UStaticMeshComponent* Mesh=Cast<UStaticMeshComponent>(Component))
            if (Mesh->GetStaticMesh() && MavicBlades.Contains(Mesh->GetStaticMesh()->GetName()))
                Mesh->SetVisibility(DroneModel==TEXT("mavic3") && !(BlurRunning && HasMavicBlur));
    if (!RotorsRunning) return;
    RotorPhase = FMath::Fmod(RotorPhase+FMath::Max(0.f,RotorRPM)*6.f*Dt,360.f);
    for (int32 I=0; I<Rotors.Num(); ++I)
    {
        AWiseEyeRotor* Rotor = Cast<AWiseEyeRotor>(Rotors[I]);
        if (!IsValid(Rotor) || !RotorInitialRotations.IsValidIndex(I)) continue;
        const FQuat Spin(FVector::UpVector,FMath::DegreesToRadians(MotorPhases[I%4]*Rotor->Direction));
        Rotor->SetActorRelativeRotation(RotorInitialRotations[I]*Spin);
    }
    for (int32 I=0; I<AvataRotors.Num(); ++I)
    {
        // Neighboring motors counter-rotate; diagonal motors share a direction.
        const float Direction=(I==0 || I==3) ? 1.f : -1.f;
        if (IsValid(AvataRotors[I]))
            AvataRotors[I]->SetRelativeRotation(FRotator(0,MotorPhases[AvataMotorIndices[I]]*Direction,0));
    }
}

void AWiseEyeDemo::UpdateDroneView()
{
    if (!IsValid(DroneView) || !IsValid(Drone)) return;
    const FVector Target = Drone->GetActorTransform().TransformPosition(TargetOffset);
    const FVector Forward = FRotator(0,Drone->GetActorRotation().Yaw-ModelHeadingOffset,0).Vector();
    const FVector Position = Target-Forward*130.f+FVector(0,0,65.f);
    DroneView->SetActorLocationAndRotation(Position,(Target-Position).Rotation());
}

void AWiseEyeDemo::ToggleFlightMode()
{
    AutomaticFlight = !AutomaticFlight;
    if (AutomaticFlight && IsValid(Drone)) FlightOrigin = Drone->GetActorLocation()-FlightOffset(SimulationTime);
    ManualInput = FVector::ZeroVector;
    ManualYawInput = 0;
}
void AWiseEyeDemo::ToggleTracking() { if (!FleetChild) { auto* Selected=FindDevice(ControlledGimbalId); if (Selected && Selected!=this) { Selected->ToggleTracking(); return; } } TrackingEnabled = !TrackingEnabled; }
void AWiseEyeDemo::ToggleRotors() { if (!FleetChild) { auto* Selected=FindDevice(ControlledDroneId); if (Selected && Selected!=this) { Selected->ToggleRotors(); return; } } if (FlightBackend==EWiseEyeFlightBackend::Kinematic) RotorsRunning = !RotorsRunning; }

void AWiseEyeDemo::TogglePause() { Paused = !Paused; }
void AWiseEyeDemo::ResetSimulation()
{
    SimulationTime = 0;
    FlightOrigin = InitialFlightOrigin;
    ManualInput = FVector::ZeroVector;
    ManualYawInput = 0;
    if (FlightBackend==EWiseEyeFlightBackend::Kinematic) StepSimulation(0,true);
    else StepGimbal(0,true);
    ScanLidar();
    UpdateDroneView();
}
void AWiseEyeDemo::SwitchView()
{
    const FString Next=ObserverMode==TEXT("overview")?TEXT("free"):ObserverMode==TEXT("free")?TEXT("gimbal"):ObserverMode==TEXT("gimbal")?TEXT("follow"):TEXT("overview");
    SetObserverMode(Next);
}
void AWiseEyeDemo::ZoomIn() { if (!FleetChild) { auto* Selected=FindDevice(ControlledGimbalId); if (Selected && Selected!=this) { Selected->ZoomIn(); return; } } if (InfraredMode) InfraredFOV=FMath::Clamp(InfraredFOV-5,5.f,120.f); else VisibleFOV=FMath::Clamp(VisibleFOV-5,5.f,120.f); RefreshSensors(); }
void AWiseEyeDemo::ZoomOut() { if (!FleetChild) { auto* Selected=FindDevice(ControlledGimbalId); if (Selected && Selected!=this) { Selected->ZoomOut(); return; } } if (InfraredMode) InfraredFOV=FMath::Clamp(InfraredFOV+5,5.f,120.f); else VisibleFOV=FMath::Clamp(VisibleFOV+5,5.f,120.f); RefreshSensors(); }
void AWiseEyeDemo::ExportFrame() { if (!FleetChild) { auto* Selected=FindDevice(ControlledGimbalId); if (Selected && Selected!=this) { Selected->ExportFrame(); return; } } ExportSensorFrame(InfraredMode); }
void AWiseEyeDemo::ExportSensorFrame(bool bInfrared)
{
    UTextureRenderTarget2D* Target = bInfrared?InfraredTarget.Get():RenderTarget.Get();
    LastExportPath.Empty();
    if (bInfrared?!InfraredEnabled:!VisibleEnabled) return;
    if (!Target) return;
    // Export the last completed render; never confuse the HUD screenshot with sensor imagery.
    const TCHAR* Sensor = bInfrared ? (BlackHot ? TEXT("IR_BH") : TEXT("IR_WH")) : TEXT("VIS");
    const FString Name = FString::Printf(TEXT("%s_%04d.png"),Sensor,FrameNumber++);
    UKismetRenderingLibrary::ExportRenderTarget(this,Target,OutputDirectory,Name);
    LastExportPath = FPaths::ConvertRelativePathToFull(FPaths::Combine(OutputDirectory,Name));
    const FVector Pos = Camera->GetComponentLocation();
    const FRotator Rot = Camera->GetComponentRotation();
    const FString Meta=FString::Printf(TEXT("{\"simulation_time_s\":%.6f,\"width\":%d,\"height\":%d,\"horizontal_fov_deg\":%.4f,\"modality\":\"%s\",\"palette\":\"%s\",\"thermal_model\":\"%s\",\"camera_cm\":[%.4f,%.4f,%.4f],\"rotation_pitch_yaw_roll_deg\":[%.4f,%.4f,%.4f],\"tracking_source\":\"UE ground truth\",\"frame_timing\":\"last completed render; not hardware synchronized\"}"),SimulationTime,Target->SizeX,Target->SizeY,bInfrared?InfraredFOV:VisibleFOV,bInfrared?TEXT("infrared"):TEXT("visible"),bInfrared?(BlackHot?TEXT("black_hot"):TEXT("white_hot")):TEXT("RGB"),bInfrared?TEXT("normalized synthetic heat; not radiometric"):TEXT("none"),Pos.X,Pos.Y,Pos.Z,Rot.Pitch,Rot.Yaw,Rot.Roll);
    const FString Identity=FString::Printf(TEXT("{\"device_id\":\"%s\",\"sensor_id\":\"%s/%s\",\"scene_id\":\"%s\",\"run_id\":\"%s\","),*GimbalId,*GimbalId,bInfrared?TEXT("infrared"):TEXT("visible"),*SceneId,*PlaySessionId);
    FFileHelper::SaveStringToFile(Identity+Meta.Mid(1),*FPaths::Combine(OutputDirectory,Name+TEXT(".json")));
    UE_LOG(LogTemp,Display,TEXT("WISEYE: exported %s/%s"),*OutputDirectory,*Name);
}
void AWiseEyeDemo::WriteTelemetry()
{
    const FVector P=Drone->GetActorLocation();
    const FString Row=FString::Printf(TEXT("%.4f,%.3f,%.3f,%.3f,%.3f,%.3f,%.6f,%.1f,%d,%d,%d,%.3f\n"),SimulationTime,P.X,P.Y,P.Z,YawPivot->GetRelativeRotation().Yaw,PitchPivot->GetRelativeRotation().Pitch,PointingError,FieldOfView,AutomaticFlight,TrackingEnabled,RotorsRunning,RotorPhase);
    FFileHelper::SaveStringToFile(Row,*FPaths::Combine(OutputDirectory,TEXT("telemetry.csv")),FFileHelper::EEncodingOptions::AutoDetect,&IFileManager::Get(),FILEWRITE_Append);
}

AWiseEyeGameMode::AWiseEyeGameMode(const FObjectInitializer& ObjectInitializer) : Super(ObjectInitializer) { HUDClass=AWiseEyeHUD::StaticClass(); DefaultPawnClass=nullptr; }
void AWiseEyeHUD::DrawHUD()
{
    Super::DrawHUD();
    if (!Canvas) return;
    AWiseEyeDemo* Demo=nullptr;
    for (TActorIterator<AWiseEyeDemo> It(GetWorld());It;++It) { Demo=*It; break; }
    if (!Demo) return;
    DrawRect(FLinearColor(.015f,.025f,.045f,.85f),12,12,790,145);
    DrawText(TEXT("WISEYE  |  UAV / EO SIMULATION"),FLinearColor(.1f,.85f,1),24,20,nullptr,1.3f);
    DrawText(FString::Printf(TEXT("%s | Flight %s/%s | Gimbal %s | Lidar %d/%d"),Demo->Paused?TEXT("PAUSED"):TEXT("RUNNING"),Demo->FlightBackend==EWiseEyeFlightBackend::ProjectAirSim?TEXT("AIRSIM"):TEXT("KINEMATIC"),Demo->DynamicsConnected?TEXT("LINKED"):TEXT("WAIT"),Demo->TrackingEnabled?TEXT("TRACK"):TEXT("HOLD"),Demo->LidarHitCount,Demo->LastLidarRangesMeters.Num()),FLinearColor::White,24,48,nullptr,1.05f);
    DrawText(FString::Printf(TEXT("Input %s | View %s | C input | TAB view | RMB+WASD free"),*Demo->ControlMode,*Demo->ObserverMode),FLinearColor(.75f,.85f,.9f),24,73,nullptr,1);
    DrawText(TEXT("T track/hold | O rotors | TAB view | SPACE pause | HOME reset"),FLinearColor(.75f,.85f,.9f),24,96,nullptr,1);
    DrawText(TEXT("I visible/IR | B palette | +/- zoom | P PNG | drone: WASD, R/F up/down, Q/E yaw"),FLinearColor(.75f,.85f,.9f),24,119,nullptr,.95f);
    if (Demo->PlacementActive)
    {
        DrawRect(FLinearColor(0,.12f,.18f,.9f),12,164,790,36);
        DrawText(FString::Printf(TEXT("PLACE %s | Left click surface | Right click cancel | draft only"),*Demo->PlacementDevice),FLinearColor(0,1,1),24,173,nullptr,1);
        if (Demo->PlacementHoverValid)
        {
            const FVector P=Canvas->Project(Demo->PlacementSurface);
            if (P.Z>0)
            {
                DrawLine(P.X-14,P.Y,P.X+14,P.Y,FLinearColor(0,1,1),2);
                DrawLine(P.X,P.Y-14,P.X,P.Y+14,FLinearColor(0,1,1),2);
                DrawText(TEXT("SURFACE"),FLinearColor(0,1,1),P.X+18,P.Y,nullptr,1);
            }
        }
    }
    if (UTextureRenderTarget2D* Target = Demo->GetSensorTarget())
    {
        const float W=FMath::Min(520.f,Canvas->SizeX*.4f), H=W*float(Target->SizeY)/float(Target->SizeX), X=Canvas->SizeX-W-20, Y=Canvas->SizeY-H-40;
        DrawRect(FLinearColor(.02f,.04f,.06f,1),X-4,Y-29,W+8,H+53);
        DrawText(FString::Printf(TEXT("%s | %d x %d | FOV %.0f"),Demo->InfraredMode?(Demo->BlackHot?TEXT("IR BLACK HOT"):TEXT("IR WHITE HOT")):TEXT("VISIBLE"),Target->SizeX,Target->SizeY,Demo->FieldOfView),FLinearColor(.1f,.85f,1),X+8,Y-23,nullptr,1);
        Canvas->K2_DrawTexture(Target,FVector2D(X,Y),FVector2D(W,H),FVector2D::ZeroVector,FVector2D::UnitVector,FLinearColor::White,BLEND_Opaque);
        DrawLine(X+W/2-10,Y+H/2,X+W/2+10,Y+H/2,FLinearColor::Green);
        DrawLine(X+W/2,Y+H/2-10,X+W/2,Y+H/2+10,FLinearColor::Green);
    }
}

void AWiseEyeDemo::EnsurePlayerInput()
{
    APlayerController* PC = GetWorld()->GetFirstPlayerController();
    if (PC && !PlayerInputBound)
    {
        PC->bAutoManageActiveCameraTarget = false;
        InputPriority = 20;
        EnableInput(PC);
        // EnableInput does not update Priority on an existing component.
        // Project AirSim registers consuming T/Tab actions during scene load.
        PC->PopInputComponent(InputComponent);
        InputComponent->Priority = InputPriority;
        PC->PushInputComponent(InputComponent);
        PC->SetInputMode(FInputModeGameOnly());
        PC->bShowMouseCursor = false;
        InputComponent->BindKey(EKeys::SpaceBar,IE_Pressed,this,&AWiseEyeDemo::LocalTogglePause);
        InputComponent->BindKey(EKeys::Tab,IE_Pressed,this,&AWiseEyeDemo::SwitchView);
        InputComponent->BindKey(EKeys::Home,IE_Pressed,this,&AWiseEyeDemo::LocalReset);
        InputComponent->BindKey(EKeys::C,IE_Pressed,this,&AWiseEyeDemo::CycleControlMode);
        InputComponent->BindKey(EKeys::P,IE_Pressed,this,&AWiseEyeDemo::ExportFrame);
        InputComponent->BindKey(EKeys::M,IE_Pressed,this,&AWiseEyeDemo::LocalToggleFlightMode);
        InputComponent->BindKey(EKeys::T,IE_Pressed,this,&AWiseEyeDemo::ToggleTracking);
        InputComponent->BindKey(EKeys::O,IE_Pressed,this,&AWiseEyeDemo::ToggleRotors);
        InputComponent->BindKey(EKeys::I,IE_Pressed,this,&AWiseEyeDemo::ToggleSensorMode);
        InputComponent->BindKey(EKeys::B,IE_Pressed,this,&AWiseEyeDemo::ToggleThermalPalette);
        InputComponent->BindKey(EKeys::Add,IE_Pressed,this,&AWiseEyeDemo::ZoomIn);
        InputComponent->BindKey(EKeys::Equals,IE_Pressed,this,&AWiseEyeDemo::ZoomIn);
        InputComponent->BindKey(EKeys::Subtract,IE_Pressed,this,&AWiseEyeDemo::ZoomOut);
        InputComponent->BindKey(EKeys::Hyphen,IE_Pressed,this,&AWiseEyeDemo::ZoomOut);
        PC->SetViewTarget(Overview ? static_cast<AActor*>(Overview) : this);
        PlayerInputBound = true;
    }
}

void AWiseEyeDemo::LocalToggleFlightMode()
{
    if (PlacementActive) return;
    if (FlightBackend==EWiseEyeFlightBackend::ProjectAirSim) LocalFlightCommands.Add(TEXT("flight.toggle_mode"));
    else ToggleFlightMode();
}
void AWiseEyeDemo::LocalTogglePause()
{
    if (FlightBackend==EWiseEyeFlightBackend::ProjectAirSim) LocalFlightCommands.Add(TEXT("sim.toggle_pause"));
    else TogglePause();
}
void AWiseEyeDemo::LocalReset()
{
    if (FlightBackend==EWiseEyeFlightBackend::ProjectAirSim) LocalFlightCommands.Add(TEXT("sim.reset"));
    else ResetSimulation();
}
void AWiseEyeDemo::PollLocalFlightInput()
{
    if (FlightBackend!=EWiseEyeFlightBackend::ProjectAirSim) return;
    APlayerController* PC=GetWorld()->GetFirstPlayerController();
    if (!PC) return;
    const FVector Previous=LocalFlightInput;
    const float PreviousYaw=LocalYawInput;
    LocalFlightInput=FVector(float(PC->IsInputKeyDown(EKeys::W))-float(PC->IsInputKeyDown(EKeys::S)),
        float(PC->IsInputKeyDown(EKeys::D))-float(PC->IsInputKeyDown(EKeys::A)),
        float(PC->IsInputKeyDown(EKeys::R))-float(PC->IsInputKeyDown(EKeys::F)));
    LocalYawInput=float(PC->IsInputKeyDown(EKeys::E))-float(PC->IsInputKeyDown(EKeys::Q));
    if (ControlMode!=TEXT("drone") || !GetWorld()->GetGameViewport() || !GetWorld()->GetGameViewport()->Viewport || !GetWorld()->GetGameViewport()->Viewport->HasFocus())
    {
        LocalFlightInput=FVector::ZeroVector;
        LocalYawInput=0;
    }
    if (!LocalFlightInput.IsNearlyZero() || LocalYawInput!=0 || Previous!=LocalFlightInput || PreviousYaw!=LocalYawInput)
        LocalFlightInputDirty=true;
    if (LocalFlightCommands.Num()>16) LocalFlightCommands.RemoveAt(0,LocalFlightCommands.Num()-16);
}

void AWiseEyeDemo::SetPerformanceProfile(const FString& Profile)
{
    PerformanceProfile=Profile;
    const bool Quality=Profile==TEXT("quality"), Economy=Profile==TEXT("economy");
    VisibleCaptureHz=Quality?30:Economy?10:20;
    InfraredCaptureHz=Quality?25:Economy?10:15;
    ObserverCaptureHz=Quality?15:Economy?8:10;
    if (!FleetChild) {
        auto Set=[](const TCHAR* Name,float Value) { if (auto* Var=IConsoleManager::Get().FindConsoleVariable(Name)) Var->Set(Value,ECVF_SetByCode); };
        Set(TEXT("t.MaxFPS"),Quality?60:Economy?30:45);
        Set(TEXT("sg.ShadowQuality"),Quality?3:Economy?1:2);
        Set(TEXT("r.Lumen.Reflections.Allow"),Quality?1:0);
        Set(TEXT("r.Lumen.DiffuseIndirect.Allow"),Economy?0:1);
    }
}
