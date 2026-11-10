#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

// Lens controls in metres/mm/f-number. Not a measured camera calibration.
struct FWiseEyeFocus {
    FString Mode=TEXT("auto");
    double DistanceM=100,Aperture=2.8,SensorWidthMM=13.2,ActualM=100,NextTrace=0;
    bool Read(const TSharedPtr<FJsonObject>& Args) {
        auto Copy=*this;
        if (Args->HasField(TEXT("focus_mode")) && (!Args->TryGetStringField(TEXT("focus_mode"),Copy.Mode) ||
            (Copy.Mode!=TEXT("auto") && Copy.Mode!=TEXT("manual") && Copy.Mode!=TEXT("infinity") && Copy.Mode!=TEXT("off")))) return false;
        for (auto Pair : {TPair<const TCHAR*,double*>(TEXT("focus_distance_m"),&Copy.DistanceM),
             TPair<const TCHAR*,double*>(TEXT("aperture_f"),&Copy.Aperture)}) {
            if (Args->HasField(Pair.Key) && (Args->Values[Pair.Key]->Type!=EJson::Number || !Args->TryGetNumberField(Pair.Key,*Pair.Value) || !FMath::IsFinite(*Pair.Value))) return false;
        }
        if (Copy.DistanceM<.2 || Copy.DistanceM>10000 || Copy.Aperture<1 || Copy.Aperture>22) return false;
        *this=Copy;return true;
    }
    void Write(const TSharedPtr<FJsonObject>& R,double Fov=25) const {
        R->SetBoolField(TEXT("focus_supported"),true);R->SetStringField(TEXT("focus_mode"),Mode);
        R->SetNumberField(TEXT("focus_distance_m"),DistanceM);R->SetNumberField(TEXT("aperture_f"),Aperture);
        R->SetNumberField(TEXT("actual_focus_distance_m"),ActualM);R->SetNumberField(TEXT("sensor_width_mm"),SensorWidthMM);
        const double F=SensorWidthMM/(2*FMath::Tan(FMath::DegreesToRadians(Fov*.5))),S=ActualM*1000;
        const double Circle=SensorWidthMM/1920*2,H=F*F/(Aperture*Circle)+F;
        const bool Infinite=Mode==TEXT("off") || H<=S-F;
        R->SetNumberField(TEXT("dof_near_m"),Mode==TEXT("off")?0:H*S/(H+S-F)/1000);
        R->SetNumberField(TEXT("dof_far_m"),Infinite?-1:H*S/(H-S+F)/1000);
        R->SetBoolField(TEXT("dof_far_infinite"),Infinite);
        R->SetStringField(TEXT("dof_estimate"),TEXT("thin-lens, 2 output-pixel circle of confusion; not measured calibration"));
    }
};
