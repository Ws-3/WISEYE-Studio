// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;
using System.IO;
using EpicGames.Core;

public class test : ModuleRules
{
	public test(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		string FDM = Path.GetFullPath(Path.Combine(ModuleDirectory,"../../ThirdParty/JSBSim"));
		RuntimeDependencies.Add("$(TargetOutputDir)/WiseEyeJSBSim.dll",Path.Combine(FDM,"bin/WiseEyeJSBSim.dll"));
		RuntimeDependencies.Add(Path.Combine(FDM,"Resources/..."), StagedFileType.NonUFS);
		RuntimeDependencies.Add(Path.Combine(FDM,"JSBSim-LICENSE.txt"), StagedFileType.NonUFS);
		// The compatibility installer also places resources under the host project.
		// Keep that runtime path when cooking a custom host, not only in the Editor.
		if (Target.ProjectFile != null)
		{
			string HostFDM = Path.Combine(Target.ProjectFile.Directory.FullName,"ThirdParty/JSBSim");
			if (Path.GetFullPath(HostFDM) != FDM)
			{
				if (Directory.Exists(Path.Combine(HostFDM,"Resources")))
					RuntimeDependencies.Add(Path.Combine(HostFDM,"Resources/..."), StagedFileType.NonUFS);
				string HostConfig = Path.Combine(Target.ProjectFile.Directory.FullName,"Config/WISEYE");
				if (Directory.Exists(HostConfig)) RuntimeDependencies.Add(Path.Combine(HostConfig,"..."), StagedFileType.NonUFS);
			}
		}

		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput", "ProjectAirSim" });

		PrivateDependencyModuleNames.AddRange(new string[] { "Sockets", "Networking", "Json", "ImageWrapper", "RHI", "RenderCore", "EngineSettings", "MassSpawner", "MassCore", "MassEntity", "MassCommon", "MassCrowd", "MassLOD", "MassRepresentation" });
		// City Sample traffic is an optional host integration, not a core sensor dependency.
		bool WithCityPopulation = false;
		if (Target.ProjectFile != null && File.Exists(Path.Combine(Target.ProjectFile.Directory.FullName,"Plugins/Traffic/Traffic.uplugin")))
		{
			var HostDescriptor = JsonObject.Read(Target.ProjectFile);
			if (HostDescriptor.TryGetObjectArrayField("Plugins",out var HostPlugins))
				foreach (var HostPlugin in HostPlugins)
					if (HostPlugin.TryGetStringField("Name",out var PluginName) && PluginName=="Traffic" &&
						HostPlugin.TryGetBoolField("Enabled",out var Enabled) && Enabled) WithCityPopulation=true;
		}
		PublicDefinitions.Add("WISEYE_WITH_CITY_POPULATION=" + (WithCityPopulation ? "1" : "0"));
		if (WithCityPopulation) PrivateDependencyModuleNames.Add("MassTraffic");
		if (Target.Platform == UnrealTargetPlatform.Win64) PublicSystemLibraries.AddRange(new string[] { "pdh.lib", "dxgi.lib", "user32.lib" });
		if (Target.bBuildEditor)
		{
			PrivateDependencyModuleNames.Add("UnrealEd");
		}

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });

		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}
