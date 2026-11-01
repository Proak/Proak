// The Unfinished Confession - checkpoint volumes, ringing phones, and the "moves when unobserved" anomaly.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ConfessionInteractable.h"
#include "ConfessionWorldActors.generated.h"

class UBoxComponent;
class UAudioComponent;

/** Silent trigger volume: snapshot progress + respawn transform the first time the player enters. */
UCLASS()
class CONFESSION_API AConfessionCheckpoint : public AActor
{
	GENERATED_BODY()

public:
	AConfessionCheckpoint();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Checkpoint")
	TObjectPtr<UBoxComponent> Volume;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Checkpoint")
	FString LayoutId;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Checkpoint")
	FString FlagOnReach;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Checkpoint")
	FTransform Respawn;

	void InitFromLayout(const TSharedPtr<FJsonObject>& Data);

protected:
	virtual void NotifyActorBeginOverlap(AActor* OtherActor) override;
};

/** Desk / wall phone. Rings once on a level event; answering may make another phone ring elsewhere. */
UCLASS()
class CONFESSION_API AConfessionPhone : public AConfessionInteractable
{
	GENERATED_BODY()

public:
	AConfessionPhone();

	virtual void InitFromLayout(const TSharedPtr<FJsonObject>& Data, const FConfessionLayout& Layout) override;
	virtual bool CanUse(const AConfessionCharacter* By) const override;
	virtual void OnLevelEvent(const FString& EventId) override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void RestoreFromProgress(const ConfessionRules::ProgressState& State) override;

	void StartRinging();
	bool IsRinging() const { return RingWindow > 0.0f; }

protected:
	virtual void HandleUse(AConfessionCharacter* By) override;

private:
	FString RingEvent;
	FString AnswerMessage;
	FString RelayTo;
	float RelayDelay = 2.5f;
	float RelayTimer = -1.0f;
	float RingWindow = 0.0f; // seconds the phone can still be answered
};

/** DIRECTOR_BEAT_SHEET key moment 01: shifts once, only after being seen and then not seen. */
UCLASS()
class CONFESSION_API AConfessionDisplacementAnomaly : public AConfessionInteractable
{
	GENERATED_BODY()

public:
	AConfessionDisplacementAnomaly();

	virtual void InitFromLayout(const TSharedPtr<FJsonObject>& Data, const FConfessionLayout& Layout) override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void RestoreFromProgress(const ConfessionRules::ProgressState& State) override;

protected:
	virtual void HandleUse(AConfessionCharacter* By) override;

private:
	bool IsInPlayerView() const;
	ConfessionRules::DisplacementAnomaly Rule;
	FVector HomeLocation = FVector::ZeroVector;
	FVector OffsetCm = FVector::ZeroVector;
	float SeenWithinCm = 450.0f;
	FString DocumentId;
};
