#pragma once

#include "CoreMinimal.h"
#include "WiseEyeThermalMath.h"

class UTextureRenderTarget2D;
struct FWiseEyeGTSnapshot;
class FWiseEyeEventCamera;
struct FWiseEyeThermalReadoutState { float Low=0,High=1,ProcessingMs=0;int64 Sequence=0;TArray<int32> ClassPixels;int32 TargetPixels=0,MotorRegionPixels=0,SkyPixels=0; };

/** Asynchronous GPU readback and JPEG cache for the two RTSP channels. */
class FWiseEyeStreamManager
{
public:
    FWiseEyeStreamManager();
    ~FWiseEyeStreamManager();
    void Tick(UTextureRenderTarget2D* Visible, UTextureRenderTarget2D* Infrared, double SimulationTime, UTextureRenderTarget2D* Observer=nullptr,UTextureRenderTarget2D* InfraredDisplay=nullptr,TSharedPtr<FWiseEyeGTSnapshot> VisibleGT=nullptr,TSharedPtr<FWiseEyeGTSnapshot> InfraredGT=nullptr,UTextureRenderTarget2D* EventTarget=nullptr,double EventTime=-1);
    void ConfigureEvent(bool Enabled,float On,float Off,int64 Refractory);
    TSharedPtr<FWiseEyeEventCamera,ESPMode::ThreadSafe> EventCamera;
    bool CanQueueSample(bool Infrared) const;
    bool GetSample(bool Infrared,FString& Metadata,TArray64<uint8>& Image) const;
    void ConfigureThermalReadout(bool Reference,bool AutoGain,bool BlackHot,float Response,float Contrast,float Blur,bool Classified,const WiseEyeThermal::DetectorSettings& Detector);
    void SetEnabled(bool Visible,bool Infrared);
    void SetSignalRecording(bool Enabled);
    bool GetSignalFrame(TArray<float>& Signal,TArray<uint8>& Sky,TArray<uint8>& Target,int64& Sequence) const;
    FWiseEyeThermalReadoutState ThermalReadoutState() const;
    bool GetObserverFrame(TArray64<uint8>& Jpeg,int32& Width,int32& Height,int64& Sequence,double& Time) const;
    void GetStatistics(bool bInfrared, int64& Sequence, int64& Completed, double& CaptureTime) const;
    bool GetFrame(bool bInfrared, TArray64<uint8>& Jpeg, int32& Width, int32& Height,
                  int64& FrameNumber, double& SimulationTime) const;
private:
    struct FChannel;
    TSharedPtr<FChannel, ESPMode::ThreadSafe> VisibleChannel;
    TSharedPtr<FChannel, ESPMode::ThreadSafe> InfraredChannel;
    TSharedPtr<FChannel, ESPMode::ThreadSafe> ObserverChannel;
    TSharedPtr<FChannel, ESPMode::ThreadSafe> EventChannel;
    static void Queue(const TSharedPtr<FChannel, ESPMode::ThreadSafe>& Channel,
                      UTextureRenderTarget2D* Target, double SimulationTime, int64 Sequence,UTextureRenderTarget2D* Display=nullptr,TSharedPtr<FWiseEyeGTSnapshot> GT=nullptr);
};
