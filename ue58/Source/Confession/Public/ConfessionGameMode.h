// The Unfinished Confession - level director: loads the layout, owns progress/objectives/checkpoints.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "ConfessionTypes.h"
#include "Core/ConfessionRules.h"
#include "ConfessionGameMode.generated.h"

class AConfessionInteractable;
class AConfessionHUD;
class AConfessionGreyboxBuilder;

UCLASS()
class CONFESSION_API AConfessionGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AConfessionGameMode();

	/** Which Content/Confession/Data/<LevelId>_layout.json to build. Override with -ConfessionLevel=<Id> or a GameMode subclass. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Confession")
	FString LevelId = TEXT("L0_B01");

	/** If the map has no AConfessionGreyboxBuilder, spawn one (lets /Engine/Maps/Entry boot straight into the slice). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Confession")
	bool bAutoSpawnGreybox = true;

	virtual void InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage) override;
	virtual void StartPlay() override;
	virtual void RestartPlayer(AController* NewPlayer) override;

	const FConfessionLayout& GetLayout() const { return Layout; }
	const ConfessionRules::ProgressState& GetProgress() const { return Progress; }

	bool HasItem(const FString& ItemId) const;
	bool HasFlag(const FString& Flag) const;
	void GiveItem(const FString& ItemId);
	void SetFlag(const FString& Flag);
	void FireEvent(const FString& EventId);
	/** Fires once no document is open (+0.8 s), so a beat is not hidden behind a reading panel. */
	void FireEventAfterDocument(const FString& EventId);

	void ShowMessageId(const FString& MessageId);
	void ShowMessage(const FText& Text, float Seconds = 3.5f);
	void ShowDocument(const FString& DocId);
	FText BuildNotebookText() const;

	void ReachCheckpoint(const FString& CheckpointId, const FTransform& Respawn, const FString& Flag);
	UFUNCTION(BlueprintCallable, Category = "Confession")
	void RespawnAtCheckpoint();

	AConfessionInteractable* FindInteractable(const FString& InteractableId) const;
	FText CurrentObjectiveText() const;
	FString CurrentObjectiveId() const;
	FString LastCheckpointId() const { return UTF8_TO_TCHAR(LastCheckpoint.Id.c_str()); }

	UFUNCTION(BlueprintCallable, Category = "Confession")
	void StartAutoPlaytest();

private:
	void OnProgressChanged();
	AConfessionHUD* GetConfessionHUD() const;
	void RestoreWorld();

	FConfessionLayout Layout;
	ConfessionRules::ProgressState Progress;
	ConfessionRules::ObjectiveFlow Flow;
	ConfessionRules::Checkpoint LastCheckpoint;
	TArray<FString> ReadDocuments;
	TSet<FString> ReachedCheckpoints;
	TArray<FString> PendingEvents;
	float PendingEventDelay = 0.0f;
	FTimerHandle PendingEventTimer;
	void PumpPendingEvents();
	FTransform StartTransform;
};
