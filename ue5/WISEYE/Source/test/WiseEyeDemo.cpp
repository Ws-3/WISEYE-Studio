#include "WiseEyeDemo.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/InputComponent.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

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
    AutoReceiveInput = EAutoReceiveInput::Player0;
}

void AWiseEyeDemo::BeginPlay()
{
    Super::BeginPlay();
    if (!IsValid(Drone))
    {
        UE_LOG(LogTemp, Error, TEXT("WISEYE: assign Drone before playing"));
        SetActorTickEnabled(false);
        return;
    }
    DroneInitialRotation = Drone->GetActorRotation();
    if (!RenderTarget)
    {
        RenderTarget = NewObject<UTextureRenderTarget2D>(this);
        RenderTarget->RenderTargetFormat = RTF_RGBA8;
        RenderTarget->InitAutoFormat(1280,720);
    }
    Capture->TextureTarget = RenderTarget;
    Camera->SetFieldOfView(FieldOfView);
    Capture->FOVAngle = FieldOfView;
    OutputDirectory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("WISEYE"), FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S")));
    IFileManager::Get().MakeDirectory(*OutputDirectory, true);
    FFileHelper::SaveStringToFile(TEXT("time_s,drone_x_cm,drone_y_cm,drone_z_cm,yaw_deg,pitch_deg,pointing_error_deg,fov_deg\n"), *FPaths::Combine(OutputDirectory,TEXT("telemetry.csv")));
    APlayerController* PC = GetWorld()->GetFirstPlayerController();
    if (PC)
    {
        PC->bAutoManageActiveCameraTarget = false;
        EnableInput(PC);
        InputComponent->BindKey(EKeys::SpaceBar,IE_Pressed,this,&AWiseEyeDemo::TogglePause);
        InputComponent->BindKey(EKeys::Tab,IE_Pressed,this,&AWiseEyeDemo::SwitchView);
        InputComponent->BindKey(EKeys::R,IE_Pressed,this,&AWiseEyeDemo::ResetSimulation);
        InputComponent->BindKey(EKeys::P,IE_Pressed,this,&AWiseEyeDemo::ExportFrame);
        InputComponent->BindKey(EKeys::Add,IE_Pressed,this,&AWiseEyeDemo::ZoomIn);
        InputComponent->BindKey(EKeys::Equals,IE_Pressed,this,&AWiseEyeDemo::ZoomIn);
        InputComponent->BindKey(EKeys::Subtract,IE_Pressed,this,&AWiseEyeDemo::ZoomOut);
        InputComponent->BindKey(EKeys::Hyphen,IE_Pressed,this,&AWiseEyeDemo::ZoomOut);
        PC->SetViewTarget(Overview ? static_cast<AActor*>(Overview) : this);
    }
    StepSimulation(0, true);
    UE_LOG(LogTemp, Display, TEXT("WISEYE: simulation started, output %s"), *OutputDirectory);
}

void AWiseEyeDemo::Tick(float Dt)
{
    Super::Tick(Dt);
    if (!IsValid(Drone)) return;
    if (!Paused)
    {
        SimulationTime += Dt;
        StepSimulation(Dt,false);
    }
    TelemetryClock += Dt;
    if (TelemetryClock >= 1)
    {
        TelemetryClock = 0;
        WriteTelemetry();
    }
}

void AWiseEyeDemo::StepSimulation(float Dt, bool Snap)
{
    // Repeatable figure-eight; analytic velocity determines heading.
    const float W = 2*PI/FMath::Max(1.f,Period);
    const float T = SimulationTime*W;
    const FVector P = FlightOrigin + FVector(FlightRadius*FMath::Sin(T), .65f*FlightRadius*FMath::Sin(2*T), 450*FMath::Sin(T));
    const FVector V(FlightRadius*W*FMath::Cos(T),1.3f*FlightRadius*W*FMath::Cos(2*T),450*W*FMath::Cos(T));
    // Imported model heading offset remains an asset calibration, not a flight-dynamics model.
    FRotator Heading = DroneInitialRotation;
    Heading.Yaw += V.Rotation().Yaw;
    Heading.Roll = 4*FMath::Sin(T);
    Drone->SetActorLocationAndRotation(P, Heading, false, nullptr, ETeleportType::TeleportPhysics);
    const FVector Target = Drone->GetActorTransform().TransformPosition(TargetOffset);
    // Solve from the displaced optical center, not the importer root or mesh bounds.
    const FVector LocalDirection = Base->GetComponentTransform().InverseTransformVectorNoScale(Target-Camera->GetComponentLocation());
    const FRotator Desired = LocalDirection.Rotation();
    const float OldYaw = YawPivot->GetRelativeRotation().Yaw;
    const float OldPitch = PitchPivot->GetRelativeRotation().Pitch;
    const float Yaw = Snap ? Desired.Yaw : FMath::FixedTurn(OldYaw,Desired.Yaw,FMath::Max(0.f,YawRate)*Dt);
    const float DesiredPitch = FMath::Clamp(Desired.Pitch,MinPitch,MaxPitch);
    const float Pitch = Snap ? DesiredPitch : FMath::FInterpConstantTo(OldPitch,DesiredPitch,Dt,FMath::Max(0.f,PitchRate));
    YawPivot->SetRelativeRotation(FRotator(0,Yaw,0));
    PitchPivot->SetRelativeRotation(FRotator(Pitch,0,0));
    const FVector Sight = (Target-Camera->GetComponentLocation()).GetSafeNormal();
    PointingError = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(Sight,Camera->GetForwardVector()),-1.0,1.0)));
}

void AWiseEyeDemo::TogglePause() { Paused = !Paused; }
void AWiseEyeDemo::ResetSimulation() { SimulationTime = 0; StepSimulation(0,true); }
void AWiseEyeDemo::SwitchView()
{
    CameraView = !CameraView;
    if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
        PC->SetViewTargetWithBlend(CameraView || !Overview ? this : static_cast<AActor*>(Overview), .3f);
}
void AWiseEyeDemo::ZoomIn() { FieldOfView=FMath::Clamp(FieldOfView-5,5.f,120.f); Camera->SetFieldOfView(FieldOfView); Capture->FOVAngle=FieldOfView; }
void AWiseEyeDemo::ZoomOut() { FieldOfView=FMath::Clamp(FieldOfView+5,5.f,120.f); Camera->SetFieldOfView(FieldOfView); Capture->FOVAngle=FieldOfView; }
void AWiseEyeDemo::ExportFrame()
{
    if (!RenderTarget) return;
    // Export the last completed render; never confuse the HUD screenshot with sensor imagery.
    const FString Name = FString::Printf(TEXT("EO_%04d.png"),FrameNumber++);
    UKismetRenderingLibrary::ExportRenderTarget(this,RenderTarget,OutputDirectory,Name);
    const FVector Pos = Camera->GetComponentLocation();
    const FRotator Rot = Camera->GetComponentRotation();
    const FString Meta=FString::Printf(TEXT("{\"simulation_time_s\":%.6f,\"width\":%d,\"height\":%d,\"fov_deg\":%.4f,\"camera_cm\":[%.4f,%.4f,%.4f],\"rotation_pitch_yaw_roll_deg\":[%.4f,%.4f,%.4f],\"tracking_source\":\"UE ground truth\",\"frame_timing\":\"last completed render\"}"),SimulationTime,RenderTarget->SizeX,RenderTarget->SizeY,FieldOfView,Pos.X,Pos.Y,Pos.Z,Rot.Pitch,Rot.Yaw,Rot.Roll);
    FFileHelper::SaveStringToFile(Meta,*FPaths::Combine(OutputDirectory,Name+TEXT(".json")));
    UE_LOG(LogTemp,Display,TEXT("WISEYE: exported %s/%s"),*OutputDirectory,*Name);
}
void AWiseEyeDemo::WriteTelemetry()
{
    const FVector P=Drone->GetActorLocation();
    const FString Row=FString::Printf(TEXT("%.4f,%.3f,%.3f,%.3f,%.3f,%.3f,%.6f,%.1f\n"),SimulationTime,P.X,P.Y,P.Z,YawPivot->GetRelativeRotation().Yaw,PitchPivot->GetRelativeRotation().Pitch,PointingError,FieldOfView);
    FFileHelper::SaveStringToFile(Row,*FPaths::Combine(OutputDirectory,TEXT("telemetry.csv")),FFileHelper::EEncodingOptions::AutoDetect,&IFileManager::Get(),FILEWRITE_Append);
}

AWiseEyeGameMode::AWiseEyeGameMode() { HUDClass=AWiseEyeHUD::StaticClass(); DefaultPawnClass=nullptr; }
void AWiseEyeHUD::DrawHUD()
{
    Super::DrawHUD();
    if (!Canvas) return;
    AWiseEyeDemo* Demo=nullptr;
    for (TActorIterator<AWiseEyeDemo> It(GetWorld());It;++It) { Demo=*It; break; }
    if (!Demo) return;
    DrawRect(FLinearColor(0.015,0.025,0.045,.85),12,12,710,106);
    DrawText(TEXT("WISEYE  |  UAV / EO SIMULATION"),FLinearColor(.1,.85,1),24,20,nullptr,1.3);
    DrawText(FString::Printf(TEXT("%s   t=%.1fs   Yaw %.1f   Pitch %.1f   Error %.3f deg"),Demo->Paused?TEXT("PAUSED"):TEXT("TRACKING"),Demo->SimulationTime,Demo->YawPivot->GetRelativeRotation().Yaw,Demo->PitchPivot->GetRelativeRotation().Pitch,Demo->PointingError),FLinearColor::White,24,50,nullptr,1.05);
    DrawText(TEXT("TAB view   SPACE pause   R restart   +/- zoom   P save PNG   ESC stop"),FLinearColor(.75,.85,.9),24,78,nullptr,1);
    DrawText(TEXT("Target: UE ground truth | Kinematic flight | Imported scale"),FLinearColor(.75,.85,.9),24,99,nullptr,.85);
    if (Demo->RenderTarget)
    {
        const float W=FMath::Min(520.f,Canvas->SizeX*.4f), H=W*9/16, X=Canvas->SizeX-W-20, Y=Canvas->SizeY-H-40;
        DrawRect(FLinearColor(.02,.04,.06,1),X-4,Y-29,W+8,H+53);
        DrawText(FString::Printf(TEXT("EO CAMERA  |  1280 x 720  |  FOV %.0f"),Demo->FieldOfView),FLinearColor(.1,.85,1),X+8,Y-23,nullptr,1);
        Canvas->K2_DrawTexture(Demo->RenderTarget,FVector2D(X,Y),FVector2D(W,H),FVector2D::ZeroVector,FVector2D::UnitVector,FLinearColor::White,BLEND_Opaque);
        DrawLine(X+W/2-10,Y+H/2,X+W/2+10,Y+H/2,FLinearColor::Green);
        DrawLine(X+W/2,Y+H/2-10,X+W/2,Y+H/2+10,FLinearColor::Green);
    }
}
