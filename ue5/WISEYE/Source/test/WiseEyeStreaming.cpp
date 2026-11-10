#include "WiseEyeStreaming.h"
#include "WiseEyeGroundTruth.h"
#include "WiseEyeEventCamera.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "WiseEyeThermalMath.h"
#include "Math/Float16Color.h"

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
    TSharedPtr<FWiseEyeEventCamera,ESPMode::ThreadSafe> Events;
    struct FReadout { WiseEyeThermal::DetectorSettings Detector;bool Reference=false,Auto=true,Black=false,Classified=false;float Response=1,Contrast=1,Blur=.8f;int64 Revision=0; } Readout;
    WiseEyeThermal::Exposure Exposure;
    FWiseEyeThermalReadoutState ThermalStats;
    explicit FChannel(double InInterval, int32 InMaxInFlight, const TCHAR* InName)
        : Interval(InInterval), MaxInFlight(InMaxInFlight), Name(InName) {}
    double Interval;
    int32 MaxInFlight;
    FString Name;
    double LastQueued = -1;
    std::atomic<int32> InFlight{0};
    std::atomic<bool> Cancelled{false};
    std::atomic<bool> Enabled{true};
    std::atomic<bool> RecordSignal{false};
    TArray<float> RecordedSignal;TArray<uint8> RecordedSky,RecordedTarget;int64 RecordedSequence=0;
    int64 QueuedFrameNumber = 0;
    mutable FCriticalSection CacheLock;
    TArray64<uint8> Jpeg;
    int32 Width = 0;
    int32 Height = 0;
    int64 FrameNumber = 0;
    int64 CompletedFrames = 0;
    double CaptureTime = 0;
    double SimulationTime = 0;
    FString SampleMetadata;TArray64<uint8> SampleImage;
    int64 SampleSequence=0;
};

FWiseEyeStreamManager::FWiseEyeStreamManager()
{
    VisibleChannel = MakeShared<FChannel, ESPMode::ThreadSafe>(0.0, 2, TEXT("WISEYE_CH1_Readback"));
    InfraredChannel = MakeShared<FChannel, ESPMode::ThreadSafe>(0.0, 2, TEXT("WISEYE_CH2_Readback"));
    ObserverChannel = MakeShared<FChannel, ESPMode::ThreadSafe>(0.0, 2,TEXT("WISEYE_OBS_Readback"));
    EventChannel=MakeShared<FChannel,ESPMode::ThreadSafe>(0.,2,TEXT("WISEYE_EVENT_Readback"));EventChannel->Enabled=false;
    EventCamera=MakeShared<FWiseEyeEventCamera,ESPMode::ThreadSafe>();EventChannel->Events=EventCamera;
    FModuleManager::LoadModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper"));
}

FWiseEyeStreamManager::~FWiseEyeStreamManager() { VisibleChannel->Cancelled=true; InfraredChannel->Cancelled=true; ObserverChannel->Cancelled=true;EventChannel->Cancelled=true; }

void FWiseEyeStreamManager::ConfigureEvent(bool Enabled,float On,float Off,int64 Refractory) {
    EventChannel->Enabled=Enabled;EventCamera->Configure(Enabled,On,Off,Refractory);
}

void FWiseEyeStreamManager::SetEnabled(bool Visible,bool Infrared)
{
    auto Set=[](const TSharedPtr<FChannel,ESPMode::ThreadSafe>& C,bool Enabled) {
        if (C->Enabled.exchange(Enabled)==Enabled) return;
        FScopeLock Lock(&C->CacheLock);
        ++C->Readout.Revision;C->SampleMetadata.Empty();C->SampleImage.Reset();C->Jpeg.Reset();C->RecordedSignal.Reset();C->RecordedSky.Reset();C->RecordedTarget.Reset();C->ThermalStats={};if (C->Readout.Detector.Mode!=1) C->Exposure={};
        C->LastQueued=-1;
    };
    Set(VisibleChannel,Visible);Set(InfraredChannel,Infrared);
}

void FWiseEyeStreamManager::Tick(UTextureRenderTarget2D* Visible, UTextureRenderTarget2D* Infrared,
                                 double SimulationTime,UTextureRenderTarget2D* Observer,UTextureRenderTarget2D* InfraredDisplay,TSharedPtr<FWiseEyeGTSnapshot> VisibleGT,TSharedPtr<FWiseEyeGTSnapshot> InfraredGT,UTextureRenderTarget2D* EventTarget,double EventTime)
{
    const double Now = FPlatformTime::Seconds();
    auto Schedule = [Now, SimulationTime](const TSharedPtr<FChannel, ESPMode::ThreadSafe>& Channel,
                                          UTextureRenderTarget2D* Target,UTextureRenderTarget2D* Display=nullptr,TSharedPtr<FWiseEyeGTSnapshot> GT=nullptr,double DataTime=-1)
    {
        if (!Channel->Enabled || !Target || (Channel->LastQueued >= 0 && Now - Channel->LastQueued < Channel->Interval)) return;
        if (Channel->InFlight.load(std::memory_order_relaxed) >= Channel->MaxInFlight) return;
        Channel->InFlight.fetch_add(1,std::memory_order_relaxed);
        Channel->LastQueued = Now;
        Queue(Channel, Target, DataTime>=0?DataTime:SimulationTime, ++Channel->QueuedFrameNumber,Display,GT);
    };
    Schedule(VisibleChannel, Visible,nullptr,VisibleGT);
    Schedule(InfraredChannel, Infrared,InfraredDisplay,InfraredGT);
    Schedule(ObserverChannel, Observer);
    Schedule(EventChannel,EventTarget,nullptr,nullptr,EventTime);
}

void FWiseEyeStreamManager::Queue(const TSharedPtr<FChannel, ESPMode::ThreadSafe>& Channel,
                                  UTextureRenderTarget2D* Target, double SimulationTime, int64 Sequence,UTextureRenderTarget2D* Display,TSharedPtr<FWiseEyeGTSnapshot> GT)
{
    FTextureRenderTargetResource* Resource = Target->GameThread_GetRenderTargetResource();
    if (!Resource)
    {
        Channel->InFlight.fetch_sub(1,std::memory_order_relaxed);
        return;
    }
    const int32 Width = Target->SizeX;
    const int32 Height = Target->SizeY;
    const double CaptureTime = FPlatformTime::Seconds();
    const FString ReadbackName = Channel->Name;
    auto* DisplayResource=Display?Display->GameThread_GetRenderTargetResource():nullptr;
    FChannel::FReadout Settings;
    { FScopeLock Lock(&Channel->CacheLock);Settings=Channel->Readout; }
    if (Channel->Events) Settings.Revision=Channel->Events->Revision();
    ENQUEUE_RENDER_COMMAND(WiseEyeAsyncReadback)(
        [Channel, Resource, DisplayResource,Settings,Width, Height, SimulationTime, Sequence, ReadbackName, CaptureTime,GT](FRHICommandListImmediate& RHICmdList)
        {
            if (!Channel->Enabled || Channel->Cancelled) { Channel->InFlight.fetch_sub(1);return; }
            FRHITexture* Texture = Resource->GetRenderTargetTexture();
            if (!Texture)
            {
                Channel->InFlight.fetch_sub(1,std::memory_order_relaxed);
                return;
            }
            auto Readback = MakeShared<FRHIGPUTextureReadback, ESPMode::ThreadSafe>(*ReadbackName);
            FTextureRHIRef DisplayTexture=DisplayResource?DisplayResource->GetRenderTargetTexture():nullptr;
            Readback->EnqueueCopy(RHICmdList, Texture, FIntVector::ZeroValue, 0, FIntVector(Width, Height, 1));
            TArray<TSharedPtr<FRHIGPUTextureReadback,ESPMode::ThreadSafe>> GTReadbacks;
            if (GT) for (auto* R:GT->Resources) {
                auto B=MakeShared<FRHIGPUTextureReadback,ESPMode::ThreadSafe>(TEXT("WISEYE_GT_Depth"));
                if (!R || !R->GetRenderTargetTexture()) { GT->Error=TEXT("Missing depth texture");break; }
                B->EnqueueCopy(RHICmdList,R->GetRenderTargetTexture(),FIntVector::ZeroValue,0,FIntVector(GT->Width,GT->Height,1));GTReadbacks.Add(B);
            }
            Async(EAsyncExecution::ThreadPool, [Channel, Readback, DisplayTexture,Settings,Width, Height, SimulationTime, Sequence, CaptureTime,GT,GTReadbacks]
            {
                while (!Readback->IsReady() || GTReadbacks.ContainsByPredicate([](const auto& B){return !B->IsReady();})) {
                    if (Channel->Cancelled || FPlatformTime::Seconds()-CaptureTime>3) {
                        // Release the RHI resource on its owning thread, never lock an unready buffer.
                        AsyncTask(ENamedThreads::ActualRenderingThread,[Channel,Readback,GTReadbacks] { Channel->InFlight.fetch_sub(1); });
                        return;
                    }
                    FPlatformProcess::SleepNoStats(0.001f);
                }
                AsyncTask(ENamedThreads::ActualRenderingThread,
                    [Channel, Readback, DisplayTexture,Settings,Width, Height, SimulationTime, Sequence, CaptureTime,GT,GTReadbacks]
                    {
                        { FScopeLock Guard(&Channel->CacheLock);
                          if (!Channel->Enabled || Channel->Cancelled || (!Channel->Events && Settings.Revision!=Channel->Readout.Revision)) { Channel->InFlight.fetch_sub(1);return; } }
                        if (GT) for (auto& B:GTReadbacks) {
                            int32 Pitch=0,Rows=0;const void* Depth=B->Lock(Pitch,&Rows);
                            TArray<float> Plane;
                            if (Depth && Pitch>=GT->Width && Rows>=GT->Height) {
                                Plane.SetNumUninitialized(GT->Width*GT->Height);
                                for (int32 Y=0;Y<GT->Height;++Y) FMemory::Memcpy(Plane.GetData()+Y*GT->Width,static_cast<const float*>(Depth)+Y*Pitch,GT->Width*sizeof(float));
                            } else GT->Error=TEXT("Depth readback failed");
                            if (Depth) B->Unlock();GT->Depths.Add(MoveTemp(Plane));
                        }
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
                        TArray<float> Signal;TArray<uint8> SkyMask,TargetMask;
                        TArray<int32> ClassPixels;ClassPixels.Init(0,7);int32 TargetPixels=0,MotorRegionPixels=0,SkyPixels=0;
                        const int32 OutWidth=Settings.Reference?640:Width,OutHeight=Settings.Reference?512:Height;
                        Pixels.SetNumUninitialized(OutWidth * OutHeight);
                        const uint8* Source = static_cast<const uint8*>(Data);
                        if (Channel->Events) {
                            Signal.SetNumUninitialized(Width*Height);
                            for (int32 Y=0;Y<Height;++Y) {
                                const auto* Row=reinterpret_cast<const FFloat16Color*>(Source)+Y*RowPitch;
                                for (int32 X=0;X<Width;++X) Signal[Y*Width+X]=.2126f*Row[X].R.GetFloat()+.7152f*Row[X].G.GetFloat()+.0722f*Row[X].B.GetFloat();
                            }
                        } else if (Settings.Reference) {
                            const int32 Scale=Width/OutWidth;
                            Signal.SetNumZeroed(OutWidth*OutHeight);SkyMask.SetNumZeroed(OutWidth*OutHeight);TargetMask.SetNumZeroed(OutWidth*OutHeight);
                            for (int32 Y=0;Y<OutHeight;++Y) for (int32 X=0;X<OutWidth;++X) {
                                float Sum=0;WiseEyeThermal::PixelLabels Labels;
                                for (int32 DY=0;DY<Scale;++DY) {
                                    const auto* Row=reinterpret_cast<const FFloat16Color*>(Source)+(Y*Scale+DY)*RowPitch;
                                    for (int32 DX=0;DX<Scale;++DX) {
                                        Sum+=Row[X*Scale+DX].R.GetFloat();
                                        if (Settings.Classified) Labels.Add(Row[X*Scale+DX].B.GetFloat());
                                    }
                                }
                                Signal[Y*OutWidth+X]=Sum/(Scale*Scale);
                                if (Settings.Classified) {
                                    const auto& Label=reinterpret_cast<const FFloat16Color*>(Source)[Y*Scale*RowPitch+X*Scale];
                                    SkyMask[Y*OutWidth+X]=Labels.Sky;
                                    TargetMask[Y*OutWidth+X]=Labels.Target?1:Labels.Population?2:0;SkyPixels+=SkyMask[Y*OutWidth+X];
                                    ++ClassPixels[FMath::Clamp(FMath::RoundToInt(Label.G.GetFloat()*8),0,6)];
                                    if (Labels.Target) ++TargetPixels;
                                    if (Labels.Motor) ++MotorRegionPixels;
                                }
                            }
                        } else for (int32 Y = 0; Y < Height; ++Y)
                            FMemory::Memcpy(Pixels.GetData() + Y * Width, Source + Y * RowPitch * sizeof(FColor),Width * sizeof(FColor));
                        Readback->Unlock();
                        Async(EAsyncExecution::ThreadPool,
                            [Channel, Pixels = MoveTemp(Pixels),Signal=MoveTemp(Signal),SkyMask=MoveTemp(SkyMask),TargetMask=MoveTemp(TargetMask),ClassPixels=MoveTemp(ClassPixels),TargetPixels,MotorRegionPixels,SkyPixels,DisplayTexture,Settings,Width=OutWidth,Height=OutHeight,SimulationTime, Sequence, CaptureTime,GT]() mutable
                            {
                                if (!Channel->Enabled || Channel->Cancelled) { Channel->InFlight.fetch_sub(1);return; }
                                if (Channel->Events) {
                                    Channel->Events->Process(Signal,Width,Height,SimulationTime,Sequence,Settings.Revision);
                                    Channel->InFlight.fetch_sub(1);return;
                                }
                                TArray<float> RawSignal;
                                if (Settings.Reference && Channel->RecordSignal) RawSignal=Signal;
                                if (Settings.Reference) {
                                    const double Begin=FPlatformTime::Seconds();
                                    TArray<float> Scratch;Scratch.SetNumUninitialized(Signal.Num());
                                    if (Settings.Detector.Denoise>0 && Settings.Classified) {
                                        WiseEyeThermal::SmoothSky(Signal.GetData(),Scratch.GetData(),SkyMask.GetData(),Width,Height,Settings.Detector.Denoise);
                                    }
                                    if (Settings.Blur>.01f) {
                                        WiseEyeThermal::OpticalBlur(Signal.GetData(),Scratch.GetData(),Width,Height,Settings.Blur);
                                    }
                                    FScopeLock Lock(&Channel->CacheLock);
                                    if (Settings.Revision!=Channel->Readout.Revision || Sequence<=Channel->ThermalStats.Sequence || Channel->Cancelled) { Channel->InFlight.fetch_sub(1);return; }
                                    if (Settings.Detector.SensorNoise && Settings.Detector.Noise>0)
                                        for (int I=0;I<Signal.Num();++I) Signal[I]=FMath::Clamp(Signal[I]+Settings.Detector.Noise*WiseEyeThermal::ReadNoise(Settings.Detector.Seed,Sequence,I),0.f,1.f);
                                    TArray<uint8> GainExclude;
                                    if (Settings.Classified && Settings.Detector.Stable) {
                                        GainExclude.SetNumUninitialized(Signal.Num());
                                        for (int I=0;I<Signal.Num();++I) GainExclude[I]=TargetMask[I] || SkyMask[I];
                                    }
                                    Channel->Exposure.Apply(Signal.GetData(),Signal.Num(),CaptureTime,Settings.Response,Settings.Detector,
                                        !GainExclude.IsEmpty()?GainExclude.GetData():Settings.Classified?TargetMask.GetData():nullptr);
                                    for (int I=0;I<Signal.Num();++I) {
                                        float Value=Settings.Classified?Channel->Exposure.DisplaySoft(Signal[I],Settings.Contrast,Settings.Detector.Facade?false:Settings.Black,Settings.Detector.Brightness):Channel->Exposure.Display(Signal[I],Settings.Contrast,Settings.Black,Settings.Detector.Brightness);
                                        if (Settings.Detector.Facade) {
                                            Value=WiseEyeThermal::FacadeDisplayValue(Value,SkyMask[I]!=0,TargetMask[I]==1,Signal[I],Settings.Detector.BackgroundMid,Settings.Detector.BackgroundSlope);
                                            if (Settings.Black) Value=1.f-Value;
                                        }
                                        uint8 V=uint8(FMath::RoundToInt(255.f*Value));Pixels[I]=FColor(V,V,V,255);
                                    }
                                    if (Settings.Detector.Facade)
                                        WiseEyeThermal::SoftenBackgroundDisplay(reinterpret_cast<uint8_t*>(Pixels.GetData()),Scratch.GetData(),TargetMask.GetData(),Width,Height);
                                    Channel->ThermalStats={Channel->Exposure.Low,Channel->Exposure.High,float((FPlatformTime::Seconds()-Begin)*1000),Sequence};
                                    Channel->ThermalStats.ClassPixels=MoveTemp(ClassPixels);Channel->ThermalStats.TargetPixels=TargetPixels;
                                    Channel->ThermalStats.MotorRegionPixels=MotorRegionPixels;Channel->ThermalStats.SkyPixels=SkyPixels;
                                }
                                IImageWrapperModule& Module = FModuleManager::GetModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper"));
                                TSharedPtr<IImageWrapper> Wrapper = Module.CreateImageWrapper(EImageFormat::JPEG);
                                TArray64<uint8> Encoded;
                                if (Wrapper.IsValid() && Wrapper->SetRaw(Pixels.GetData(), Pixels.Num() * sizeof(FColor),
                                        Width, Height, ERGBFormat::BGRA, 8))
                                    Encoded = Wrapper->GetCompressed(90);
                                FString SampleMetadata;
                                if (GT) FJsonSerializer::Serialize(GT->Annotate(Sequence,SimulationTime).ToSharedRef(),TJsonWriterFactory<>::Create(&SampleMetadata));
                                if (!Encoded.IsEmpty())
                                {
                                    FScopeLock Lock(&Channel->CacheLock);
                                    if (GT && !Channel->Cancelled && Channel->Enabled && Settings.Revision==Channel->Readout.Revision && Sequence>Channel->SampleSequence) {
                                        Channel->SampleMetadata=MoveTemp(SampleMetadata);Channel->SampleImage=Encoded;Channel->SampleSequence=Sequence;
                                    }
                                    if (!Channel->Cancelled && Channel->Enabled && Sequence > Channel->FrameNumber)
                                    {
                                        if (Settings.Revision!=Channel->Readout.Revision) { Channel->InFlight.fetch_sub(1);return; }
                                        if (Settings.Reference && DisplayTexture) {
                                            ENQUEUE_RENDER_COMMAND(WiseEyeThermalDisplay)([Channel,DisplayTexture,Pixels,Width,Height,Settings](FRHICommandListImmediate& Cmd) {
                                                FScopeLock Guard(&Channel->CacheLock);
                                                if (Channel->Cancelled || !Channel->Enabled || Settings.Revision!=Channel->Readout.Revision) return;
                                                Cmd.UpdateTexture2D(DisplayTexture,0,FUpdateTextureRegion2D(0,0,0,0,Width,Height),Width*sizeof(FColor),reinterpret_cast<const uint8*>(Pixels.GetData()));
                                            });
                                        }
                                        if (Channel->RecordSignal && !RawSignal.IsEmpty()) {
                                            Channel->RecordedSignal=MoveTemp(RawSignal);Channel->RecordedSky=MoveTemp(SkyMask);Channel->RecordedTarget=MoveTemp(TargetMask);Channel->RecordedSequence=Sequence;
                                        }
                                        Channel->Jpeg = MoveTemp(Encoded);
                                        Channel->Width = Width;
                                        Channel->Height = Height;
                                        Channel->SimulationTime = SimulationTime;
                                        Channel->FrameNumber = Sequence;
                                        ++Channel->CompletedFrames;
                                        Channel->CaptureTime = CaptureTime;
                                    }
                                }
                                Channel->InFlight.fetch_sub(1,std::memory_order_relaxed);
                            });
                    });
            });
        });
}

void FWiseEyeStreamManager::ConfigureThermalReadout(bool Reference,bool AutoGain,bool BlackHot,float Response,float Contrast,float Blur,bool Classified,const WiseEyeThermal::DetectorSettings& Detector)
{
    FScopeLock Lock(&InfraredChannel->CacheLock);
    auto& S=InfraredChannel->Readout;
    if (S.Reference==Reference && S.Auto==AutoGain && S.Black==BlackHot && S.Response==Response && S.Contrast==Contrast && S.Blur==Blur && S.Classified==Classified && S.Detector==Detector) return;
    if (S.Reference!=Reference || (S.Classified!=Classified && Detector.Mode!=1)) InfraredChannel->Exposure=WiseEyeThermal::Exposure{};
    S.Classified=Classified;S.Detector=Detector;
    S.Reference=Reference;S.Auto=AutoGain;S.Black=BlackHot;S.Response=Response;S.Contrast=Contrast;S.Blur=Blur;++S.Revision;
}
FWiseEyeThermalReadoutState FWiseEyeStreamManager::ThermalReadoutState() const
{
    FScopeLock Lock(&InfraredChannel->CacheLock);return InfraredChannel->ThermalStats;
}

void FWiseEyeStreamManager::GetStatistics(bool bInfrared, int64& Sequence, int64& Completed, double& CaptureTime) const
{
    const auto& Channel = bInfrared ? InfraredChannel : VisibleChannel;
    FScopeLock Lock(&Channel->CacheLock);
    Sequence=Channel->FrameNumber;
    Completed=Channel->CompletedFrames;
    CaptureTime=Channel->CaptureTime;
}

bool FWiseEyeStreamManager::GetFrame(bool bInfrared, TArray64<uint8>& Jpeg, int32& Width, int32& Height,
                                     int64& FrameNumber, double& SimulationTime) const
{
    const auto& Channel = bInfrared ? InfraredChannel : VisibleChannel;
    FScopeLock Lock(&Channel->CacheLock);
    if (!Channel->Enabled || Channel->Jpeg.IsEmpty() || FPlatformTime::Seconds()-Channel->CaptureTime>2) return false;
    Jpeg = Channel->Jpeg;
    Width = Channel->Width;
    Height = Channel->Height;
    FrameNumber = Channel->FrameNumber;
    SimulationTime = Channel->SimulationTime;
    return true;
}

bool FWiseEyeStreamManager::GetObserverFrame(TArray64<uint8>& Jpeg,int32& Width,int32& Height,int64& Sequence,double& Time) const
{
    FScopeLock Lock(&ObserverChannel->CacheLock);
    if (ObserverChannel->Jpeg.IsEmpty() || FPlatformTime::Seconds()-ObserverChannel->CaptureTime>2) return false;
    Jpeg=ObserverChannel->Jpeg; Width=ObserverChannel->Width; Height=ObserverChannel->Height;
    Sequence=ObserverChannel->FrameNumber; Time=ObserverChannel->SimulationTime;
    return true;
}

void FWiseEyeStreamManager::SetSignalRecording(bool Enabled)
{
    FScopeLock Lock(&InfraredChannel->CacheLock);InfraredChannel->RecordSignal=Enabled;
    InfraredChannel->RecordedSignal.Reset();InfraredChannel->RecordedSky.Reset();InfraredChannel->RecordedTarget.Reset();
}
bool FWiseEyeStreamManager::GetSignalFrame(TArray<float>& Signal,TArray<uint8>& Sky,TArray<uint8>& Target,int64& Sequence) const
{
    FScopeLock Lock(&InfraredChannel->CacheLock);
    if (!InfraredChannel->Enabled || !InfraredChannel->RecordSignal || InfraredChannel->RecordedSignal.IsEmpty()) return false;
    Signal=InfraredChannel->RecordedSignal;Sky=InfraredChannel->RecordedSky;Target=InfraredChannel->RecordedTarget;Sequence=InfraredChannel->RecordedSequence;return true;
}

bool FWiseEyeStreamManager::CanQueueSample(bool IR) const {
    const auto& C=IR?InfraredChannel:VisibleChannel;
    return C->Enabled && C->InFlight.load()<C->MaxInFlight;
}
bool FWiseEyeStreamManager::GetSample(bool IR,FString& Metadata,TArray64<uint8>& Image) const {
    const auto& C=IR?InfraredChannel:VisibleChannel;FScopeLock Lock(&C->CacheLock);
    if (!C->Enabled || C->SampleImage.IsEmpty()) return false;
    Metadata=C->SampleMetadata;Image=C->SampleImage;return true;
}
