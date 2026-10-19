#include "WiseEyeStreaming.h"

#include "Async/Async.h"
#include "Engine/TextureRenderTarget2D.h"
#include "HAL/PlatformProcess.h"
#include "IImageWrapper.h"
#include "IImageWrapperModule.h"
#include "Modules/ModuleManager.h"
#include "RenderResource.h"
#include "RenderingThread.h"
#include "RHIGPUReadback.h"
#include <atomic>

struct FWiseEyeStreamManager::FChannel
{
    explicit FChannel(double InInterval, int32 InMaxInFlight, const TCHAR* InName)
        : Interval(InInterval), MaxInFlight(InMaxInFlight), Name(InName) {}
    double Interval;
    int32 MaxInFlight;
    FString Name;
    double LastQueued = -1;
    std::atomic<int32> InFlight{0};
    int64 QueuedFrameNumber = 0;
    mutable FCriticalSection CacheLock;
    TArray64<uint8> Jpeg;
    int32 Width = 0;
    int32 Height = 0;
    int64 FrameNumber = 0;
    double SimulationTime = 0;
};

FWiseEyeStreamManager::FWiseEyeStreamManager()
{
    VisibleChannel = MakeShared<FChannel, ESPMode::ThreadSafe>(1.0 / 30.0, 8, TEXT("WISEYE_CH1_Readback"));
    InfraredChannel = MakeShared<FChannel, ESPMode::ThreadSafe>(1.0 / 25.0, 6, TEXT("WISEYE_CH2_Readback"));
    FModuleManager::LoadModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper"));
}

FWiseEyeStreamManager::~FWiseEyeStreamManager() = default;

void FWiseEyeStreamManager::Tick(UTextureRenderTarget2D* Visible, UTextureRenderTarget2D* Infrared,
                                 double SimulationTime)
{
    const double Now = FPlatformTime::Seconds();
    auto Schedule = [Now, SimulationTime](const TSharedPtr<FChannel, ESPMode::ThreadSafe>& Channel,
                                          UTextureRenderTarget2D* Target)
    {
        if (!Target || (Channel->LastQueued >= 0 && Now - Channel->LastQueued < Channel->Interval)) return;
        if (Channel->InFlight.load(std::memory_order_relaxed) >= Channel->MaxInFlight) return;
        Channel->InFlight.fetch_add(1,std::memory_order_relaxed);
        Channel->LastQueued = Now;
        Queue(Channel, Target, SimulationTime, ++Channel->QueuedFrameNumber);
    };
    Schedule(VisibleChannel, Visible);
    Schedule(InfraredChannel, Infrared);
}

void FWiseEyeStreamManager::Queue(const TSharedPtr<FChannel, ESPMode::ThreadSafe>& Channel,
                                  UTextureRenderTarget2D* Target, double SimulationTime, int64 Sequence)
{
    FTextureRenderTargetResource* Resource = Target->GameThread_GetRenderTargetResource();
    if (!Resource)
    {
        Channel->InFlight.fetch_sub(1,std::memory_order_relaxed);
        return;
    }
    const int32 Width = Target->SizeX;
    const int32 Height = Target->SizeY;
    const FString ReadbackName = Channel->Name;
    ENQUEUE_RENDER_COMMAND(WiseEyeAsyncReadback)(
        [Channel, Resource, Width, Height, SimulationTime, Sequence, ReadbackName](FRHICommandListImmediate& RHICmdList)
        {
            FRHITexture* Texture = Resource->GetRenderTargetTexture();
            if (!Texture)
            {
                Channel->InFlight.fetch_sub(1,std::memory_order_relaxed);
                return;
            }
            auto Readback = MakeShared<FRHIGPUTextureReadback, ESPMode::ThreadSafe>(*ReadbackName);
            Readback->EnqueueCopy(RHICmdList, Texture, FIntVector::ZeroValue, 0, FIntVector(Width, Height, 1));
            Async(EAsyncExecution::ThreadPool, [Channel, Readback, Width, Height, SimulationTime, Sequence]
            {
                while (!Readback->IsReady()) FPlatformProcess::SleepNoStats(0.001f);
                AsyncTask(ENamedThreads::ActualRenderingThread,
                    [Channel, Readback, Width, Height, SimulationTime, Sequence]
                    {
                        int32 RowPitch = 0;
                        int32 BufferHeight = 0;
                        const void* Data = Readback->Lock(RowPitch, &BufferHeight);
                        if (!Data || RowPitch < Width || BufferHeight < Height)
                        {
                            if (Data) Readback->Unlock();
                            Channel->InFlight.fetch_sub(1,std::memory_order_relaxed);
                            return;
                        }
                        TArray<FColor> Pixels;
                        Pixels.SetNumUninitialized(Width * Height);
                        const uint8* Source = static_cast<const uint8*>(Data);
                        for (int32 Y = 0; Y < Height; ++Y)
                            FMemory::Memcpy(Pixels.GetData() + Y * Width, Source + Y * RowPitch * sizeof(FColor),
                                            Width * sizeof(FColor));
                        Readback->Unlock();
                        Async(EAsyncExecution::ThreadPool,
                            [Channel, Pixels = MoveTemp(Pixels), Width, Height, SimulationTime, Sequence]() mutable
                            {
                                IImageWrapperModule& Module = FModuleManager::GetModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper"));
                                TSharedPtr<IImageWrapper> Wrapper = Module.CreateImageWrapper(EImageFormat::JPEG);
                                TArray64<uint8> Encoded;
                                if (Wrapper.IsValid() && Wrapper->SetRaw(Pixels.GetData(), Pixels.Num() * sizeof(FColor),
                                        Width, Height, ERGBFormat::BGRA, 8))
                                    Encoded = Wrapper->GetCompressed(60);
                                if (!Encoded.IsEmpty())
                                {
                                    FScopeLock Lock(&Channel->CacheLock);
                                    if (Sequence > Channel->FrameNumber)
                                    {
                                        Channel->Jpeg = MoveTemp(Encoded);
                                        Channel->Width = Width;
                                        Channel->Height = Height;
                                        Channel->SimulationTime = SimulationTime;
                                        Channel->FrameNumber = Sequence;
                                    }
                                }
                                Channel->InFlight.fetch_sub(1,std::memory_order_relaxed);
                            });
                    });
            });
        });
}

bool FWiseEyeStreamManager::GetFrame(bool bInfrared, TArray64<uint8>& Jpeg, int32& Width, int32& Height,
                                     int64& FrameNumber, double& SimulationTime) const
{
    const auto& Channel = bInfrared ? InfraredChannel : VisibleChannel;
    FScopeLock Lock(&Channel->CacheLock);
    if (Channel->Jpeg.IsEmpty()) return false;
    Jpeg = Channel->Jpeg;
    Width = Channel->Width;
    Height = Channel->Height;
    FrameNumber = Channel->FrameNumber;
    SimulationTime = Channel->SimulationTime;
    return true;
}
