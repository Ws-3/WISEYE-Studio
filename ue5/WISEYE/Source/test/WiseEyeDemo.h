#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/HUD.h"
#include "ProjectAirSimGameMode.h"
#include "WiseEyeThermalMath.h"
#include "WiseEyeFocus.h"
#include "WiseEyeGroundTruth.h"
#include "WiseEyeFixedwingEngine.h"
#include "WiseEyeDemo.generated.h"

class FJsonObject;
class FJsonValue;
class USceneComponent;
class UCameraComponent;
class USceneCaptureComponent2D;
class UTextureRenderTarget2D;
class ACameraActor;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UStaticMeshComponent;
class UStaticMesh;
class UPrimitiveComponent;
class FWiseEyeBridge;
class FWiseEyeStreamManager;
class UWiseEyePopulationWatch;
struct FWiseEyeThermalReadoutState;
class UDirectionalLightComponent;
class USkyLightComponent;
class UExponentialHeightFogComponent;
class UMaterialParameterCollectionInstance;
class UMaterialParameterCollection;
class UInstancedStaticMeshComponent;

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
    friend class FWiseEyeBridge;
    friend TSharedPtr<FWiseEyeGTSnapshot> CaptureWiseEyeGroundTruth(AWiseEyeDemo&,bool,const FString&);
public:
    AWiseEyeDemo();
    bool FleetChild=false;
    bool OwnsDrone=true;
    FString DroneId=TEXT("uav-01");
    FString GimbalId=TEXT("ptz-01");
    FString DeviceName;
    FString DroneName=TEXT("无人机 1");
    FString GimbalName=TEXT("云台 1");
    FString TrackingTargetId=TEXT("uav-01");
    FString ControlledDroneId=TEXT("uav-01");
    FString ControlledGimbalId=TEXT("ptz-01");
    float InitialYawDegrees=0;
    UPROPERTY() TObjectPtr<AWiseEyeDemo> FleetRoot;
    UPROPERTY() TArray<TObjectPtr<AWiseEyeDemo>> FleetRigs;
    UPROPERTY() TObjectPtr<AActor> TrackingDrone;
    TSharedPtr<FJsonObject> FleetManifest;
    bool InitializeFleet(FString& Error);
    AWiseEyeDemo* FindDevice(const FString& Id) const;
    TArray<TSharedPtr<FJsonValue>> DeviceInventory() const;
    TSharedPtr<FJsonObject> DispatchDevice(const TSharedPtr<FJsonObject>& Request);
    void InitializeFleetChild();
    void UpdateRuntimeStatus();
    TSharedPtr<FJsonObject> RuntimeStatus;
    double RuntimeSampleTime=0;
    int64 RuntimeSampleTick=0;
    TSharedPtr<FJsonObject> EnvironmentState();
    void InitializeEnvironment();
    bool ConfigureEnvironment(bool OverrideTime,float Hour,float Fog,float Rain,FString& Error);
    void UpdateRainVolumes();
    void UpdateEnvironmentViews();
    float EnvironmentNightAmount() const;
    void ResetEnvironment();
    bool ConfigureClouds(float Coverage,FString& Error);
    float EnvironmentClouds=0;
    UPROPERTY() TObjectPtr<UMaterialInterface> EnvironmentCloudMaterial;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> EnvironmentCloudInstance;
    TWeakObjectPtr<AActor> EnvironmentCloudActor;
    TWeakObjectPtr<AActor> EnvironmentCloudAtmosphere;
    bool EnvironmentCloudSunOriginal=false;
    bool EnvironmentInitialized=false,EnvironmentTimeOverride=false;
    float EnvironmentHour=12,EnvironmentFog=0,EnvironmentRain=0;
    TWeakObjectPtr<UDirectionalLightComponent> EnvironmentSun;
    FRotator EnvironmentSunRotation;
    float EnvironmentSunIntensity=0;
    uint8 EnvironmentSunMobility=0;
    TArray<TWeakObjectPtr<USkyLightComponent>> EnvironmentSkyLights;
    TArray<float> EnvironmentSkyIntensities;
    TWeakObjectPtr<UExponentialHeightFogComponent> EnvironmentFogComponent;
    TWeakObjectPtr<AActor> EnvironmentCreatedFog;
    float EnvironmentOriginalFog=0;
    float EnvironmentFogStart=0,EnvironmentFogFalloff=.2f,EnvironmentFogOpacity=1;
    FLinearColor EnvironmentFogColor;
    bool EnvironmentFogVisible=true,EnvironmentFogOwnerHidden=false;
    UPROPERTY() TObjectPtr<UMaterialParameterCollection> EnvironmentWeatherCollection;
    UPROPERTY() TObjectPtr<UMaterialParameterCollectionInstance> EnvironmentWeatherParameters;
    double EnvironmentRainRetryTime=0;
    bool EnvironmentRainDefaultsCaptured=false;
    void EnsureEnvironmentRainResources();
    // A runtime-loaded Blueprint class must remain referenced across AirSim GC.
    UPROPERTY() TObjectPtr<UClass> EnvironmentRainClass;
    float EnvironmentOriginalRain=0,EnvironmentOriginalWeatherEnabled=0;
    TArray<TWeakObjectPtr<AActor>> EnvironmentRainActors;
    TArray<TWeakObjectPtr<USceneComponent>> EnvironmentRainTargets;
    UPROPERTY() TObjectPtr<UMaterialInterface> EnvironmentRainMaterial;
    bool UpdateWorldRain(int32 Index);
    TArray<TWeakObjectPtr<UStaticMeshComponent>> EnvironmentSkyMeshes;
    TArray<bool> EnvironmentSkyMeshVisible;
    virtual ~AWiseEyeDemo();
    virtual void BeginPlay() override;
    void EnsurePlayerInput();
    void LocalToggleFlightMode();
    void LocalTogglePause();
    void LocalReset();
    void PollLocalFlightInput();
    void StepObserver(float DeltaSeconds);
    bool SetObserverMode(const FString& Mode);
    bool SetControlMode(const FString& Mode);
    void CycleControlMode();
    FString ObserverMode = TEXT("overview");
    FString ControlMode = TEXT("observer");
    FVector RemoteObserverInput = FVector::ZeroVector;
    FVector2D RemoteGimbalInput = FVector2D::ZeroVector;
    float ObserverCaptureTime = -1;
    double ObserverInputTime = 0;
    double GimbalInputTime = 0;
    UPROPERTY() TObjectPtr<USceneCaptureComponent2D> ObserverCapture;
    UPROPERTY() TObjectPtr<UTextureRenderTarget2D> ObserverTarget;
    void UpdateObserverCapture();
    bool GetObserverFrame(TArray64<uint8>& Jpeg,int32& Width,int32& Height,int64& Sequence,double& Time) const;
    UPROPERTY() TObjectPtr<ACameraActor> FreeObserver;
    bool BeginPlacement(const FString& DeviceId, const FString& Token, float Clearance, FString& Error);
    void CancelPlacement();
    bool SnapPlacement(const FString& DeviceId, const FString& Token, const FVector& Position, float Clearance, FString& Error);
    void StepPlacement();
    bool TracePlacement(const FVector& Start, const FVector& End, FVector& Point, FString& Error) const;
    void CommitPlacement(const FVector& Surface);
    FVector PlacementAnchor(const FVector& Surface) const;
    bool BuildPlacementPreview(FString& Error);
    bool ApplyDevicePlacement(const FString& DeviceId,const FVector& Position,float Yaw,FString& Error);
    void DestroyPlacementPreview();
    void UpdatePlacementPreview(bool Valid);
    UPROPERTY() TObjectPtr<AActor> PlacementPreview;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> PlacementPreviewMaterial;
    FTransform PlacementPreviewReference;
    FVector PlacementPreviewPosition=FVector::ZeroVector;
    FVector PlacementNudge=FVector::ZeroVector;
    bool PlacementLocked=false;
    TMap<FName,double> PlacementRepeats;
    float PlacementYawDegrees=0,PlacementBaseYaw=0;
    float GimbalPlacementYaw=0;
    FString PlacementAppliedToken,PlacementAppliedDevice;
    bool PlacementActive = false;
    bool PlacementHasResult = false;
    bool PlacementHoverValid = false;
    FString PlacementDevice;
    FString PlacementToken;
    FString PlacementError;
    int32 PlacementSequence = 0;
    FVector PlacementSurface = FVector::ZeroVector;
    FVector PlacementPosition = FVector::ZeroVector;
    float PlacementClearance = 0;
    double PlacementStarted = 0;
    TArray<FString> LocalFlightCommands;
    FVector LocalFlightInput = FVector::ZeroVector;
    float LocalYawInput = 0;
    bool LocalFlightInputDirty = false;
    FString PlaySessionId;
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
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneComponent> OpticalMount;
    // Physical centimetres / pitch-yaw-roll degrees, independent of imported mesh scale.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Calibration") FVector VisibleOffsetCm=FVector(0,-6,0);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Calibration") FVector InfraredOffsetCm=FVector(0,6,0);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Calibration") FRotator VisibleBoresight=FRotator::ZeroRotator;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Calibration") FRotator InfraredBoresight=FRotator(.1,.2,0);
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
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> ThermalDisplayInstance;
    UPROPERTY() TObjectPtr<UTextureRenderTarget2D> InfraredSignalTarget;
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
    // Appearance prototype. Kept separate from physical/radiometric temperature.
    FString ThermalProfile = TEXT("enhanced");
    float ThermalBlurPixels = .8f;
    float ThermalContrast = 1.35f;
    float ThermalBackgroundDetail = .65f;
    int32 ThermalFrameIndex = 0;
    bool ThermalAutoGain=true;
    WiseEyeThermal::DetectorSettings ThermalDetector;
    float ThermalGainResponse=1.f;
    int32 ThermalSamplingScale=1;
    WiseEyeThermal::HeatState ThermalHeat;
    float ThermalPower=0;
    float ThermalNextClassify=0;
    void UpdateThermalState(float Dt);
    void UpdateThermalProjection();
    bool HasReferenceInfrared() const;
    bool HasClassifiedInfrared() const;
    bool HasFacadeInfrared() const;
    bool UsesThermalReadout() const { return HasReferenceInfrared() && (ThermalProfile==TEXT("reference") || ThermalProfile==TEXT("classified") || ThermalProfile==TEXT("facade")); }
    FWiseEyeThermalReadoutState GetThermalReadout() const;
    void SetSignalRecording(bool Enabled);
    bool GetSignalFrame(TArray<float>& Signal,TArray<uint8>& Sky,TArray<uint8>& Target,int64& Sequence) const;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") FVector FlightOrigin = FVector(0,0,4000);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") FVector TargetOffset = FVector::ZeroVector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE", meta=(ClampMin="1")) float FlightRadius = 4000;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE", meta=(ClampMin="1")) float Period = 36;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE", meta=(ClampMin="1")) float YawRate = 45;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE", meta=(ClampMin="1")) float PitchRate = 30;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") float MinPitch = -15;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE") float MaxPitch = 75;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE", meta=(ClampMin="5", ClampMax="120")) float FieldOfView = 45;
    float VisibleFOV = 25;
    float VisibleBlur=.95f,VisibleNoise=.006f,VisibleContrast=.96f,VisibleSaturation=.88f;
    FWiseEyeFocus VisibleFocus,AerialFocus;
    bool SimulationWindowVisible=true,SimulationWindowInitialized=false;
    bool SetSimulationWindowVisible(bool Visible);
    void UpdateSimulationWindow();
    float AerialVisibleBlur=.95f;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> AerialVisibleMaterial;
    void ApplyVisibleFocus(USceneCaptureComponent2D* Lens,FWiseEyeFocus& Focus,bool TrackTarget=false);
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> VisibleInstance;
    float InfraredFOV = 25;
    bool VisibleEnabled = true;
    int64 VisibleCaptureSequence=0;
    bool InfraredEnabled = true;
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
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Rotors", meta=(ClampMin="0", ClampMax="30000")) float RotorRPM = 6000;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Rotors") TArray<TObjectPtr<AActor>> Rotors;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Rotors")         float RotorPhase = 0;
    TArray<float> MotorRPMs = {0,0,0,0};
    TArray<float> MotorPhases = {0,0,0,0};
    TArray<int32> AvataMotorIndices = {0,1,2,3};
    double RotorTelemetryTime = 0;
    bool RotorTelemetryValid = false;
    int64 TickSequence = 0;
    FString PerformanceProfile = TEXT("balanced");
    float VisibleCaptureHz=20, InfraredCaptureHz=15, ObserverCaptureHz=10;
    double NextVisibleCapture=0, NextInfraredCapture=0;
    bool ObserverCaptured=false;
    void SetPerformanceProfile(const FString& Profile);
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Drone") FString DroneModel = TEXT("mavic3");
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="WISEYE|Drone") bool NavigationLightsEnabled = true;
    bool NavigationNight=false, NavigationRedOn=false, NavigationGreenOn=false;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> NavigationLamps;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="WISEYE|Drone") TObjectPtr<UStaticMeshComponent> AlternateDroneMesh;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> FixedwingMesh;
    int32 RuntimeFleetRevision=0;
    bool EditLiveFleet(const TSharedPtr<FJsonObject>& Args,FString& Error);
    AWiseEyeDemo* SpawnLiveDevice(const TSharedPtr<FJsonObject>& Item,FString& Error);
    void RemoveLiveDevice(const FString& Id);
    bool FixedwingActive=false;
    float FixedwingSpeed=12.f,FixedwingActualSpeed=0,FixedwingYaw=0;
    float FixedwingHoldAltitude=0;
    TUniquePtr<FWiseEyeFixedwingEngine> FixedwingEngine;
    FVector FixedwingInput=FVector::ZeroVector;
    double FixedwingInputAt=0;
    TArray<FVector> FixedwingRoute;
    int32 FixedwingWaypoint=0;
    bool FixedwingRepeat=false;
    FString FixedwingRouteStatus=TEXT("idle"),FixedwingError;
    void InitializeFixedwingVisual();
    void StepFixedwing(float Dt);
    bool ControlFixedwing(const TSharedPtr<FJsonObject>& Args,FString& Error);
    TSharedPtr<FJsonObject> FixedwingState() const;
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
    int64 LidarScanSequence=0;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Lidar") float LidarNearestRangeMeters = 0;
    UPROPERTY(BlueprintReadOnly, Category="WISEYE|Lidar") FString LastLidarExportPath;
    TArray<float> LastLidarRangesMeters;
    TArray<FVector> LastLidarPointsWorldCm;
    UFUNCTION(BlueprintCallable, Category="WISEYE") void TogglePause();
    UFUNCTION(BlueprintCallable, Category="WISEYE") void ResetSimulation();
    UFUNCTION(BlueprintCallable, Category="WISEYE") void SwitchView();
    UFUNCTION(BlueprintCallable, Category="WISEYE") void ExportFrame();
    void ExportSensorFrame(bool bInfrared);
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
    void RefreshEventSensor();
    TSharedPtr<FJsonObject> EventSensorState() const;
    bool EventEnabled=true;
    float EventFOV=25,EventSampleHz=15,EventOn=.2f,EventOff=.2f;
    int64 EventRefractoryUs=100;
    FVector EventOffsetCm=FVector(0,0,2);
    FRotator EventBoresight=FRotator::ZeroRotator;
    UPROPERTY() TObjectPtr<USceneCaptureComponent2D> EventCapture;
    UPROPERTY() TObjectPtr<UTextureRenderTarget2D> EventTarget;
    double NextEventCapture=0;
    FString LastEventExportPath;
    /** Normalized forward/right/up and yaw inputs; keyboard input is added at runtime. */
    UFUNCTION(BlueprintCallable, Category="WISEYE") void SetManualInput(float Forward, float Right, float Up, float Yaw);
    bool SetDroneModel(const FString& ModelId, FString& Error);
    TSharedPtr<FJsonObject> AerialState() const;
    bool ConfigureAerial(const TSharedPtr<FJsonObject>& Args,FString& Error);
    bool GetAerialFrame(TArray64<uint8>& Jpeg,int32& Width,int32& Height,int64& Sequence,double& Time,bool IR=false);
    void UpdateAerial();
    UPROPERTY() TObjectPtr<USceneCaptureComponent2D> AerialCapture;
    UPROPERTY() TObjectPtr<UTextureRenderTarget2D> AerialTarget;
    UPROPERTY() TObjectPtr<ACameraActor> AerialViewer;
    void ReleaseAerial();
    bool AerialEnabled=true,AerialStabilized=true;
    float AerialPitch=-60,AerialYaw=0,AerialFOV=65,AerialHz=15;
    double AerialDemandUntil=0,AerialNext=0;
    FWiseEyeStreamManager* AerialStream=nullptr;
    bool AerialIREnabled=true,AerialIRBlackHot=false;
    float AerialIRFOV=65,AerialIRBlur=.8f,AerialIRNoise=.008f,AerialIRHz=15;
    double AerialIRDemandUntil=0,AerialIRNext=0;
    UPROPERTY() TObjectPtr<USceneCaptureComponent2D> AerialIRCapture;
    UPROPERTY() TObjectPtr<UTextureRenderTarget2D> AerialIRSignal;
    UPROPERTY() TObjectPtr<UTextureRenderTarget2D> AerialIRTarget;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> AerialIRMaterial;
    FWiseEyeStreamManager* AerialIRStream=nullptr;
    TMap<double,TSharedPtr<FJsonObject>> AerialContexts[2];
    void RecordAerialContext(bool IR);
    void InitializeObservation();
    void UpdatePopulation();
    TSharedPtr<FJsonObject> PopulationState() const;
    TSharedPtr<FJsonObject> PopulationAgents(const FString& FromCamera=TEXT("")) const;
    bool ConfigurePopulation(const TSharedPtr<FJsonObject>& Args,FString& Error);
    bool SaveObservation(FString& Error) const;
    bool PopulationVehicles=true,PopulationPedestrians=true;
    float PopulationVehicleDensity=.25f,PopulationPedestrianDensity=.25f;
    double PopulationNextScan=0,PopulationApplyAt=0,PopulationWarmup=0;
    UPROPERTY() TArray<TObjectPtr<UWiseEyePopulationWatch>> PopulationWatches;
    TMap<TWeakObjectPtr<UStaticMesh>,uint8> PopulationThermalMeshes;
    double PopulationThermalNext=0;
    int32 PopulationThermalComponents=0;
    int32 PopulationThermalPeople=0,PopulationThermalVehicles=0;
    bool GetStreamFrame(bool bInfrared, TArray64<uint8>& Jpeg, int32& Width, int32& Height,
                        int64& StreamFrameNumber, double& StreamSimulationTime) const;
    void GetStreamStatistics(bool bInfrared, int64& Sequence, int64& Completed, double& CaptureTime) const;
private:
    void StepSimulation(float DeltaSeconds, bool Snap);
    FVector FlightOffset(float Time) const;
    void StepManualFlight(float DeltaSeconds);
    void StepGimbal(float DeltaSeconds, bool Snap);
    void StepRotors(float DeltaSeconds);
    void StepNavigationLights();
    void StepProjectAirSim(float DeltaSeconds);
    bool TryBindDynamicsSource();
    void SetVisualAssemblyCollision(bool Enabled);
    void UpdateDroneView();
    void InitializeSensors();
    void UpdateSensorTransforms();
    void InitializeDroneModels();
    void ConfigureThermalActors();
    void WriteTelemetry();
    FRotator DroneInitialRotation;
    FVector InitialFlightOrigin;
    FVector ManualInput = FVector::ZeroVector;
    float ManualYawInput = 0;
    TArray<FQuat> RotorInitialRotations;
    UPROPERTY() TArray<TObjectPtr<UPrimitiveComponent>> MavicVisualComponents;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="WISEYE|Drone", meta=(AllowPrivateAccess="true"))
    TArray<TObjectPtr<UStaticMeshComponent>> AvataRotors;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> AvataRotorBlurs;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> MavicRotorBlurs;
    float TelemetryClock = 0;
    float LidarClock = 0;
    FTransform LastLidarPose;
    double LastLidarCaptureTime=0;
    int32 FrameNumber = 0;
    int32 ViewMode = 0;
    FString OutputDirectory;
    FWiseEyeBridge* Bridge = nullptr;
    FWiseEyeStreamManager* StreamManager = nullptr;
    FWiseEyeGTSettings GTSettings;
    UPROPERTY() TArray<TObjectPtr<USceneCaptureComponent2D>> GTDepthCaptures;
    UPROPERTY() TArray<TObjectPtr<UTextureRenderTarget2D>> GTDepthTargets;
    FString GTSampleTokens[2];
    bool GTPairPending=false;
    double GTSampleRequestedAt[2]={-100,-100};
    bool PlayerInputBound = false;
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
