#pragma once
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"

namespace WiseEyePaths
{
    inline FString DataRoot()
    {
        FString Root;
        FParse::Value(FCommandLine::Get(), TEXT("WiseEyeDataDir="), Root);
        return Root.IsEmpty() ? FString() : FPaths::ConvertRelativePathToFull(Root);
    }
    inline FString ConfigRoot()
    {
        const FString Root=DataRoot();
        return Root.IsEmpty() ? FPaths::ProjectConfigDir() : FPaths::Combine(Root,TEXT("ue5/WISEYE/Config"));
    }
    inline FString SavedRoot()
    {
        const FString Root=DataRoot();
        return Root.IsEmpty() ? FPaths::ProjectSavedDir() : FPaths::Combine(Root,TEXT("ue5/WISEYE/Saved"));
    }
}
