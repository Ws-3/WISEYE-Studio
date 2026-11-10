#pragma once
#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "WiseEyePopulation.generated.h"
class AMassSpawner;
struct FStreamableHandle;
/** Holds the completion callback for one existing map spawner. No per-agent control. */
UCLASS()
class UWiseEyePopulationWatch : public UObject {
    GENERATED_BODY()
public:
    UPROPERTY() TWeakObjectPtr<AMassSpawner> Spawner;
    FString Kind;
    int32 BaseCount=0,Desired=0,Applied=-1;
    bool Pending=false;
    bool Prepared=false,Preparing=false;
    FString PreloadError;
    TSharedPtr<FStreamableHandle> AssetHandle;
    void Prepare();
    UFUNCTION() void Finished();
    void Apply();
};
