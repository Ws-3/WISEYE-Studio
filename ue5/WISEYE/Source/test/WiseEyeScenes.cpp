#include "WiseEyeRuntimePaths.h"
#include "WiseEyeDemo.h"
#include "Camera/CameraActor.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/PackageName.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"

namespace
{
    bool ReadScene(const FString& Id, TSharedPtr<FJsonObject>& Scene, FString& Error)
    {
        if (Id.IsEmpty() || Id.Len()>48) { Error=TEXT("Invalid scene ID"); return false; }
        for (TCHAR C : Id)
            if (!(C>='a' && C<='z') && !(C>='0' && C<='9') && C!='_') { Error=TEXT("Invalid scene ID"); return false; }
        FString Text;
        const FString File=FPaths::Combine(WiseEyePaths::ConfigRoot(),TEXT("WISEYE/Scenes"),Id+TEXT(".json"));
        if (!FFileHelper::LoadFileToString(Text,*File) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Scene) || !Scene)
        { Error=TEXT("Scene manifest not found or invalid JSON"); return false; }
        double Version=0;
        bool Prepared=false;
        FString ManifestId, Map, Rig;
        if (!Scene->TryGetBoolField(TEXT("prepared"),Prepared) || !Prepared ||
            !Scene->TryGetNumberField(TEXT("version"),Version) || Version!=1 ||
            !Scene->TryGetStringField(TEXT("id"),ManifestId) || ManifestId!=Id ||
            !Scene->TryGetStringField(TEXT("rig"),Rig) || Rig!=TEXT("standard_v1") ||
            !Scene->TryGetStringField(TEXT("map"),Map) || !Map.StartsWith(TEXT("/Game/")) ||
            !FPackageName::IsValidLongPackageName(Map) || !FPackageName::DoesPackageExist(Map))
        { Error=TEXT("Scene version, ID, rig or installed map is invalid"); return false; }
        for (const TCHAR* Key : {TEXT("gimbal_location_cm"),TEXT("flight_origin_cm"),TEXT("overview_location_cm"),TEXT("overview_rotation_deg")})
        {
            const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
            if (!Scene->TryGetArrayField(Key,Values) || Values->Num()!=3) { Error=TEXT("Invalid scene vector"); return false; }
            for (auto V : *Values) { double N; if (!V->TryGetNumber(N) || !FMath::IsFinite(N) || FMath::Abs(N)>1e8) { Error=TEXT("Invalid scene coordinate"); return false; } }
        }
        const TCHAR* Keys[]={TEXT("flight_radius_cm"),TEXT("period_s"),TEXT("vertical_amplitude_cm"),TEXT("fov_deg")};
        const double Low[]={1,1,0,5}, High[]={1e6,86400,1e6,120};
        for (int32 I=0; I<4; ++I) { double N; if (!Scene->TryGetNumberField(Keys[I],N) || !FMath::IsFinite(N) || N<Low[I] || N>High[I]) { Error=TEXT("Invalid scene parameter range"); return false; } }
        return true;
    }
    FVector Vec(const TSharedPtr<FJsonObject>& Scene,const TCHAR* Key)
    {
        const auto& V=Scene->GetArrayField(Key);
        return FVector(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber());
    }
}

bool AWiseEyeDemo::ApplySceneConfiguration(FString& Error)
{
    // URL selects an experiment on travel; actor default identifies editor Play.
    const FString Option=GetWorld()->URL.GetOption(TEXT("wiseeye_scene="),TEXT(""));
    if (!Option.IsEmpty()) SceneId=Option;
    TSharedPtr<FJsonObject> Scene;
    if (!ReadScene(SceneId,Scene,Error)) return false;
    FString Map=GetWorld()->GetOutermost()->GetName();
    Map=UWorld::RemovePIEPrefix(Map);
    if (Map!=Scene->GetStringField(TEXT("map"))) { Error=TEXT("Scene manifest does not match active map"); return false; }
    // Optional user layout overrides positions only, never base scene assets.
    const FString LayoutFile=FPaths::Combine(WiseEyePaths::ConfigRoot(),TEXT("WISEYE/Layouts"),SceneId+TEXT(".json"));
    if (FPaths::FileExists(LayoutFile))
    {
        FString Text; TSharedPtr<FJsonObject> Layout;
        if (!FFileHelper::LoadFileToString(Text,*LayoutFile) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Layout) || !Layout)
        { Error=TEXT("Invalid initial layout JSON"); return false; }
        double Version=0; FString LayoutScene;
        if (!Layout->TryGetNumberField(TEXT("version"),Version) || Version!=1 || !Layout->TryGetStringField(TEXT("scene_id"),LayoutScene) || LayoutScene!=SceneId)
        { Error=TEXT("Invalid initial layout version or scene"); return false; }
        for (const TCHAR* Key : {TEXT("gimbal_location_cm"),TEXT("flight_origin_cm")})
        {
            const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
            if (!Layout->TryGetArrayField(Key,Values) || Values->Num()!=3) { Error=TEXT("Invalid layout vector"); return false; }
            for (const auto& Value : *Values) { double N=0; if (!Value->TryGetNumber(N) || !FMath::IsFinite(N) || FMath::Abs(N)>1e7) { Error=TEXT("Invalid layout coordinate"); return false; } }
        }
        for (const TCHAR* Key : {TEXT("gimbal_location_cm"),TEXT("flight_origin_cm")}) Scene->SetArrayField(Key,Layout->GetArrayField(Key));
    }
    AActor* Mount=this;
    while (Mount->GetAttachParentActor()) Mount=Mount->GetAttachParentActor();
    Mount->AddActorWorldOffset(Vec(Scene,TEXT("gimbal_location_cm"))-GetActorLocation());
    FlightOrigin=Vec(Scene,TEXT("flight_origin_cm"));
    FlightRadius=Scene->GetNumberField(TEXT("flight_radius_cm"));
    Period=Scene->GetNumberField(TEXT("period_s"));
    VerticalAmplitude=Scene->GetNumberField(TEXT("vertical_amplitude_cm"));
    FieldOfView=Scene->GetNumberField(TEXT("fov_deg"));
    MinimumAltitude=FMath::Min(MinimumAltitude,float(FlightOrigin.Z-FlightRadius));
    MaximumAltitude=FMath::Max(MaximumAltitude,float(FlightOrigin.Z+FlightRadius));
    if (Overview)
    {
        const FVector R=Vec(Scene,TEXT("overview_rotation_deg"));
        Overview->SetActorLocationAndRotation(Vec(Scene,TEXT("overview_location_cm")),FRotator(R.X,R.Y,R.Z));
    }
    return true;
}

bool AWiseEyeDemo::RequestScene(const FString& Id,FString& Error)
{
    if (!PendingScene.IsEmpty()) { Error=TEXT("A scene switch is already pending"); return false; }
    TSharedPtr<FJsonObject> Scene;
    if (!ReadScene(Id,Scene,Error)) return false;
    PendingScene=Id;
    const FString Map=Scene->GetStringField(TEXT("map"));
    // Allow the acknowledgement to leave the nonblocking socket before EndPlay closes it.
    FTimerHandle Handle;
    GetWorldTimerManager().SetTimer(Handle,FTimerDelegate::CreateWeakLambda(this,[this,Map,Id]()
    {
        UGameplayStatics::OpenLevel(this,FName(*Map),true,TEXT("game=/Script/test.WiseEyeGameMode?wiseeye_scene=")+Id);
    }),0.75f,false);
    return true;
}
