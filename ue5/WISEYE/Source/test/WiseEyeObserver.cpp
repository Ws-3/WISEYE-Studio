#include "WiseEyeDemo.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/SceneComponent.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerController.h"
#include "UnrealClient.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "WiseEyeStreaming.h"
#include "HAL/PlatformTime.h"

bool AWiseEyeDemo::SetControlMode(const FString& Mode)
{
    if (Mode!=TEXT("observer") && Mode!=TEXT("drone") && Mode!=TEXT("gimbal")) return false;
    if (PlacementActive && Mode!=TEXT("observer")) CancelPlacement();
    if (ControlMode!=Mode)
    {
        LocalFlightInput=FVector::ZeroVector;
        LocalYawInput=0;
        LocalFlightInputDirty=true;
        SetManualInput(0,0,0,0);
        RemoteObserverInput=FVector::ZeroVector;
        RemoteGimbalInput=FVector2D::ZeroVector;
    }
    ControlMode=Mode;
    return true;
}

void AWiseEyeDemo::CycleControlMode()
{
    SetControlMode(ControlMode==TEXT("observer")?TEXT("drone"):ControlMode==TEXT("drone")?TEXT("gimbal"):TEXT("observer"));
}

bool AWiseEyeDemo::SetObserverMode(const FString& Mode)
{
    if (Mode!=TEXT("overview") && Mode!=TEXT("free") && Mode!=TEXT("gimbal") && Mode!=TEXT("follow")) return false;
    if (PlacementActive) CancelPlacement();
    APlayerController* PC=GetWorld()->GetFirstPlayerController();
    if (!PC) return false;
    if (Mode==TEXT("free") && !IsValid(FreeObserver))
    {
        FreeObserver=GetWorld()->SpawnActor<ACameraActor>();
        if (!FreeObserver) return false;
        FreeObserver->GetCameraComponent()->SetFieldOfView(70);
        FreeObserver->SetActorLocationAndRotation(PC->PlayerCameraManager->GetCameraLocation(),PC->PlayerCameraManager->GetCameraRotation());
    }
    auto* SelectedDrone=FindDevice(ControlledDroneId);auto* SelectedGimbal=FindDevice(ControlledGimbalId);
    AActor* ViewTarget=Mode==TEXT("free")?FreeObserver.Get():Mode==TEXT("follow")?(SelectedDrone?SelectedDrone->DroneView.Get():DroneView.Get()):Mode==TEXT("gimbal")?static_cast<AActor*>(SelectedGimbal?SelectedGimbal:this):static_cast<AActor*>(Overview.Get());
    if (!IsValid(ViewTarget)) return false;
    ObserverMode=Mode;
    PC->SetViewTargetWithBlend(ViewTarget,.2f);
    return true;
}

void AWiseEyeDemo::StepObserver(float Dt)
{
    if (PlacementActive) { StepPlacement(); return; }
    const double Now=FPlatformTime::Seconds();
    if (ControlMode==TEXT("observer") && ObserverMode==TEXT("free") && IsValid(FreeObserver) && Now-ObserverInputTime<.3)
    {
        const FRotator R=FreeObserver->GetActorRotation();
        const FVector Move=R.Vector()*RemoteObserverInput.X+FRotationMatrix(R).GetUnitAxis(EAxis::Y)*RemoteObserverInput.Y+FVector::UpVector*RemoteObserverInput.Z;
        FreeObserver->AddActorWorldOffset(Move.GetClampedToMaxSize(1)*600.f*FMath::Min(Dt,.1f));
    }
    if (ControlMode==TEXT("gimbal") && Now-GimbalInputTime<.3 && !RemoteGimbalInput.IsNearlyZero())
    {
        TrackingEnabled=false;
        YawPivot->SetRelativeRotation(FRotator(0,FMath::UnwindDegrees(YawPivot->GetRelativeRotation().Yaw+RemoteGimbalInput.X*30*Dt),0));
        PitchPivot->SetRelativeRotation(FRotator(FMath::Clamp(PitchPivot->GetRelativeRotation().Pitch+RemoteGimbalInput.Y*20*Dt,MinPitch,MaxPitch),0,0));
    }
    if (FleetChild) return;
    APlayerController* PC=GetWorld()->GetFirstPlayerController();
    const bool Focused=GetWorld()->GetGameViewport() && GetWorld()->GetGameViewport()->Viewport && GetWorld()->GetGameViewport()->Viewport->HasFocus();
    if (!PC || !Focused) return;
    if (ControlMode==TEXT("observer") && ObserverMode==TEXT("free") && IsValid(FreeObserver) && PC->IsInputKeyDown(EKeys::RightMouseButton))
    {
        float X=0,Y=0; PC->GetInputMouseDelta(X,Y);
        FRotator Rotation=FreeObserver->GetActorRotation();
        Rotation.Yaw+=X*.15f; Rotation.Pitch=FMath::Clamp(Rotation.Pitch+Y*.15f,-89.f,89.f);
        FreeObserver->SetActorRotation(Rotation);
        const FVector Axis(float(PC->IsInputKeyDown(EKeys::W))-float(PC->IsInputKeyDown(EKeys::S)),float(PC->IsInputKeyDown(EKeys::D))-float(PC->IsInputKeyDown(EKeys::A)),float(PC->IsInputKeyDown(EKeys::E))-float(PC->IsInputKeyDown(EKeys::Q)));
        const float Speed=PC->IsInputKeyDown(EKeys::LeftShift)?3000.f:600.f;
        const FVector Delta=Rotation.Vector()*Axis.X+FRotationMatrix(Rotation).GetUnitAxis(EAxis::Y)*Axis.Y+FVector::UpVector*Axis.Z;
        FreeObserver->AddActorWorldOffset(Delta.GetClampedToMaxSize(1)*Speed*FMath::Min(Dt,.1f));
    }
    else if (ControlMode==TEXT("gimbal"))
    {
        AWiseEyeDemo* Selected=FindDevice(ControlledGimbalId);if (!Selected) Selected=this;
        const float Yaw=float(PC->IsInputKeyDown(EKeys::Right))-float(PC->IsInputKeyDown(EKeys::Left));
        const float Pitch=float(PC->IsInputKeyDown(EKeys::Up))-float(PC->IsInputKeyDown(EKeys::Down));
        if (Yaw!=0 || Pitch!=0)
        {
            Selected->TrackingEnabled=false;
            Selected->YawPivot->SetRelativeRotation(FRotator(0,FMath::UnwindDegrees(Selected->YawPivot->GetRelativeRotation().Yaw+Yaw*30*Dt),0));
            Selected->PitchPivot->SetRelativeRotation(FRotator(FMath::Clamp(Selected->PitchPivot->GetRelativeRotation().Pitch+Pitch*20*Dt,Selected->MinPitch,Selected->MaxPitch),0,0));
        }
    }
}

void AWiseEyeDemo::UpdateObserverCapture()
{
    ObserverCaptured=false;
    APlayerController* PC=GetWorld()->GetFirstPlayerController();
    if (!PC || !PC->PlayerCameraManager) return;
    if (!ObserverCapture)
    {
        ObserverTarget=NewObject<UTextureRenderTarget2D>(this);
        ObserverTarget->RenderTargetFormat=RTF_RGBA8;
        ObserverTarget->bForceLinearGamma=true;
        ObserverTarget->InitAutoFormat(960,540);
        ObserverTarget->TargetGamma=2.2f;
        ObserverCapture=NewObject<USceneCaptureComponent2D>(this);
        ObserverCapture->SetupAttachment(GetRootComponent());
        ObserverCapture->CaptureSource=ESceneCaptureSource::SCS_FinalColorLDR;
        ObserverCapture->TextureTarget=ObserverTarget;
        ObserverCapture->bCaptureEveryFrame=false;
        ObserverCapture->bCaptureOnMovement=false;
        ObserverCapture->bAlwaysPersistRenderingState=true;
        ObserverCapture->RegisterComponent();
    }
    ObserverCapture->SetWorldLocationAndRotation(PC->PlayerCameraManager->GetCameraLocation(),PC->PlayerCameraManager->GetCameraRotation());
    ObserverCapture->FOVAngle=PC->PlayerCameraManager->GetFOVAngle();
    // Observation preview is separate from calibrated sensor captures and HUD.
    const float Interval=1.f/ObserverCaptureHz;
    const float Now=GetWorld()->GetRealTimeSeconds();
    if (Now>=ObserverCaptureTime)
    {
        ObserverCapture->CaptureScene();
        ObserverCaptureTime=FMath::Max(ObserverCaptureTime+Interval,Now+.001f);
        ObserverCaptured=true;
    }
}

bool AWiseEyeDemo::GetObserverFrame(TArray64<uint8>& Jpeg,int32& Width,int32& Height,int64& Sequence,double& Time) const
{
    return StreamManager && StreamManager->GetObserverFrame(Jpeg,Width,Height,Sequence,Time);
}
