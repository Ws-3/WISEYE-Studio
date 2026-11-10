#include "WiseEyeDemo.h"
#include "Dom/JsonObject.h"
#include "HAL/PlatformMemory.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformProcess.h"
#include "HAL/PlatformTime.h"
#include "DynamicRHI.h"
#include "RHIStats.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "ShaderCompiler.h"
#endif
#if PLATFORM_WINDOWS
#include "Windows/WindowsHWrapper.h"
#include <pdh.h>
#include <pdhmsg.h>
#include <d3d12.h>
#include <dxgi1_4.h>
#endif

namespace
{
    void ReadShippingVideoMemory(const TSharedRef<FJsonObject>& Result)
    {
#if PLATFORM_WINDOWS
        // UE's D3D12 memory snapshot is compiled out when Shipping disables STATS.
        // Query the actual RHI device's adapter, not the first enumerated GPU.
        if (!GDynamicRHI || GDynamicRHI->GetInterfaceType()!=ERHIInterfaceType::D3D12) return;
        auto* Device=static_cast<ID3D12Device*>(GDynamicRHI->RHIGetNativeDevice());
        if (!Device) return;
        IDXGIFactory4* Factory=nullptr;
        if (FAILED(CreateDXGIFactory1(IID_PPV_ARGS(&Factory)))) return;
        IDXGIAdapter3* Adapter=nullptr;
        const HRESULT Found=Factory->EnumAdapterByLuid(Device->GetAdapterLuid(),IID_PPV_ARGS(&Adapter));
        Factory->Release();
        if (FAILED(Found)) return;
        DXGI_QUERY_VIDEO_MEMORY_INFO Info={};
        if (SUCCEEDED(Adapter->QueryVideoMemoryInfo(0,DXGI_MEMORY_SEGMENT_GROUP_LOCAL,&Info)) && Info.Budget>0) {
            Result->SetNumberField(TEXT("ue_vram_used_bytes"),double(Info.CurrentUsage));
            Result->SetNumberField(TEXT("ue_vram_budget_bytes"),double(Info.Budget));
        }
        Adapter->Release();
#endif
    }

    // PDH has no shell, vendor utility or child process. English paths work on
    // localized Windows. GPU is the busiest engine of THIS UE process.
    struct FWindowsLoad
    {
#if PLATFORM_WINDOWS
        PDH_HQUERY Query=nullptr;
        PDH_HCOUNTER Counter=nullptr;
        uint64 LastIdle=0,LastKernel=0,LastUser=0;
        bool Warm=false;
        FWindowsLoad() {
            if (PdhOpenQueryW(nullptr,0,&Query)==ERROR_SUCCESS &&
                PdhAddEnglishCounterW(Query,L"\\GPU Engine(*)\\Utilization Percentage",0,&Counter)==ERROR_SUCCESS)
                PdhCollectQueryData(Query);
        }
        ~FWindowsLoad() { if (Query) PdhCloseQuery(Query); }
        void Read(const TSharedRef<FJsonObject>& Result) {
            FILETIME Idle,Kernel,User;
            if (GetSystemTimes(&Idle,&Kernel,&User)) {
                auto Value=[](FILETIME T) { return (uint64(T.dwHighDateTime)<<32)|T.dwLowDateTime; };
                const uint64 I=Value(Idle),K=Value(Kernel),U=Value(User);
                const uint64 Total=(K-LastKernel)+(U-LastUser);
                if (Warm && Total>0) Result->SetNumberField(TEXT("system_cpu_pct"),FMath::Clamp(100.*(1.-double(I-LastIdle)/Total),0.,100.));
                LastIdle=I;LastKernel=K;LastUser=U;Warm=true;
            }
            if (!Counter || PdhCollectQueryData(Query)!=ERROR_SUCCESS) return;
            DWORD Bytes=0,Count=0;
            if (PdhGetFormattedCounterArrayW(Counter,PDH_FMT_DOUBLE,&Bytes,&Count,nullptr)!=PDH_MORE_DATA || !Bytes) return;
            TArray<uint8> Buffer;Buffer.SetNumUninitialized(Bytes);
            auto* Items=reinterpret_cast<PDH_FMT_COUNTERVALUE_ITEM_W*>(Buffer.GetData());
            if (PdhGetFormattedCounterArrayW(Counter,PDH_FMT_DOUBLE,&Bytes,&Count,Items)!=ERROR_SUCCESS) return;
            const FString Pid=FString::Printf(TEXT("pid_%u_"),FPlatformProcess::GetCurrentProcessId());
            double Peak=0;bool Found=false;
            for (DWORD Index=0;Index<Count;++Index) {
                if (FString(Items[Index].szName).StartsWith(Pid) &&
                    (Items[Index].FmtValue.CStatus==PDH_CSTATUS_VALID_DATA || Items[Index].FmtValue.CStatus==PDH_CSTATUS_NEW_DATA)) {
                    Found=true;Peak=FMath::Max(Peak,Items[Index].FmtValue.doubleValue);
                }
            }
            if (Found) Result->SetNumberField(TEXT("ue_gpu_engine_peak_pct"),FMath::Clamp(Peak,0.,100.));
        }
#else
        void Read(const TSharedRef<FJsonObject>&) {}
#endif
    };
}

void AWiseEyeDemo::UpdateRuntimeStatus()
{
    const double Now=FPlatformTime::Seconds();
    if (RuntimeStatus && Now-RuntimeSampleTime<1.) return;
    auto Snapshot=MakeShared<FJsonObject>();
    Snapshot->SetNumberField(TEXT("sample_time_s"),Now);
    Snapshot->SetStringField(TEXT("scope"),TEXT("simulation_host"));
    Snapshot->SetStringField(TEXT("cpu_name"),FPlatformMisc::GetCPUBrand());
    Snapshot->SetStringField(TEXT("gpu_name"),GRHIAdapterName);
#if WITH_EDITOR
    Snapshot->SetNumberField(TEXT("asset_compile_jobs"),FAssetCompilingManager::Get().GetNumRemainingAssets());
    Snapshot->SetNumberField(TEXT("shader_compile_jobs"),GShaderCompilingManager?GShaderCompilingManager->GetNumRemainingJobs():0);
#endif
    if (RuntimeSampleTime>0) Snapshot->SetNumberField(TEXT("ue_fps"),(TickSequence-RuntimeSampleTick)/(Now-RuntimeSampleTime));
    const auto Memory=FPlatformMemory::GetStats();
    Snapshot->SetNumberField(TEXT("system_ram_total_bytes"),double(Memory.TotalPhysical));
    Snapshot->SetNumberField(TEXT("system_ram_used_bytes"),double(Memory.TotalPhysical-Memory.AvailablePhysical));
    Snapshot->SetNumberField(TEXT("ue_ram_bytes"),double(Memory.UsedPhysical));
    if (GDynamicRHI) {
        FTextureMemoryStats Texture;RHIGetTextureMemoryStats(Texture);
        FRHIMemoryStats Gpu;RHIGetMemoryStats(Gpu);
        if (Texture.DedicatedVideoMemory>0) Snapshot->SetNumberField(TEXT("gpu_dedicated_total_bytes"),double(Texture.DedicatedVideoMemory));
        if (Gpu.IsValid()) {
            Snapshot->SetNumberField(TEXT("ue_vram_used_bytes"),double(Gpu.UsedLocal));
            Snapshot->SetNumberField(TEXT("ue_vram_budget_bytes"),double(Gpu.BudgetLocal));
        }
    }
    if (!Snapshot->HasField(TEXT("ue_vram_budget_bytes"))) ReadShippingVideoMemory(Snapshot);
    static FWindowsLoad Load;Load.Read(Snapshot);
    RuntimeStatus=Snapshot;RuntimeSampleTime=Now;RuntimeSampleTick=TickSequence;
}
