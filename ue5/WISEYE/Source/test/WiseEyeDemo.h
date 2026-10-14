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
class UMaterialInterface;
class UMaterialInstanceDynamic;
class FWiseEyeBridge;

/** Two-axis ground EO demonstrator. Centimeters, degrees, +X optical axis. */
UCLASS()
class TEST_API AWiseEyeDemo : public AActor
{
    GENERATED_BODY()
public:
    AWiseEyeDemo();
    virtual ~AWiseEyeDemo();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneComponent> Base;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneComponent> YawPivot;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneComponent> PitchPivot;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneCaptureComponent2D> Capture;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneCaptureComponent2D> InfraredCapture;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") TObjectPtr<AActor> Drone;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") TObjectPtr<ACameraActor> Overview;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") TObjectPtr<UTextureRenderTarget2D> RenderTarget;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Sensors") TObjectPtr<UTextureRenderTarget2D> InfraredTarget;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Sensors") TObjectPtr<UMaterialInterface> ThermalMaterial;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Sensors") TObjectPtr<UMaterialInstanceDynamic> ThermalInstance;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Sensors") bool InfraredMode = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Sensors") bool BlackHot = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Sensors", meta=(ClampMin="0", ClampMax="1")) float BodyHeat = .65f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Sensors", meta=(ClampMin="0", ClampMax="1")) float MotorHeat = .92f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Sensors", meta=(ClampMin="0", ClampMax="1")) float RotorHeat = .48f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Sensors", meta=(ClampMin="0", ClampMax="1")) float BackgroundHeat = .27f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Sensors", meta=(ClampMin="0", ClampMax="1")) float SkyHeat = .08f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Sensors", meta=(ClampMin="0", ClampMax=".1")) float ThermalNoise = .008f;
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
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Flight") bool AutomaticFlight = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Flight", meta=(ClampMin="0")) float VerticalAmplitude = 150;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Flight", meta=(ClampMin="1")) float ManualSpeed = 300;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Flight", meta=(ClampMin="1")) float ManualYawRate = 90;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Flight") float MinimumAltitude = 60;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Flight") float MaximumAltitude = 5000;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Flight") float ModelHeadingOffset = -90;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Gimbal") bool TrackingEnabled = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Rotors") bool RotorsRunning = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Rotors", meta=(ClampMin="0", ClampMax="3000")) float RotorRPM = 600;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Rotors") TArray<TObjectPtr<AActor>> Rotors;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Rotors") float RotorPhase = 0;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE") TObjectPtr<ACameraActor> DroneView;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE") float SimulationTime = 0;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE") float PointingError = 0;
    UPROPERTY(EditAnywhere, Category="WISEYE|Bridge", meta=(ClampMin="1024",ClampMax="65535")) int32 ControlPort = 50051;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Bridge") bool BridgeReady = false;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Bridge") FString BridgeError;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Sensors") FString LastExportPath;
    UFUNCTION(BlueprintCallable, Category="WISEYE") void TogglePause();
    UFUNCTION(BlueprintCallable, Category="WISEYE") void ResetSimulation();
    UFUNCTION(BlueprintCallable, Category="WISEYE") void SwitchView();
    UFUNCTION(BlueprintCallable, Category="WISEYE") void ExportFrame();
    UFUNCTION(BlueprintCallable, Category="WISEYE") void ZoomIn();
    UFUNCTION(BlueprintCallable, Category="WISEYE") void ZoomOut();
    UFUNCTION(BlueprintCallable, Category="WISEYE") void ToggleFlightMode();
    UFUNCTION(BlueprintCallable, Category="WISEYE") void ToggleTracking();
    UFUNCTION(BlueprintCallable, Category="WISEYE") void ToggleRotors();
    UFUNCTION(BlueprintCallable, Category="WISEYE|Sensors") void ToggleSensorMode();
    UFUNCTION(BlueprintCallable, Category="WISEYE|Sensors") void ToggleThermalPalette();
    UFUNCTION(BlueprintCallable, Category="WISEYE|Sensors") void RefreshSensors();
    UFUNCTION(BlueprintPure, Category="WISEYE|Sensors") UTextureRenderTarget2D* GetSensorTarget() const;
    /** Normalized forward/right/up and yaw inputs; keyboard input is added at runtime. */
    UFUNCTION(BlueprintCallable, Category="WISEYE") void SetManualInput(float Forward, float Right, float Up, float Yaw);
private:
    void StepSimulation(float DeltaSeconds, bool Snap);
    FVector FlightOffset(float Time) const;
    void StepManualFlight(float DeltaSeconds);
    void StepGimbal(float DeltaSeconds, bool Snap);
    void StepRotors(float DeltaSeconds);
    void UpdateDroneView();
    void InitializeSensors();
    void ConfigureThermalActors();
    void WriteTelemetry();
    FRotator DroneInitialRotation;
    FVector InitialFlightOrigin;
    FVector ManualInput = FVector::ZeroVector;
    float ManualYawInput = 0;
    TArray<FQuat> RotorInitialRotations;
    float TelemetryClock = 0;
    int32 FrameNumber = 0;
    int32 ViewMode = 0;
    FString OutputDirectory;
    FWiseEyeBridge* Bridge = nullptr;
};

/** Persisted pivot for the imported hub and two blades of one rotor. */
UCLASS()
class TEST_API AWiseEyeRotor : public AActor
{
    GENERATED_BODY()
public:
    AWiseEyeRotor();
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Pivot;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") float Direction = 1;
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
