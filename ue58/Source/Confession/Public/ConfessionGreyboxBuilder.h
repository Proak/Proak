// The Unfinished Confession - builds a playable greybox level from the layout JSON at runtime.
// Lets the project boot into a playable L0_B01 from an empty map, before any .umap is authored.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Engine/TimerHandle.h"
#include "ConfessionGreyboxBuilder.generated.h"

class UStaticMeshComponent;
class UAudioComponent;
struct FConfessionLayout;

UCLASS()
class CONFESSION_API AConfessionGreyboxBuilder : public AActor
{
	GENERATED_BODY()

public:
	AConfessionGreyboxBuilder();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

	/** Number of boxes/lights/interactables created (for logs and the autopilot report). */
	int32 NumBoxes = 0;
	int32 NumLights = 0;
	int32 NumInteractables = 0;

private:
	void Build(const FConfessionLayout& Layout);
	void BuildGeometry(const FConfessionLayout& Layout);
	void BuildLights(const FConfessionLayout& Layout);
	void BuildEnvironment(const FConfessionLayout& Layout);
	void BuildAudio(const FConfessionLayout& Layout);
	void SpawnInteractables(const FConfessionLayout& Layout);
	void ScheduleIntervalSound(int32 EmitterIndex);

	struct FIntervalEmitter
	{
		FString SoundId;
		FVector Location;
		float Volume = 1.0f;
		float RadiusCm = 1500.0f;
		FVector2D IntervalSeconds = FVector2D(20.0, 40.0);
		FVector2D FirstDelaySeconds = FVector2D(-1.0, -1.0);
		bool bFirstDone = false;
	};
	TArray<FIntervalEmitter> IntervalEmitters;
	TArray<FTimerHandle> IntervalTimers;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UActorComponent>> Generated;

	UPROPERTY(Transient)
	TArray<TObjectPtr<AActor>> SpawnedActors;
};
