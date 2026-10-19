#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/HUD.h"
#include "ProjectAirSimGameMode.h"
#include "WiseEyeDemo.generated.h"

class USceneComponent;
class UCameraComponent;
class USceneCaptureComponent2D;
class UTextureRenderTarget2D;
class ACameraActor;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UStaticMeshComponent;
class UPrimitiveComponent;
class FWiseEyeBridge;
class FWiseEyeStreamManager;

UENUM(BlueprintType)
enum class EWiseEyeFlightBackend : uint8
{
    Kinematic UMETA(DisplayName="WISEYE Kinematic"),
    ProjectAirSim UMETA(DisplayName="Project AirSim")
};

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
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Scene") FString SceneId = TEXT("original");
    FString PendingScene;
    bool RequestScene(const FString& Id, FString& Error);
    bool ApplySceneConfiguration(FString& Error);
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneComponent> Base;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneComponent> YawPivot;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneComponent> PitchPivot;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneCaptureComponent2D> Capture;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneCaptureComponent2D> InfraredCapture;
    /** Laser scanner origin. It is below the pitch pivot through the EO camera hierarchy. */
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="WISEYE|Lidar") TObjectPtr<USceneComponent> LidarMount;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="WISEYE|Lidar") TObjectPtr<UStaticMeshComponent> LidarBody;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") TObjectPtr<AActor> Drone;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") TObjectPtr<ACameraActor> Overview;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") TObjectPtr<UTextureRenderTarget2D> RenderTarget;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Sensors") TObjectPtr<UTextureRenderTarget2D> InfraredTarget;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Sensors") TObjectPtr<UMaterialInterface> ThermalMaterial;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Sensors") TObjectPtr<UMaterialInstanceDynamic> ThermalInstance;
    // Real‑time image processing (updated every Tick)
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|ImageProcessing")
    UTextureRenderTarget2D* ProcessedRenderTarget = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|ImageProcessing")
    UMaterialInstanceDynamic* MatInst = nullptr;

    // Image‑processing parameters (exposed to editor/BP, 0‑10 range)
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|ImageProcessing",
              meta=(ClampMin="0",ClampMax="10"))
    float Gain = 1.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|ImageProcessing",
              meta=(ClampMin="0",ClampMax="1"))
    float Gamma = 0.45f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|ImageProcessing",
              meta=(ClampMin="0",ClampMax="1"))
    float NoiseSigma = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Sensors") bool InfraredMode = false;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Sensors") FString ActiveSensor = TEXT("visible");
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
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Flight") EWiseEyeFlightBackend FlightBackend = EWiseEyeFlightBackend::ProjectAirSim;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Flight") FName DynamicsActorName = TEXT("Drone1");
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Flight") TObjectPtr<AActor> DynamicsSource;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Flight") bool DynamicsConnected = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Flight") bool HideDynamicsVisual = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Flight") FRotator DynamicsVisualRotationOffset = FRotator(0,-90,0);
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
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Drone") FString DroneModel = TEXT("mavic3");
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="WISEYE|Drone") TObjectPtr<UStaticMeshComponent> AlternateDroneMesh;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE") TObjectPtr<ACameraActor> DroneView;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE") float SimulationTime = 0;
    // Last captured frame pixels (processed, for read‑back by user code)
    TArray<FColor> LastFramePixels;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE") float PointingError = 0;
    UPROPERTY(EditAnywhere, Category="WISEYE|Bridge", meta=(ClampMin="1024",ClampMax="65535")) int32 ControlPort = 50051;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Bridge") bool BridgeReady = false;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Bridge") FString BridgeError;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Sensors") FString LastExportPath;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Lidar") bool LidarEnabled = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Lidar", meta=(ClampMin="1", ClampMax="128")) int32 LidarHorizontalSamples = 48;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Lidar", meta=(ClampMin="1", ClampMax="64")) int32 LidarVerticalSamples = 12;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Lidar", meta=(ClampMin="0.1", ClampMax="60")) float LidarHorizontalFov = 30;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Lidar", meta=(ClampMin="0.1", ClampMax="60")) float LidarVerticalFov = 8;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Lidar", meta=(ClampMin="1", ClampMax="1000")) float LidarRangeMeters = 300;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Lidar", meta=(ClampMin="0.05", ClampMax="10")) float LidarScanRateHz = 10;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Lidar") int32 LidarHitCount = 0;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Lidar") float LidarNearestRangeMeters = 0;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Lidar") FString LastLidarExportPath;
    TArray<float> LastLidarRangesMeters;
    TArray<FVector> LastLidarPointsWorldCm;
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
    UFUNCTION(BlueprintCallable, Category="WISEYE|Lidar") void ScanLidar();
    UFUNCTION(BlueprintCallable, Category="WISEYE|Lidar") bool ExportLidarPointCloud();
    TArray<FVector> GetLidarPreviewPoints(int32 MaxPoints=1024) const;
    UFUNCTION(BlueprintPure, Category="WISEYE|Sensors") UTextureRenderTarget2D* GetSensorTarget() const;
    /** Normalized forward/right/up and yaw inputs; keyboard input is added at runtime. */
    UFUNCTION(BlueprintCallable, Category="WISEYE") void SetManualInput(float Forward, float Right, float Up, float Yaw);
    bool SetDroneModel(const FString& ModelId, FString& Error);
    bool GetStreamFrame(bool bInfrared, TArray64<uint8>& Jpeg, int32& Width, int32& Height,
                        int64& StreamFrameNumber, double& StreamSimulationTime) const;
private:
    void StepSimulation(float DeltaSeconds, bool Snap);
    FVector FlightOffset(float Time) const;
    void StepManualFlight(float DeltaSeconds);
    void StepGimbal(float DeltaSeconds, bool Snap);
    void StepRotors(float DeltaSeconds);
    void StepProjectAirSim(float DeltaSeconds);
    bool TryBindDynamicsSource();
    void SetVisualAssemblyCollision(bool Enabled);
    void UpdateDroneView();
    void InitializeSensors();
    void InitializeDroneModels();
    void ConfigureThermalActors();
    void WriteTelemetry();
    FRotator DroneInitialRotation;
    FVector InitialFlightOrigin;
    FVector ManualInput = FVector::ZeroVector;
    float ManualYawInput = 0;
    TArray<FQuat> RotorInitialRotations;
    UPROPERTY() TArray<TObjectPtr<UPrimitiveComponent>> MavicVisualComponents;
    float TelemetryClock = 0;
    float LidarClock = 0;
    FTransform LastLidarPose;
    int32 FrameNumber = 0;
    int32 ViewMode = 0;
    FString OutputDirectory;
    FWiseEyeBridge* Bridge = nullptr;
    FWiseEyeStreamManager* StreamManager = nullptr;
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
class TEST_API AWiseEyeGameMode : public AProjectAirSimGameMode
{
    GENERATED_BODY()
public:
    explicit AWiseEyeGameMode(const FObjectInitializer& ObjectInitializer);
};
