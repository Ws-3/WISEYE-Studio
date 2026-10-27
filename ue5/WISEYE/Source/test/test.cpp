// Copyright Epic Games, Inc. All Rights Reserved.

#include "test.h"
#include "Modules/ModuleManager.h"
#include "WiseEyeRuntimePaths.h"
#include "HAL/PlatformProperties.h"
#include "GameMapsSettings.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"

class FWiseEyeGameModule : public FDefaultGameModuleImpl
{
public:
    virtual void StartupModule() override
    {
        FDefaultGameModuleImpl::StartupModule();
        if (!FPlatformProperties::RequiresCookedData()) return;
        FString SceneId;
        if (!FParse::Value(FCommandLine::Get(),TEXT("WiseEyeScene="),SceneId)) return;
        if (SceneId.IsEmpty() || SceneId.Len()>48) return;
        for (TCHAR C : SceneId)
            if (!(C>='a' && C<='z') && !(C>='0' && C<='9') && C!='_') return;
        FString Text,Map,Id;
        TSharedPtr<FJsonObject> Scene;
        const FString File=FPaths::Combine(WiseEyePaths::ConfigRoot(),TEXT("WISEYE/Scenes"),SceneId+TEXT(".json"));
        bool Prepared=false;
        if (FFileHelper::LoadFileToString(Text,*File) && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Scene) && Scene &&
            Scene->TryGetStringField(TEXT("id"),Id) && Id==SceneId && Scene->TryGetBoolField(TEXT("prepared"),Prepared) && Prepared &&
            Scene->TryGetStringField(TEXT("map"),Map) && Map.StartsWith(TEXT("/Game/")) && FPackageName::IsValidLongPackageName(Map))
        {
            // Shipping intentionally ignores positional map URLs. Set the
            // configured default before UGameInstance chooses its startup map.
            UGameMapsSettings::SetGameDefaultMap(Map);
        }
        else UE_LOG(LogTemp,Error,TEXT("WISEYE invalid startup scene manifest: %s"),*File);
    }
};

IMPLEMENT_PRIMARY_GAME_MODULE( FWiseEyeGameModule, test, "test" );
