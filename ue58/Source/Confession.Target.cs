using UnrealBuildTool;
using System.Collections.Generic;

public class ConfessionTarget : TargetRules
{
	public ConfessionTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("Confession");
	}
}
