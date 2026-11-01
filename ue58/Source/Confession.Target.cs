using UnrealBuildTool;
using System.Collections.Generic;
public class ConfessionTarget : TargetRules {
    public ConfessionTarget(TargetInfo Target) : base(Target) {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.V5;
        ExtraModuleNames.Add("Confession");
    }
}
