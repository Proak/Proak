using UnrealBuildTool;

public class Confession : ModuleRules
{
	public Confession(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		CppStandard = CppStandardVersion.Cpp20;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput", "Json"
		});
		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"Slate", "SlateCore"
		});
	}
}
