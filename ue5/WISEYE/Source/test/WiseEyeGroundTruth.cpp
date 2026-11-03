#include "WiseEyeGroundTruth.h"
#include "WiseEyeDemo.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "HAL/PlatformTime.h"

namespace {
TArray<TSharedPtr<FJsonValue>> Numbers(std::initializer_list<double> Values) {
    TArray<TSharedPtr<FJsonValue>> Out;
    for (double V:Values) Out.Add(MakeShared<FJsonValueNumber>(V));
    return Out;
}
}

TSharedPtr<FWiseEyeGTSnapshot> CaptureWiseEyeGroundTruth(AWiseEyeDemo& Demo,bool IR,const FString& Token)
{
    auto S=MakeShared<FWiseEyeGTSnapshot>();
    S->Token=Token;S->RunId=Demo.PlaySessionId;S->SceneId=Demo.SceneId;S->DeviceId=Demo.GimbalId;
    S->SensorId=IR?TEXT("infrared"):TEXT("visible");S->Width=IR?640:1920;S->Height=IR?512:1080;
    auto* Source=IR?Demo.InfraredCapture.Get():Demo.Capture.Get();
    S->Position=Source->GetComponentLocation();S->Rotation=Source->GetComponentRotation();S->Fov=Source->FOVAngle;S->Settings=Demo.GTSettings;
    TArray<AWiseEyeDemo*> Targets;
    auto* Root=Demo.FleetRoot?Demo.FleetRoot.Get():&Demo;
    S->Environment=Root->EnvironmentState();
    for (auto Rig:Root->FleetRigs) if (IsValid(Rig) && Rig->OwnsDrone && IsValid(Rig->Drone)) {
        Targets.Add(Rig);S->TargetIds.Add(Rig->DroneId);S->Models.Add(Rig->DroneModel);S->ScenarioModels.AddUnique(Rig->DroneModel);
    }
    // Separate fixed-resolution resources per modality, reused only in render
    // command order. Never alter shared thermal stencil codes or scene assets.
    const int32 Base=IR?5:0;
    if (Demo.GTDepthCaptures.Num()<10) Demo.GTDepthCaptures.SetNum(10);
    if (Demo.GTDepthTargets.Num()<10) Demo.GTDepthTargets.SetNum(10);
    for (int32 I=0;I<=Targets.Num();++I) {
        auto* C=Demo.GTDepthCaptures[Base+I].Get();
        if (!C) {
            C=NewObject<USceneCaptureComponent2D>(&Demo);
            C->bCaptureEveryFrame=false;C->bCaptureOnMovement=false;
            C->RegisterComponent();Demo.GTDepthCaptures[Base+I]=C;
            auto* RT=NewObject<UTextureRenderTarget2D>(&Demo);
            RT->RenderTargetFormat=RTF_R32f;RT->bForceLinearGamma=true;
            RT->ClearColor=FLinearColor::Black;RT->InitAutoFormat(S->Width,S->Height);
            Demo.GTDepthTargets[Base+I]=RT;C->TextureTarget=RT;
        }
        C->SetWorldLocationAndRotation(S->Position,S->Rotation);C->FOVAngle=S->Fov;
        C->CaptureSource=ESceneCaptureSource::SCS_SceneDepth;
        C->ShowFlags.SetTemporalAA(false);C->ShowFlags.SetAntiAliasing(false);
        C->HiddenActors=Source->HiddenActors;C->HiddenComponents=Source->HiddenComponents;
        C->ShowOnlyComponents.Empty();C->ShowOnlyActors.Empty();
        C->PrimitiveRenderMode=I==0?ESceneCapturePrimitiveRenderMode::PRM_RenderScenePrimitives:ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
        if (I>0) {
            TArray<AActor*> Actors={Targets[I-1]->Drone};
            Targets[I-1]->Drone->GetAttachedActors(Actors,false,true);
            for (auto* Actor:Actors) {
                TArray<UPrimitiveComponent*> Components;Actor->GetComponents(Components);
                for (auto* P:Components) if (P->IsVisible() && !P->bHiddenInGame) C->ShowOnlyComponent(P);
            }
        }
        C->CaptureScene();
        S->Resources.Add(C->TextureTarget->GameThread_GetRenderTargetResource());
    }
    return S;
}

TSharedPtr<FJsonObject> FWiseEyeGTSnapshot::Annotate(int64 Sequence,double Time) const
{
    const double Started=FPlatformTime::Seconds();
    auto R=MakeShared<FJsonObject>();
    R->SetStringField(TEXT("sample_token"),Token);R->SetStringField(TEXT("run_id"),RunId);R->SetStringField(TEXT("scene_id"),SceneId);
    R->SetStringField(TEXT("device_id"),DeviceId);R->SetStringField(TEXT("sensor_id"),SensorId);
    if (Environment) R->SetObjectField(TEXT("environment"),Environment);
    TArray<TSharedPtr<FJsonValue>> Scenario;
    for (const FString& Model:ScenarioModels) Scenario.Add(MakeShared<FJsonValueString>(Model));
    R->SetArrayField(TEXT("scenario_models"),Scenario);
    R->SetStringField(TEXT("context_source"),TEXT("capture_tick"));
    R->SetStringField(TEXT("frame_id"),RunId+TEXT("/")+DeviceId+TEXT("/")+SensorId+TEXT("/")+FString::Printf(TEXT("%lld"),Sequence));
    R->SetNumberField(TEXT("frame_number"),Sequence);R->SetNumberField(TEXT("simulation_time_s"),Time);
    R->SetNumberField(TEXT("width"),Width);R->SetNumberField(TEXT("height"),Height);R->SetNumberField(TEXT("horizontal_fov_deg"),Fov);
    const double Focal=Width/(2.*FMath::Tan(FMath::DegreesToRadians(double(Fov)*.5)));
    R->SetArrayField(TEXT("intrinsics_fx_fy_cx_cy"),Numbers({Focal,Focal,Width*.5,Height*.5}));
    R->SetArrayField(TEXT("camera_position_cm"),Numbers({Position.X,Position.Y,Position.Z}));
    R->SetArrayField(TEXT("camera_rotation_pitch_yaw_roll_deg"),Numbers({Rotation.Pitch,Rotation.Yaw,Rotation.Roll}));
    R->SetStringField(TEXT("bbox_format"),TEXT("xyxy_pixels_exclusive_visible_extent"));
    R->SetStringField(TEXT("visibility_method"),TEXT("raster_scene_vs_isolated_target_depth"));
    auto Policy=MakeShared<FJsonObject>();Policy->SetBoolField(TEXT("keep_partial_occlusion"),Settings.KeepPartialOcclusion);
    Policy->SetBoolField(TEXT("keep_partial_outside"),Settings.KeepPartialOutside);Policy->SetNumberField(TEXT("min_visible_pixels"),Settings.MinVisiblePixels);
    Policy->SetNumberField(TEXT("min_visible_fraction"),Settings.MinVisibleFraction);R->SetObjectField(TEXT("gt_policy"),Policy);
    TArray<TSharedPtr<FJsonValue>> Objects,Ignored;
    bool Valid=Error.IsEmpty() && Depths.Num()==TargetIds.Num()+1;
    for (const auto& D:Depths) Valid=Valid && D.Num()==Width*Height;
    if (Valid) for (int32 I=0;I<TargetIds.Num();++I) {
        int32 Total=0,Visible=0,MinX=Width,MinY=Height,MaxX=0,MaxY=0;bool Outside=false;
        for (int32 Y=0;Y<Height;++Y) for (int32 X=0;X<Width;++X) {
            const int32 P=Y*Width+X;const float D=Depths[I+1][P],Scene=Depths[0][P];
            if (!FMath::IsFinite(D) || D<=0 || D>=1e8f) continue;
            ++Total;Outside=Outside || X==0 || Y==0 || X==Width-1 || Y==Height-1;
            const float Tolerance=FMath::Max(.5f,D*.00001f);
            if (!FMath::IsFinite(Scene) || Scene<=0 || D>Scene+Tolerance) continue;
            ++Visible;MinX=FMath::Min(MinX,X);MinY=FMath::Min(MinY,Y);MaxX=FMath::Max(MaxX,X+1);MaxY=FMath::Max(MaxY,Y+1);
        }
        if (!Visible) continue; // fully hidden / outside / behind camera: no GT
        const double Fraction=double(Visible)/FMath::Max(1,Total);const bool Occluded=Visible<Total;
        auto O=MakeShared<FJsonObject>();O->SetStringField(TEXT("target_id"),TargetIds[I]);O->SetNumberField(TEXT("class_id"),0);
        O->SetStringField(TEXT("class_name"),TEXT("drone"));O->SetStringField(TEXT("model_id"),Models[I]);
        O->SetArrayField(TEXT("bbox_xyxy"),Numbers({double(MinX),double(MinY),double(MaxX),double(MaxY)}));
        O->SetNumberField(TEXT("visible_pixels"),Visible);O->SetNumberField(TEXT("in_frame_target_pixels"),Total);
        O->SetNumberField(TEXT("visible_fraction_in_frame"),Fraction);O->SetBoolField(TEXT("partially_occluded"),Occluded);
        O->SetBoolField(TEXT("partially_outside"),Outside);
        const bool Keep=(!Occluded || Settings.KeepPartialOcclusion) && (!Outside || Settings.KeepPartialOutside) && Visible>=Settings.MinVisiblePixels && Fraction>=Settings.MinVisibleFraction;
        (Keep?Objects:Ignored).Add(MakeShared<FJsonValueObject>(O));
    }
    R->SetStringField(TEXT("annotation_status"),Valid?TEXT("complete"):TEXT("unavailable"));
    R->SetBoolField(TEXT("training_eligible"),Valid && Ignored.IsEmpty());
    R->SetBoolField(TEXT("negative_sample"),Valid && Objects.IsEmpty() && Ignored.IsEmpty());
    R->SetArrayField(TEXT("objects"),Objects);R->SetArrayField(TEXT("ignored_objects"),Ignored);
    if (!Valid) R->SetStringField(TEXT("annotation_error"),Error.IsEmpty()?TEXT("Incomplete depth planes"):Error);
    R->SetNumberField(TEXT("gt_annotation_cpu_ms"),(FPlatformTime::Seconds()-Started)*1000);
    return R;
}
