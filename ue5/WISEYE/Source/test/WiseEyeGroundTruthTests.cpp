#include "WiseEyeGroundTruth.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Dom/JsonObject.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWiseEyeGTTest,"WiseEye.GroundTruth.VisibilityPolicy",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWiseEyeGTTest::RunTest(const FString&)
{
    FWiseEyeGTSnapshot S;S.Width=5;S.Height=5;S.TargetIds={TEXT("uav-01")};S.Models={TEXT("mavic3")};
    S.Depths.SetNum(2);S.Depths[0].Init(1e10f,25);S.Depths[1].Init(1e10f,25);
    S.Depths[0][12]=S.Depths[1][12]=100;
    auto R=S.Annotate(1,0);
    TestEqual(TEXT("visible target"),R->GetArrayField(TEXT("objects")).Num(),1);
    TestFalse(TEXT("positive"),R->GetBoolField(TEXT("negative_sample")));
    S.Depths[0][12]=50;R=S.Annotate(2,0);
    TestEqual(TEXT("occluded target removed"),R->GetArrayField(TEXT("objects")).Num(),0);
    TestTrue(TEXT("full occlusion is valid negative"),R->GetBoolField(TEXT("negative_sample")));
    S.Depths[0][13]=S.Depths[1][13]=100;R=S.Annotate(3,0);
    TestEqual(TEXT("partial retained"),R->GetArrayField(TEXT("objects")).Num(),1);
    S.Settings.KeepPartialOcclusion=false;R=S.Annotate(4,0);
    TestEqual(TEXT("partial policy omitted"),R->GetArrayField(TEXT("objects")).Num(),0);
    TestEqual(TEXT("ignored recorded"),R->GetArrayField(TEXT("ignored_objects")).Num(),1);
    TestFalse(TEXT("filtered visible not a false negative"),R->GetBoolField(TEXT("training_eligible")));
    S.Depths[0].Init(1e10f,25);S.Depths[1].Init(1e10f,25);S.Depths[0][10]=S.Depths[1][10]=100;
    S.Settings.KeepPartialOutside=false;R=S.Annotate(5,0);
    TestEqual(TEXT("border-clipped filtered"),R->GetArrayField(TEXT("ignored_objects")).Num(),1);
    S.Settings.KeepPartialOutside=true;R=S.Annotate(6,0);
    TestEqual(TEXT("border-clipped retained"),R->GetArrayField(TEXT("objects")).Num(),1);
    S.Depths[1].Init(1e10f,25);R=S.Annotate(7,0);
    TestTrue(TEXT("out of view negative"),R->GetBoolField(TEXT("negative_sample")));
    S.Error=TEXT("readback failed");R=S.Annotate(8,0);
    TestFalse(TEXT("failure never trains"),R->GetBoolField(TEXT("training_eligible")));
    TestEqual(TEXT("failure distinguished"),R->GetStringField(TEXT("annotation_status")),FString(TEXT("unavailable")));
    return true;
}
#endif
