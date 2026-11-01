// The Unfinished Confession - in-engine automation tests (no world needed).
// Run: UnrealEditor-Cmd Confession.uproject -ExecCmds="Automation RunTests Confession; Quit" -unattended -nullrhi
#include "ConfessionAudio.h"
#include "ConfessionTypes.h"
#include "Core/ConfessionRules.h"
#include "HAL/FileManager.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#define ConfessionTestFlags (EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter)

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FConfessionLayoutLoads, "Confession.Data.L0_B01.LayoutLoads", ConfessionTestFlags)
bool FConfessionLayoutLoads::RunTest(const FString& Parameters)
{
	FConfessionLayout L;
	FString Error;
	const bool bOk = L.LoadFromFile(FConfessionLayout::PathFor(TEXT("L0_B01")), Error);
	TestTrue(FString::Printf(TEXT("layout loads (%s)"), *Error), bOk);
	if (!bOk)
	{
		return false;
	}
	TestTrue(TEXT("has geometry"), L.Geometry.Num() > 50);
	TestTrue(TEXT("has flow"), L.Flow.Num() >= 4);
	TestTrue(TEXT("start is inside the arcade (south of the lobby)"), L.PlayerStartCm.Y > 950.0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FConfessionFlowIsCompletable, "Confession.Data.L0_B01.EveryObjectiveFlagHasASource", ConfessionTestFlags)
bool FConfessionFlowIsCompletable::RunTest(const FString& Parameters)
{
	FConfessionLayout L;
	FString Error;
	if (!L.LoadFromFile(FConfessionLayout::PathFor(TEXT("L0_B01")), Error))
	{
		AddError(Error);
		return false;
	}
	// A flow step whose flag nothing can set is a guaranteed soft-lock.
	TSet<FString> Settable;
	for (const TSharedPtr<FJsonObject>& I : L.Interactables)
	{
		Settable.Add(ConfessionData::GetString(I, TEXT("sets_flag")));
		Settable.Add(ConfessionData::GetString(I, TEXT("sets_flag_on_open")));
	}
	for (const TSharedPtr<FJsonObject>& F : L.Flow)
	{
		const FString Flag = ConfessionData::GetString(F, TEXT("complete_on"));
		if (!Flag.IsEmpty())
		{
			TestTrue(FString::Printf(TEXT("flag '%s' is set by some interactable"), *Flag), Settable.Contains(Flag));
		}
	}
	// Every door item must be obtainable.
	TSet<FString> Items;
	for (const TSharedPtr<FJsonObject>& I : L.Interactables)
	{
		Items.Add(ConfessionData::GetString(I, TEXT("item")));
	}
	for (const TSharedPtr<FJsonObject>& I : L.Interactables)
	{
		const FString Need = ConfessionData::GetString(I, TEXT("requires_item"));
		if (!Need.IsEmpty())
		{
			TestTrue(FString::Printf(TEXT("required item '%s' exists as a pickup"), *Need), Items.Contains(Need));
		}
	}
	// Every autopilot target exists.
	for (const TSharedPtr<FJsonObject>& Op : L.Autopilot)
	{
		const FString Target = ConfessionData::GetString(Op, TEXT("target"));
		if (!Target.IsEmpty())
		{
			TestTrue(FString::Printf(TEXT("autopilot target '%s' exists"), *Target), L.FindInteractable(Target).IsValid());
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FConfessionSoundsExist, "Confession.Data.L0_B01.ReferencedSoundsExist", ConfessionTestFlags)
bool FConfessionSoundsExist::RunTest(const FString& Parameters)
{
	FConfessionLayout L;
	FString Error;
	if (!L.LoadFromFile(FConfessionLayout::PathFor(TEXT("L0_B01")), Error))
	{
		AddError(Error);
		return false;
	}
	TSet<FString> Ids = {TEXT("door_reject"), TEXT("door_release"), TEXT("door_open"), TEXT("phone_ring"), TEXT("phone_pickup"),
		TEXT("dial_tone"), TEXT("checkpoint_soft"), TEXT("footstep_concrete_01"), TEXT("footstep_concrete_06")};
	for (const TSharedPtr<FJsonObject>& E : L.AudioEmitters) { Ids.Add(ConfessionData::GetString(E, TEXT("sound"))); }
	for (const TSharedPtr<FJsonObject>& I : L.Interactables)
	{
		const FString S = ConfessionData::GetString(I, TEXT("sound"));
		if (!S.IsEmpty()) { Ids.Add(S); }
	}
	for (const FString& Id : Ids)
	{
		TestTrue(FString::Printf(TEXT("sound file for '%s'"), *Id),
			IFileManager::Get().FileExists(*UConfessionAudioSubsystem::PathFor(Id)));
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FConfessionRulesInEngine, "Confession.Rules.EntranceDoorSequence", ConfessionTestFlags)
bool FConfessionRulesInEngine::RunTest(const FString& Parameters)
{
	// Same rules core as tests/core, compiled with the engine toolchain.
	using namespace ConfessionRules;
	DoorLock D(LockMode::RejectOnceThenRelease, 1.4, 1.2);
	TestTrue(TEXT("no item -> NeedItem"), D.Use(false) == UseResult::NeedItem);
	TestTrue(TEXT("item -> Rejected (shows previous number)"), D.Use(true) == UseResult::Rejected);
	for (int32 i = 0; i < 100; ++i) { D.Tick(1.0 / 60.0); }
	TestTrue(TEXT("latch releases by itself"), D.GetState() == DoorState::Unlocked);
	TestTrue(TEXT("push opens"), D.Use(true) == UseResult::Opening);
	return true;
}

#undef ConfessionTestFlags

#endif // WITH_DEV_AUTOMATION_TESTS
