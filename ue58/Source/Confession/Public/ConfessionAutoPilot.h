// The Unfinished Confession - scripted bot playthrough that uses the REAL movement, collision and
// interaction code (it steers the character and presses "use"; it never teleports).
// Writes a JSON report + screenshots to Saved/Confession/Evidence/<run>/ and, with
// -ConfessionAutoQuit, exits the process with code 0 (PASS) or 1 (FAIL) for CI.
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Dom/JsonObject.h"
#include "ConfessionAutoPilot.generated.h"

class ACameraActor;
class AConfessionCharacter;
struct FConfessionLayout;

UCLASS(ClassGroup = (Confession))
class CONFESSION_API UConfessionAutoPilot : public UActorComponent
{
	GENERATED_BODY()

public:
	UConfessionAutoPilot();

	void Begin(const FConfessionLayout& Layout);
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	bool IsRunning() const { return bRunning; }

	/** Seconds allowed per "goto" before the run fails as stuck. */
	float GotoTimeout = 15.0f;
	float ArriveRadiusCm = 22.0f;

private:
	enum class EPhase : uint8 { Start, Aim, Act, Verify, Shot };

	void NextOp();
	void Fail(const FString& Reason);
	void Finish(bool bPass, const FString& Reason);
	void LogOp(const FString& Result, const FString& Detail);
	bool FlagSet(const FString& Flag) const;
	void AimAt(const FVector& WorldPoint, float DeltaTime, float Rate);
	void RequestScreenshot(const FString& Name);
	void WriteReport();

	TArray<TSharedPtr<FJsonObject>> Ops;
	TMap<FString, TSharedPtr<FJsonObject>> ShotsById;
	TArray<TSharedPtr<FJsonValue>> OpLog;
	TArray<FString> Screenshots;
	int32 OpIndex = -1;
	EPhase Phase = EPhase::Start;
	float PhaseTime = 0.0f;
	float RunTime = 0.0f;
	bool bRunning = false;
	bool bPass = false;
	FString FailReason;
	FString RunDir;
	FString LayoutId;

	// frame-time statistics over the run (ms)
	TArray<float> FrameMs;

	UPROPERTY(Transient)
	TObjectPtr<ACameraActor> ShotCamera;
};
