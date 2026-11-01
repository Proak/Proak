// The Unfinished Confession - level director.
#include "ConfessionGameMode.h"

#include "ConfessionAudio.h"
#include "ConfessionAutoPilot.h"
#include "ConfessionCharacter.h"
#include "ConfessionGreyboxBuilder.h"
#include "ConfessionHUD.h"
#include "ConfessionInteractable.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "TimerManager.h"

namespace
{
AConfessionGameMode* GameModeOf(UWorld* World)
{
	return World ? World->GetAuthGameMode<AConfessionGameMode>() : nullptr;
}

FAutoConsoleCommandWithWorld GCmdRespawn(TEXT("Confession.Respawn"),
	TEXT("Return to the last checkpoint (restores items/flags/doors as they were)."),
	FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
	{
		if (AConfessionGameMode* GM = GameModeOf(World)) { GM->RespawnAtCheckpoint(); }
	}));

FAutoConsoleCommandWithWorld GCmdAutoPlaytest(TEXT("Confession.AutoPlaytest"),
	TEXT("Run the scripted bot route from the layout (real movement + interaction); writes Saved/Confession/Evidence/<run>/."),
	FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
	{
		if (AConfessionGameMode* GM = GameModeOf(World)) { GM->StartAutoPlaytest(); }
	}));

FAutoConsoleCommandWithWorld GCmdDump(TEXT("Confession.DumpState"),
	TEXT("Log items, flags, objective and checkpoint."),
	FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
	{
		AConfessionGameMode* GM = GameModeOf(World);
		if (!GM) { return; }
		FString Items, Flags;
		for (const std::string& S : GM->GetProgress().Items) { Items += UTF8_TO_TCHAR(S.c_str()); Items += TEXT(" "); }
		for (const std::string& S : GM->GetProgress().Flags) { Flags += UTF8_TO_TCHAR(S.c_str()); Flags += TEXT(" "); }
		UE_LOG(LogConfession, Display, TEXT("Objective=%s Checkpoint=%s Items=[%s] Flags=[%s]"),
			*GM->CurrentObjectiveId(), *GM->LastCheckpointId(), *Items, *Flags);
	}));
} // namespace

AConfessionGameMode::AConfessionGameMode()
{
	DefaultPawnClass = AConfessionCharacter::StaticClass();
	HUDClass = AConfessionHUD::StaticClass();
}

void AConfessionGameMode::InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage)
{
	Super::InitGame(MapName, Options, ErrorMessage);

	FString Override;
	if (FParse::Value(FCommandLine::Get(), TEXT("ConfessionLevel="), Override))
	{
		LevelId = Override;
	}
	FString Error;
	const FString Path = FConfessionLayout::PathFor(LevelId);
	if (!Layout.LoadFromFile(Path, Error))
	{
		UE_LOG(LogConfession, Error, TEXT("Layout load failed: %s"), *Error);
		return;
	}
	UE_LOG(LogConfession, Display, TEXT("Layout %s v%s: %d boxes, %d interactables, %d flow steps (%s)"), *Layout.Id,
		*Layout.LayoutVersion, Layout.Geometry.Num(), Layout.Interactables.Num(), Layout.Flow.Num(), *Path);

	std::vector<ConfessionRules::ObjectiveStep> Steps;
	for (const TSharedPtr<FJsonObject>& F : Layout.Flow)
	{
		Steps.push_back({ConfessionData::ToStd(ConfessionData::GetString(F, TEXT("id"))),
			ConfessionData::ToStd(ConfessionData::GetString(F, TEXT("complete_on")))});
	}
	Flow.SetSteps(std::move(Steps));

	// Capsule half height 92 cm: spawn the capsule centre just above the floor.
	StartTransform = FTransform(FRotator(0.0f, Layout.PlayerStartYawDeg, 0.0f), Layout.PlayerStartCm + FVector(0.0, 0.0, 94.0));

	if (bAutoSpawnGreybox)
	{
		bool bHasBuilder = false;
		for (TActorIterator<AConfessionGreyboxBuilder> It(GetWorld()); It; ++It)
		{
			bHasBuilder = true;
		}
		if (!bHasBuilder)
		{
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			GetWorld()->SpawnActor<AConfessionGreyboxBuilder>(AConfessionGreyboxBuilder::StaticClass(), FTransform::Identity, Params);
		}
	}
}

void AConfessionGameMode::StartPlay()
{
	Super::StartPlay();
	OnProgressChanged();
	if (FParse::Param(FCommandLine::Get(), TEXT("ConfessionAutoPlaytest")))
	{
		FTimerHandle Handle;
		GetWorldTimerManager().SetTimer(Handle, this, &AConfessionGameMode::StartAutoPlaytest, 2.0f, false);
	}
}

void AConfessionGameMode::RestartPlayer(AController* NewPlayer)
{
	if (!NewPlayer || !Layout.bValid)
	{
		Super::RestartPlayer(NewPlayer);
		return;
	}
	RestartPlayerAtTransform(NewPlayer, StartTransform);
}

bool AConfessionGameMode::HasItem(const FString& ItemId) const { return Progress.HasItem(ConfessionData::ToStd(ItemId)); }
bool AConfessionGameMode::HasFlag(const FString& Flag) const { return Progress.HasFlag(ConfessionData::ToStd(Flag)); }

void AConfessionGameMode::GiveItem(const FString& ItemId)
{
	if (ItemId.IsEmpty()) { return; }
	Progress.AddItem(ConfessionData::ToStd(ItemId));
	OnProgressChanged();
}

void AConfessionGameMode::SetFlag(const FString& Flag)
{
	if (Flag.IsEmpty() || HasFlag(Flag)) { return; }
	Progress.SetFlag(ConfessionData::ToStd(Flag));
	UE_LOG(LogConfession, Log, TEXT("[Flag] %s"), *Flag);
	OnProgressChanged();
}

void AConfessionGameMode::FireEvent(const FString& EventId)
{
	UE_LOG(LogConfession, Log, TEXT("[Event] %s"), *EventId);
	for (TActorIterator<AConfessionInteractable> It(GetWorld()); It; ++It)
	{
		It->OnLevelEvent(EventId);
	}
}

AConfessionHUD* AConfessionGameMode::GetConfessionHUD() const
{
	const APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	return PC ? Cast<AConfessionHUD>(PC->GetHUD()) : nullptr;
}

void AConfessionGameMode::ShowMessage(const FText& Text, float Seconds)
{
	if (Text.IsEmpty()) { return; }
	if (AConfessionHUD* HUD = GetConfessionHUD()) { HUD->ShowMessage(Text, Seconds); }
	UE_LOG(LogConfession, Log, TEXT("[Message] %s"), *Text.ToString());
}

void AConfessionGameMode::ShowMessageId(const FString& MessageId) { ShowMessage(Layout.Message(MessageId)); }

void AConfessionGameMode::ShowDocument(const FString& DocId)
{
	FText Title, Body;
	if (!Layout.Document(DocId, Title, Body)) { return; }
	ReadDocuments.AddUnique(DocId);
	if (AConfessionHUD* HUD = GetConfessionHUD()) { HUD->OpenDocument(Title, Body); }
}

FText AConfessionGameMode::BuildNotebookText() const
{
	FString Out;
	const FText Objective = CurrentObjectiveText();
	Out += Layout.Message(TEXT("ui_current")).ToString() + Objective.ToString() + TEXT("\n\n");
	for (const FString& DocId : ReadDocuments)
	{
		FText Title, Body;
		if (Layout.Document(DocId, Title, Body))
		{
			Out += TEXT("- ") + Title.ToString() + TEXT("\n  ") + Body.ToString() + TEXT("\n\n");
		}
	}
	return FText::FromString(Out);
}

FText AConfessionGameMode::CurrentObjectiveText() const
{
	const int32 Index = Progress.ObjectiveIndex;
	return Layout.Flow.IsValidIndex(Index) ? ConfessionData::Localized(Layout.Flow[Index], TEXT("text")) : FText::GetEmpty();
}

FString AConfessionGameMode::CurrentObjectiveId() const
{
	const int32 Index = Progress.ObjectiveIndex;
	return Layout.Flow.IsValidIndex(Index) ? ConfessionData::GetString(Layout.Flow[Index], TEXT("id")) : FString();
}

void AConfessionGameMode::OnProgressChanged()
{
	const bool bChanged = Flow.Advance(Progress);
	if (bChanged || Progress.ObjectiveIndex == 0)
	{
		if (AConfessionHUD* HUD = GetConfessionHUD()) { HUD->ShowObjective(CurrentObjectiveText()); }
		UE_LOG(LogConfession, Log, TEXT("[Objective] %s"), *CurrentObjectiveId());
		const ConfessionRules::ObjectiveStep* Step = Flow.Current(Progress);
		if (bChanged && Step && Step->CompleteOnFlag.empty())
		{
			ShowMessageId(TEXT("msg_slice_end"));
		}
	}
}

void AConfessionGameMode::ReachCheckpoint(const FString& CheckpointId, const FTransform& Respawn, const FString& Flag)
{
	const std::string Id = ConfessionData::ToStd(CheckpointId);
	if (LastCheckpoint.bValid && LastCheckpoint.Id == Id)
	{
		return;
	}
	SetFlag(Flag); // before the snapshot so the respawned state includes it
	LastCheckpoint.Id = Id;
	LastCheckpoint.State = Progress;
	LastCheckpoint.Location = {Respawn.GetLocation().X, Respawn.GetLocation().Y, Respawn.GetLocation().Z + 94.0};
	LastCheckpoint.YawDeg = Respawn.Rotator().Yaw;
	LastCheckpoint.bValid = true;
	if (UConfessionAudioSubsystem* Audio = GetWorld()->GetSubsystem<UConfessionAudioSubsystem>())
	{
		if (const APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0))
		{
			Audio->PlayAt(TEXT("checkpoint_soft"), Pawn->GetActorLocation(), 0.35f, 400.0f);
		}
	}
	if (AConfessionHUD* HUD = GetConfessionHUD()) { HUD->PulseCheckpoint(Layout.Message(TEXT("msg_checkpoint"))); }
	UE_LOG(LogConfession, Log, TEXT("[Checkpoint] %s"), *CheckpointId);
}

void AConfessionGameMode::RestoreWorld()
{
	for (TActorIterator<AConfessionInteractable> It(GetWorld()); It; ++It)
	{
		It->RestoreFromProgress(Progress);
	}
}

void AConfessionGameMode::RespawnAtCheckpoint()
{
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	ACharacter* Character = PC ? Cast<ACharacter>(PC->GetPawn()) : nullptr;
	if (!Character) { return; }
	FVector Loc = StartTransform.GetLocation();
	float Yaw = StartTransform.Rotator().Yaw;
	if (LastCheckpoint.bValid)
	{
		Progress = LastCheckpoint.State;
		Loc = FVector(LastCheckpoint.Location.X, LastCheckpoint.Location.Y, LastCheckpoint.Location.Z);
		Yaw = static_cast<float>(LastCheckpoint.YawDeg);
	}
	else
	{
		Progress = ConfessionRules::ProgressState();
		ReadDocuments.Reset();
	}
	Character->GetCharacterMovement()->StopMovementImmediately();
	Character->SetActorLocationAndRotation(Loc, FRotator(0.0f, Yaw, 0.0f), false, nullptr, ETeleportType::TeleportPhysics);
	PC->SetControlRotation(FRotator(0.0f, Yaw, 0.0f));
	RestoreWorld();
	OnProgressChanged();
	if (AConfessionHUD* HUD = GetConfessionHUD()) { HUD->ShowObjective(CurrentObjectiveText()); }
	UE_LOG(LogConfession, Log, TEXT("[Respawn] at %s"), *LastCheckpointId());
}

AConfessionInteractable* AConfessionGameMode::FindInteractable(const FString& InteractableId) const
{
	for (TActorIterator<AConfessionInteractable> It(GetWorld()); It; ++It)
	{
		if (It->LayoutId == InteractableId) { return *It; }
	}
	return nullptr;
}

void AConfessionGameMode::StartAutoPlaytest()
{
	APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!Pawn)
	{
		UE_LOG(LogConfession, Error, TEXT("[AutoPlaytest] no player pawn"));
		return;
	}
	UConfessionAutoPilot* Pilot = Pawn->FindComponentByClass<UConfessionAutoPilot>();
	if (!Pilot)
	{
		Pilot = NewObject<UConfessionAutoPilot>(Pawn, TEXT("ConfessionAutoPilot"));
		Pilot->RegisterComponent();
	}
	Pilot->Begin(Layout);
}
