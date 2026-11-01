// The Unfinished Confession - scripted bot playthrough (see header).
#include "ConfessionAutoPilot.h"

#include "ConfessionCharacter.h"
#include "ConfessionGameMode.h"
#include "ConfessionHUD.h"
#include "ConfessionInteractable.h"
#include "ConfessionTypes.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformMisc.h"
#include "Misc/App.h"
#include "Misc/CommandLine.h"
#include "Misc/DateTime.h"
#include "Misc/EngineVersion.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UnrealClient.h"

UConfessionAutoPilot::UConfessionAutoPilot()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = true;
}

void UConfessionAutoPilot::Begin(const FConfessionLayout& Layout)
{
	Ops = Layout.Autopilot;
	LayoutId = Layout.Id + TEXT(" v") + Layout.LayoutVersion;
	ShotsById.Reset();
	for (const TSharedPtr<FJsonObject>& S : Layout.Shots)
	{
		ShotsById.Add(ConfessionData::GetString(S, TEXT("id")), S);
	}
	OpLog.Reset();
	Screenshots.Reset();
	FrameMs.Reset();
	RunDir = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("Confession/Evidence") /
		FDateTime::UtcNow().ToString(TEXT("%Y%m%d_%H%M%S")));
	OpIndex = -1;
	RunTime = 0.0f;
	bPass = false;
	FailReason.Reset();
	bRunning = Ops.Num() > 0;
	UE_LOG(LogConfession, Display, TEXT("[AutoPlaytest] start: %d ops, evidence -> %s"), Ops.Num(), *RunDir);
	if (!bRunning)
	{
		Finish(false, TEXT("layout has no autopilot ops"));
		return;
	}
	NextOp();
}

void UConfessionAutoPilot::NextOp()
{
	++OpIndex;
	Phase = EPhase::Start;
	PhaseTime = 0.0f;
	if (OpIndex >= Ops.Num())
	{
		Finish(true, TEXT("all ops completed"));
	}
}

bool UConfessionAutoPilot::FlagSet(const FString& Flag) const
{
	const AConfessionGameMode* GM = GetWorld()->GetAuthGameMode<AConfessionGameMode>();
	return Flag.IsEmpty() || (GM && GM->HasFlag(Flag));
}

void UConfessionAutoPilot::LogOp(const FString& Result, const FString& Detail)
{
	TSharedPtr<FJsonObject> E = MakeShared<FJsonObject>();
	const TSharedPtr<FJsonObject>& Op = Ops.IsValidIndex(OpIndex) ? Ops[OpIndex] : nullptr;
	E->SetNumberField(TEXT("index"), OpIndex);
	E->SetStringField(TEXT("op"), ConfessionData::GetString(Op, TEXT("op")));
	E->SetStringField(TEXT("arg"), ConfessionData::GetString(Op, TEXT("target"), ConfessionData::GetString(Op, TEXT("shot"))));
	E->SetStringField(TEXT("result"), Result);
	E->SetStringField(TEXT("detail"), Detail);
	E->SetNumberField(TEXT("t"), RunTime);
	if (const AActor* Owner = GetOwner())
	{
		E->SetStringField(TEXT("pawn_location_cm"), Owner->GetActorLocation().ToString());
	}
	OpLog.Add(MakeShared<FJsonValueObject>(E));
	UE_LOG(LogConfession, Display, TEXT("[AutoPlaytest] op %d %s: %s %s"), OpIndex, *E->GetStringField(TEXT("op")), *Result, *Detail);
}

void UConfessionAutoPilot::AimAt(const FVector& WorldPoint, float DeltaTime, float Rate)
{
	AConfessionCharacter* C = Cast<AConfessionCharacter>(GetOwner());
	AController* Ctrl = C ? C->GetController() : nullptr;
	if (!Ctrl || !C->FirstPersonCamera)
	{
		return;
	}
	const FRotator Desired = (WorldPoint - C->FirstPersonCamera->GetComponentLocation()).Rotation();
	Ctrl->SetControlRotation(FMath::RInterpTo(Ctrl->GetControlRotation(), Desired, DeltaTime, Rate));
}

void UConfessionAutoPilot::RequestScreenshot(const FString& Name)
{
	const FString Path = RunDir / (Name + TEXT(".png"));
	FScreenshotRequest::RequestScreenshot(Path, false, false);
	Screenshots.Add(Path);
}

void UConfessionAutoPilot::Fail(const FString& Reason)
{
	LogOp(TEXT("FAIL"), Reason);
	Finish(false, Reason);
}

void UConfessionAutoPilot::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	if (!bRunning)
	{
		return;
	}
	RunTime += DeltaTime;
	PhaseTime += DeltaTime;
	FrameMs.Add(DeltaTime * 1000.0f);

	AConfessionCharacter* C = Cast<AConfessionCharacter>(GetOwner());
	AConfessionGameMode* GM = GetWorld()->GetAuthGameMode<AConfessionGameMode>();
	APlayerController* PC = C ? Cast<APlayerController>(C->GetController()) : nullptr;
	if (!C || !GM || !PC)
	{
		Finish(false, TEXT("lost player/game mode"));
		return;
	}
	const TSharedPtr<FJsonObject> Op = Ops[OpIndex];
	const FString Kind = ConfessionData::GetString(Op, TEXT("op"));
	const FString ExpectFlag = ConfessionData::GetString(Op, TEXT("expect_flag"));

	if (Kind == TEXT("goto"))
	{
		const FVector2D To = ConfessionData::GetVec2(Op, TEXT("to"));
		const FVector Target = ConfessionData::ToUE(FVector(To.X, To.Y, 0.0));
		FVector Delta = Target - C->GetActorLocation();
		Delta.Z = 0.0;
		const double Dist = Delta.Size();
		if (Phase == EPhase::Start)
		{
			if (Dist <= ArriveRadiusCm)
			{
				Phase = EPhase::Verify;
				PhaseTime = 0.0f;
			}
			else if (PhaseTime > GotoTimeout)
			{
				Fail(FString::Printf(TEXT("stuck: %.0f cm short of (%.2f, %.2f) m after %.0f s"), Dist, To.X, To.Y, GotoTimeout));
			}
			else
			{
				AimAt(Target + FVector(0.0, 0.0, 165.0), DeltaTime, 6.0f);
				C->AutopilotMove(Delta, Dist < 90.0 ? 0.45f : 1.0f);
			}
		}
		else if (FlagSet(ExpectFlag))
		{
			LogOp(TEXT("OK"), ExpectFlag.IsEmpty() ? TEXT("arrived") : (TEXT("arrived, flag ") + ExpectFlag));
			NextOp();
		}
		else if (PhaseTime > 1.5f)
		{
			Fail(FString::Printf(TEXT("arrived but flag '%s' not set (trigger volume missed?)"), *ExpectFlag));
		}
		return;
	}

	if (Kind == TEXT("use"))
	{
		const FString TargetId = ConfessionData::GetString(Op, TEXT("target"));
		AConfessionInteractable* Target = GM->FindInteractable(TargetId);
		if (!Target)
		{
			Fail(TEXT("target not found: ") + TargetId);
			return;
		}
		switch (Phase)
		{
		case EPhase::Start:
		case EPhase::Aim:
			Phase = EPhase::Aim;
			AimAt(Target->GetAimPoint(), DeltaTime, 10.0f);
			if (PhaseTime > 0.6f && C->GetFocused() == Target)
			{
				Phase = EPhase::Act;
			}
			else if (PhaseTime > 2.0f)
			{
				const AConfessionInteractable* F = C->GetFocused();
				Fail(FString::Printf(TEXT("focus trace does not reach %s (focused: %s, distance %.0f cm)"), *TargetId,
					F ? *F->LayoutId : TEXT("nothing"), (Target->GetAimPoint() - C->FirstPersonCamera->GetComponentLocation()).Size()));
			}
			break;
		case EPhase::Act:
			C->TryUse();
			Phase = EPhase::Verify;
			PhaseTime = 0.0f;
			break;
		case EPhase::Verify:
		{
			AConfessionHUD* HUD = Cast<AConfessionHUD>(PC->GetHUD());
			if (HUD && HUD->IsDocumentOpen() && PhaseTime > 1.0f)
			{
				HUD->CloseDocument(); // like pressing E after reading
			}
			if (FlagSet(ExpectFlag) && PhaseTime > 0.3f && !(HUD && HUD->IsDocumentOpen()))
			{
				LogOp(TEXT("OK"), ExpectFlag.IsEmpty() ? TEXT("used") : (TEXT("used, flag ") + ExpectFlag));
				NextOp();
			}
			else if (PhaseTime > 3.0f)
			{
				Fail(FString::Printf(TEXT("used %s but flag '%s' not set"), *TargetId, *ExpectFlag));
			}
			break;
		}
		default:
			break;
		}
		return;
	}

	if (Kind == TEXT("wait"))
	{
		if (PhaseTime >= static_cast<float>(ConfessionData::GetNumber(Op, TEXT("seconds"), 1.0)))
		{
			LogOp(TEXT("OK"), TEXT("waited"));
			NextOp();
		}
		return;
	}

	if (Kind == TEXT("screenshot"))
	{
		const FString ShotId = ConfessionData::GetString(Op, TEXT("shot"));
		const TSharedPtr<FJsonObject>* Shot = ShotsById.Find(ShotId);
		if (Phase == EPhase::Start)
		{
			RequestScreenshot(TEXT("fp_") + ShotId); // what the player actually sees at this moment
			Phase = EPhase::Shot;
			PhaseTime = 0.0f;
			if (Shot)
			{
				const FVector Cam = ConfessionData::ToUE(ConfessionData::GetVec3(*Shot, TEXT("camera")));
				const FVector Aim = ConfessionData::ToUE(ConfessionData::GetVec3(*Shot, TEXT("aim")));
				if (!ShotCamera)
				{
					ShotCamera = GetWorld()->SpawnActor<ACameraActor>(ACameraActor::StaticClass(), FTransform::Identity);
				}
				ShotCamera->SetActorLocationAndRotation(Cam, (Aim - Cam).Rotation());
				ShotCamera->GetCameraComponent()->SetFieldOfView(C->FirstPersonCamera->FieldOfView);
				ShotCamera->GetCameraComponent()->bConstrainAspectRatio = false;
			}
		}
		else if (Phase == EPhase::Shot)
		{
			if (Shot && PhaseTime > 0.3f && PC->GetViewTarget() != ShotCamera)
			{
				PC->SetViewTarget(ShotCamera);
				PhaseTime = 0.0f;
				Phase = EPhase::Verify;
			}
			else if (!Shot && PhaseTime > 0.3f)
			{
				LogOp(TEXT("WARN"), TEXT("shot id not in layout; first-person capture only"));
				NextOp();
			}
		}
		else if (Phase == EPhase::Verify)
		{
			// Give auto-exposure ~1.5 s to settle on the fixed camera before capturing.
			if (PhaseTime > 1.5f && PhaseTime - DeltaTime <= 1.5f)
			{
				RequestScreenshot(ShotId);
			}
			if (PhaseTime > 2.1f)
			{
				PC->SetViewTarget(C);
				LogOp(TEXT("OK"), TEXT("captured fp_") + ShotId + TEXT(" and ") + ShotId);
				NextOp();
			}
		}
		return;
	}

	Fail(TEXT("unknown op: ") + Kind);
}

void UConfessionAutoPilot::Finish(bool bInPass, const FString& Reason)
{
	bRunning = false;
	bPass = bInPass;
	FailReason = bInPass ? FString() : Reason;
	if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
	{
		if (PC->GetPawn())
		{
			PC->SetViewTarget(PC->GetPawn());
		}
	}
	WriteReport();
	UE_LOG(LogConfession, Display, TEXT("[AutoPlaytest] RESULT %s (%s) after %.1f s"), bPass ? TEXT("PASS") : TEXT("FAIL"), *Reason, RunTime);
	if (AConfessionGameMode* GM = GetWorld()->GetAuthGameMode<AConfessionGameMode>())
	{
		GM->ShowMessage(FText::FromString(FString::Printf(TEXT("AutoPlaytest %s: %s"), bPass ? TEXT("PASS") : TEXT("FAIL"), *Reason)), 8.0f);
	}
	if (FParse::Param(FCommandLine::Get(), TEXT("ConfessionAutoQuit")))
	{
		FPlatformMisc::RequestExitWithStatus(false, bPass ? 0 : 1);
	}
}

void UConfessionAutoPilot::WriteReport()
{
	TArray<float> Sorted = FrameMs;
	Sorted.Sort();
	float Sum = 0.0f;
	for (float V : Sorted) { Sum += V; }
	const int32 N = Sorted.Num();
	const float Avg = N ? Sum / static_cast<float>(N) : 0.0f;
	const float P99 = N ? Sorted[FMath::Clamp(static_cast<int32>(static_cast<float>(N) * 0.99f), 0, N - 1)] : 0.0f;
	const float Max = N ? Sorted.Last() : 0.0f;

	TSharedRef<FJsonObject> R = MakeShared<FJsonObject>();
	R->SetStringField(TEXT("kind"), TEXT("UE_RUNTIME_AUTOPLAYTEST"));
	R->SetStringField(TEXT("result"), bPass ? TEXT("PASS") : TEXT("FAIL"));
	R->SetStringField(TEXT("reason"), bPass ? TEXT("all ops completed") : FailReason);
	R->SetStringField(TEXT("layout"), LayoutId);
	R->SetStringField(TEXT("engine_version"), FEngineVersion::Current().ToString());
	R->SetStringField(TEXT("rhi"), FApp::GetGraphicsRHI());
	R->SetStringField(TEXT("cpu"), FPlatformMisc::GetCPUBrand());
	R->SetStringField(TEXT("gpu"), FPlatformMisc::GetPrimaryGPUBrand());
	R->SetStringField(TEXT("utc"), FDateTime::UtcNow().ToIso8601());
	R->SetStringField(TEXT("command_line"), FCommandLine::Get());
	R->SetNumberField(TEXT("run_seconds"), RunTime);
	R->SetNumberField(TEXT("frames"), N);
	R->SetNumberField(TEXT("frame_ms_avg"), Avg);
	R->SetNumberField(TEXT("frame_ms_p99"), P99);
	R->SetNumberField(TEXT("frame_ms_max"), Max);
	R->SetArrayField(TEXT("ops"), OpLog);
	TArray<TSharedPtr<FJsonValue>> Shots;
	for (const FString& S : Screenshots) { Shots.Add(MakeShared<FJsonValueString>(S)); }
	R->SetArrayField(TEXT("screenshots_requested"), Shots);
	R->SetStringField(TEXT("note"), TEXT("Bot run proves reachability/interaction/flow in this build. It does not measure fun, fear, readability for humans or art quality."));

	FString Out;
	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Out);
	FJsonSerializer::Serialize(R, Writer);
	const FString Path = RunDir / TEXT("autoplaytest.json");
	FFileHelper::SaveStringToFile(Out, *Path, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	UE_LOG(LogConfession, Display, TEXT("[AutoPlaytest] report: %s"), *Path);
}
