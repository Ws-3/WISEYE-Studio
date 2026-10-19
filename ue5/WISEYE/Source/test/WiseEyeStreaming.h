#pragma once

#include "CoreMinimal.h"

class UTextureRenderTarget2D;

/** Asynchronous GPU readback and JPEG cache for the two RTSP channels. */
class FWiseEyeStreamManager
{
public:
    FWiseEyeStreamManager();
    ~FWiseEyeStreamManager();
    void Tick(UTextureRenderTarget2D* Visible, UTextureRenderTarget2D* Infrared, double SimulationTime);
    bool GetFrame(bool bInfrared, TArray64<uint8>& Jpeg, int32& Width, int32& Height,
                  int64& FrameNumber, double& SimulationTime) const;
private:
    struct FChannel;
    TSharedPtr<FChannel, ESPMode::ThreadSafe> VisibleChannel;
    TSharedPtr<FChannel, ESPMode::ThreadSafe> InfraredChannel;
    static void Queue(const TSharedPtr<FChannel, ESPMode::ThreadSafe>& Channel,
                      UTextureRenderTarget2D* Target, double SimulationTime, int64 Sequence);
};
