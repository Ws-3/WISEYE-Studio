#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/HUD.h"
#include "GameFramework/GameModeBase.h"
#include "WiseEyeDemo.generated.h"

class USceneComponent;
class UCameraComponent;
class USceneCaptureComponent2D;
class UTextureRenderTarget2D;
class ACameraActor;

/** Two-axis ground EO demonstrator. Centimeters, degrees, +X optical axis. */
UCLASS()
class TEST_API AWiseEyeDemo : public AActor
{
    GENERATED_BODY()
public:
    AWiseEyeDemo();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneComponent> Base;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneComponent> YawPivot;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneComponent> PitchPivot;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneCaptureComponent2D> Capture;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") TObjectPtr<AActor> Drone;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") TObjectPtr<ACameraActor> Overview;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") TObjectPtr<UTextureRenderTarget2D> RenderTarget;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") FVector FlightOrigin = FVector(0,0,4000);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") FVector TargetOffset = FVector::ZeroVector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE", meta=(ClampMin="1")) float FlightRadius = 4000;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE", meta=(ClampMin="1")) float Period = 36;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE", meta=(ClampMin="1")) float YawRate = 45;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE", meta=(ClampMin="1")) float PitchRate = 30;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") float MinPitch = -15;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") float MaxPitch = 75;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE", meta=(ClampMin="5", ClampMax="120")) float FieldOfView = 45;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE") bool Paused = false;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE") float SimulationTime = 0;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE") float PointingError = 0;
    UFUNCTION(BlueprintCallable, Category="WISEYE") void TogglePause();
    UFUNCTION(BlueprintCallable, Category="WISEYE") void ResetSimulation();
    UFUNCTION(BlueprintCallable, Category="WISEYE") void SwitchView();
    UFUNCTION(BlueprintCallable, Category="WISEYE") void ExportFrame();
    UFUNCTION(BlueprintCallable, Category="WISEYE") void ZoomIn();
    UFUNCTION(BlueprintCallable, Category="WISEYE") void ZoomOut();
private:
    void StepSimulation(float DeltaSeconds, bool Snap);
    void WriteTelemetry();
    FRotator DroneInitialRotation;
    float TelemetryClock = 0;
    int32 FrameNumber = 0;
    bool CameraView = false;
    FString OutputDirectory;
};

UCLASS()
class TEST_API AWiseEyeHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
};

UCLASS()
class TEST_API AWiseEyeGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AWiseEyeGameMode();
};
