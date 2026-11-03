#include "WiseEyeEventCamera.h"
#include "Dom/JsonObject.h"

void FWiseEyeEventCamera::Configure(bool Value,float On,float Off,int64 Refractory) {
    FScopeLock Guard(&Lock);
    if (Enabled==Value && Model.On==On && Model.Off==Off && Model.Refractory==Refractory) return;
    Enabled=Value;Model.On=On;Model.Off=Off;Model.Refractory=Refractory;Model.Reset();
    ++Generation;Count=Write=0;LastTime=-1;ActualHz=0;LastFrame=0;
    if (Enabled) Ring.SetNum(65536);else Ring.Empty();
}
int64 FWiseEyeEventCamera::Revision() const { FScopeLock Guard(&Lock);return Generation; }
void FWiseEyeEventCamera::Process(const TArray<float>& Signal,int Width,int Height,double Time,int64 Frame,int64 Revision) {
    FScopeLock Guard(&Lock);
    if (!Enabled || Revision!=Generation || Frame<=LastFrame || Signal.Num()!=Width*Height || Time<=LastTime) return;
    if (LastFrame>0) DroppedFrames+=FMath::Max(int64(0),Frame-LastFrame-1);
    if (LastTime>=0) ActualHz=1./FMath::Max(.000001,Time-LastTime);
    auto Events=Model.Process(Signal.GetData(),Width,Height,Time);
    for (const auto& E:Events) { Ring[Write]=E;Write=(Write+1)%Ring.Num();Count=FMath::Min(Count+1,Ring.Num());++Next; }
    ++Frames;LastFrame=Frame;LastTime=Time;
}
TSharedPtr<FJsonObject> FWiseEyeEventCamera::State() const {
    FScopeLock Guard(&Lock);auto R=MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("enabled"),Enabled);R->SetNumberField(TEXT("generation"),Generation);
    R->SetNumberField(TEXT("events_total"),Next-1);R->SetNumberField(TEXT("buffer_events"),Count);
    R->SetNumberField(TEXT("sample_frames"),Frames);R->SetNumberField(TEXT("actual_sample_hz"),Enabled?ActualHz:0);
    R->SetNumberField(TEXT("dropped_sample_frames"),DroppedFrames);R->SetNumberField(TEXT("truncated_events"),double(Model.Truncated));
    R->SetStringField(TEXT("signal_model"),TEXT("independent HDR capture, frame-driven log-intensity crossings; interpolated timestamps, not hardware timing"));return R;
}
TSharedPtr<FJsonObject> FWiseEyeEventCamera::Packet(int64 After,int32 Limit,bool Latest) const {
    FScopeLock Guard(&Lock);auto R=MakeShared<FJsonObject>();
    const int64 Oldest=Next-Count;
    int64 Start=FMath::Max(After+1,Oldest);
    if (Latest) Start=FMath::Max(Start,Next-Limit);
    const int64 Stop=FMath::Min(Next,Start+Limit);
    TArray<TSharedPtr<FJsonValue>> Rows;
    for (int64 Id=Start;Id<Stop;++Id) {
        const int32 Offset=int32(Id-Oldest),Index=(Write-Count+Ring.Num()+Offset)%Ring.Num();
        const auto& E=Ring[Index];TArray<TSharedPtr<FJsonValue>> Row;
        for (double V:{double(E.X),double(E.Y),double(E.T),double(E.P)}) Row.Add(MakeShared<FJsonValueNumber>(V));
        Rows.Add(MakeShared<FJsonValueArray>(Row));
    }
    R->SetArrayField(TEXT("events"),Rows);R->SetNumberField(TEXT("after_sequence"),After);
    R->SetNumberField(TEXT("next_cursor"),Rows.IsEmpty()?FMath::Min(After,Next-1):Stop-1);
    R->SetNumberField(TEXT("latest_sequence"),Next-1);R->SetNumberField(TEXT("skipped_events"),FMath::Max(int64(0),Start-After-1));
    R->SetNumberField(TEXT("generation"),Generation);R->SetNumberField(TEXT("world_time_s"),FMath::Max(0.,LastTime));
    R->SetNumberField(TEXT("truncated_events"),double(Model.Truncated));R->SetNumberField(TEXT("dropped_sample_frames"),DroppedFrames);
    R->SetNumberField(TEXT("sample_frames"),Frames);R->SetNumberField(TEXT("actual_sample_hz"),Enabled?ActualHz:0);
    R->SetNumberField(TEXT("positive_threshold"),Model.On);R->SetNumberField(TEXT("negative_threshold"),Model.Off);
    R->SetNumberField(TEXT("refractory_us"),Model.Refractory);
    R->SetStringField(TEXT("columns"),TEXT("x,y,t_us,p"));R->SetStringField(TEXT("timebase"),TEXT("ue_world_time_since_play_us; frame-interpolated"));
    R->SetNumberField(TEXT("width"),640);R->SetNumberField(TEXT("height"),480);R->SetBoolField(TEXT("enabled"),Enabled);return R;
}
