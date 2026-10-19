#include "WiseEyeDemo.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/InputComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "HAL/FileManager.h"
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
    OutputDirectory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("WISEYE"), FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S")));
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
APlayerController* PC = GetWorld()->GetFirstPlayerController();
    if (PC)
    {
        PC->bAutoManageActiveCameraTarget = false;
        EnableInput(PC);
        InputComponent->BindKey(EKeys::SpaceBar,IE_Pressed,this,&AWiseEyeDemo::TogglePause);
        InputComponent->BindKey(EKeys::Tab,IE_Pressed,this,&AWiseEyeDemo::SwitchView);
        InputComponent->BindKey(EKeys::R,IE_Pressed,this,&AWiseEyeDemo::ResetSimulation);
        InputComponent->BindKey(EKeys::P,IE_Pressed,this,&AWiseEyeDemo::ExportFrame);
        InputComponent->BindKey(EKeys::M,IE_Pressed,this,&AWiseEyeDemo::ToggleFlightMode);
        InputComponent->BindKey(EKeys::T,IE_Pressed,this,&AWiseEyeDemo::ToggleTracking);
        InputComponent->BindKey(EKeys::F,IE_Pressed,this,&AWiseEyeDemo::ToggleRotors);
        InputComponent->BindKey(EKeys::I,IE_Pressed,this,&AWiseEyeDemo::ToggleSensorMode);
        InputComponent->BindKey(EKeys::B,IE_Pressed,this,&AWiseEyeDemo::ToggleThermalPalette);
        InputComponent->BindKey(EKeys::Add,IE_Pressed,this,&AWiseEyeDemo::ZoomIn);
        InputComponent->BindKey(EKeys::Equals,IE_Pressed,this,&AWiseEyeDemo::ZoomIn);
        InputComponent->BindKey(EKeys::Subtract,IE_Pressed,this,&AWiseEyeDemo::ZoomOut);
        InputComponent->BindKey(EKeys::Hyphen,IE_Pressed,this,&AWiseEyeDemo::ZoomOut);
        PC->SetViewTarget(Overview ? static_cast<AActor*>(Overview) : this);
    }
    if (FlightBackend==EWiseEyeFlightBackend::Kinematic) StepSimulation(0, true);
    else
    {
        SetVisualAssemblyCollision(false);
        TryBindDynamicsSource();
        StepGimbal(0,true);
    }
    ScanLidar();
    UpdateDroneView();
    Bridge = new FWiseEyeBridge(*this);
    BridgeReady = Bridge->Start(ControlPort,BridgeError);
    if (!BridgeReady) UE_LOG(LogTemp,Error,TEXT("WISEYE control bridge: %s"),*BridgeError);
    UE_LOG(LogTemp, Display, TEXT("WISEYE: simulation started, output %s"), *OutputDirectory);
}

void AWiseEyeDemo::Tick(float Dt)
{
    Super::Tick(Dt);
    if (!IsValid(Drone)) return;
    if (StreamManager) StreamManager->Tick(RenderTarget,InfraredTarget,SimulationTime);
    if (Bridge) Bridge->Tick();
    if (!Paused)
    {
        if (FlightBackend==EWiseEyeFlightBackend::ProjectAirSim)
        {
            SimulationTime += Dt;
            StepProjectAirSim(Dt);
        }
        else if (AutomaticFlight)
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
    Drone->GetAttachedActors(AttachedDroneActors,true,false);
    for (AActor* Actor : AttachedDroneActors) AddActorVisuals(Actor);
    for (AActor* Rotor : Rotors) AddActorVisuals(Rotor);

    UStaticMesh* AvataMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/WISEYE/DroneModels/Avata/Avata_black.Avata_black"));
    if (AvataMesh && IsValid(Drone) && Drone->GetRootComponent())
    {
        AlternateDroneMesh=NewObject<UStaticMeshComponent>(this,TEXT("AvataVisual"));
        AlternateDroneMesh->SetStaticMesh(AvataMesh);
        AlternateDroneMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        AlternateDroneMesh->SetMobility(EComponentMobility::Movable);
        AlternateDroneMesh->RegisterComponent();
        AlternateDroneMesh->AttachToComponent(Drone->GetRootComponent(),FAttachmentTransformRules::KeepRelativeTransform);
        const FBoxSphereBounds Bounds=AvataMesh->GetBounds();
        const float Span=FMath::Max(Bounds.BoxExtent.X*2.f,Bounds.BoxExtent.Y*2.f);
        const float Scale=Span>1.f ? 60.f/Span : 1.f;
        const FVector ParentScale=Drone->GetRootComponent()->GetComponentScale().GetAbs().ComponentMax(FVector(.0001f));
        const FVector RelativeScale=FVector(Scale)/ParentScale;
        AlternateDroneMesh->SetRelativeScale3D(RelativeScale);
        AlternateDroneMesh->SetRelativeLocation((-Bounds.Origin*Scale)/ParentScale);
        AlternateDroneMesh->SetRelativeRotation(FRotator::ZeroRotator);
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
    DroneModel=Normalized;
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
    const FVector Target = Drone->GetActorTransform().TransformPosition(TargetOffset);
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
    if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
    {
        Input.X += float(PC->IsInputKeyDown(EKeys::W))-float(PC->IsInputKeyDown(EKeys::S));
        Input.Y += float(PC->IsInputKeyDown(EKeys::D))-float(PC->IsInputKeyDown(EKeys::A));
        Input.Z += float(PC->IsInputKeyDown(EKeys::Up))-float(PC->IsInputKeyDown(EKeys::Down));
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
    if (!RotorsRunning) return;
    RotorPhase = FMath::Fmod(RotorPhase+FMath::Max(0.f,RotorRPM)*6.f*Dt,360.f);
    for (int32 I=0; I<Rotors.Num(); ++I)
    {
        AWiseEyeRotor* Rotor = Cast<AWiseEyeRotor>(Rotors[I]);
        if (!IsValid(Rotor) || !RotorInitialRotations.IsValidIndex(I)) continue;
        const FQuat Spin(FVector::UpVector,FMath::DegreesToRadians(RotorPhase*Rotor->Direction));
        Rotor->SetActorRelativeRotation(RotorInitialRotations[I]*Spin);
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
void AWiseEyeDemo::ToggleTracking() { TrackingEnabled = !TrackingEnabled; }
void AWiseEyeDemo::ToggleRotors() { RotorsRunning = !RotorsRunning; }

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
    ViewMode = (ViewMode+1)%3;
    if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
    {
        AActor* Target = ViewMode==2 && DroneView ? static_cast<AActor*>(DroneView) : ViewMode==0 && Overview ? static_cast<AActor*>(Overview) : this;
        PC->SetViewTargetWithBlend(Target,.3f);
    }
}
void AWiseEyeDemo::ZoomIn() { FieldOfView=FMath::Clamp(FieldOfView-5,5.f,120.f); RefreshSensors(); }
void AWiseEyeDemo::ZoomOut() { FieldOfView=FMath::Clamp(FieldOfView+5,5.f,120.f); RefreshSensors(); }
void AWiseEyeDemo::ExportFrame()
{
    UTextureRenderTarget2D* Target = GetSensorTarget();
    if (!Target) return;
    // Export the last completed render; never confuse the HUD screenshot with sensor imagery.
    const TCHAR* Sensor = InfraredMode ? (BlackHot ? TEXT("IR_BH") : TEXT("IR_WH")) : TEXT("VIS");
    const FString Name = FString::Printf(TEXT("%s_%04d.png"),Sensor,FrameNumber++);
    UKismetRenderingLibrary::ExportRenderTarget(this,Target,OutputDirectory,Name);
    LastExportPath = FPaths::ConvertRelativePathToFull(FPaths::Combine(OutputDirectory,Name));
    const FVector Pos = Camera->GetComponentLocation();
    const FRotator Rot = Camera->GetComponentRotation();
    const FString Meta=FString::Printf(TEXT("{\"simulation_time_s\":%.6f,\"width\":%d,\"height\":%d,\"horizontal_fov_deg\":%.4f,\"modality\":\"%s\",\"palette\":\"%s\",\"thermal_model\":\"%s\",\"camera_cm\":[%.4f,%.4f,%.4f],\"rotation_pitch_yaw_roll_deg\":[%.4f,%.4f,%.4f],\"tracking_source\":\"UE ground truth\",\"frame_timing\":\"last completed render; not hardware synchronized\"}"),SimulationTime,Target->SizeX,Target->SizeY,FieldOfView,InfraredMode?TEXT("infrared"):TEXT("visible"),InfraredMode?(BlackHot?TEXT("black_hot"):TEXT("white_hot")):TEXT("RGB"),InfraredMode?TEXT("normalized synthetic heat; not radiometric"):TEXT("none"),Pos.X,Pos.Y,Pos.Z,Rot.Pitch,Rot.Yaw,Rot.Roll);
    FFileHelper::SaveStringToFile(Meta,*FPaths::Combine(OutputDirectory,Name+TEXT(".json")));
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
    DrawText(TEXT("M auto/manual | WASD move | UP/DOWN altitude | Q/E turn | SHIFT boost"),FLinearColor(.75f,.85f,.9f),24,73,nullptr,1);
    DrawText(TEXT("T track/hold | F rotors | TAB overview/EO/drone | SPACE pause | R reset"),FLinearColor(.75f,.85f,.9f),24,96,nullptr,1);
    DrawText(TEXT("I visible/IR | B white/black hot | +/- zoom | P native PNG | UE truth"),FLinearColor(.75f,.85f,.9f),24,119,nullptr,.95f);
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
