// The Unfinished Confession - base class for everything the player can use with E.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Dom/JsonObject.h"
#include "Core/ConfessionRules.h"
#include "ConfessionInteractable.generated.h"

class UStaticMeshComponent;
class USceneComponent;
class AConfessionCharacter;
class AConfessionGameMode;
struct FConfessionLayout;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FConfessionUsedSignature, AActor*, InstigatorActor);

UCLASS(Blueprintable)
class CONFESSION_API AConfessionInteractable : public AActor
{
	GENERATED_BODY()

public:
	AConfessionInteractable();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Interaction")
	TObjectPtr<USceneComponent> SceneRoot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Interaction")
	TObjectPtr<UStaticMeshComponent> Visual;

	/** Id from the level layout (e.g. "Door_Entrance_01"); used by flags, autopilot and logs. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Interaction")
	FString LayoutId;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interaction")
	FText InteractionLabel;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interaction")
	bool bOneShot = false;

	UPROPERTY(BlueprintAssignable, Category = "Interaction")
	FConfessionUsedSignature OnUsed;

	/** Called by the greybox builder before FinishSpawning. */
	virtual void InitFromLayout(const TSharedPtr<FJsonObject>& Data, const FConfessionLayout& Layout);

	virtual bool CanUse(const AConfessionCharacter* By) const;
	virtual FText GetPrompt(const AConfessionCharacter* By) const;
	/** World point the player (or autopilot) should look at to use this. */
	virtual FVector GetAimPoint() const;

	UFUNCTION(BlueprintCallable, Category = "Interaction")
	void Use(AActor* ByActor);

	/** Re-applies persistent state after a checkpoint respawn. */
	virtual void RestoreFromProgress(const ConfessionRules::ProgressState& State) {}
	/** Level-wide events such as "phone_ring_once". */
	virtual void OnLevelEvent(const FString& EventId) {}

protected:
	virtual void HandleUse(AConfessionCharacter* By) {}
	AConfessionGameMode* GetConfessionGameMode() const;
	/** Sizes Visual as a greybox cube at a world centre (cm) with a layout material. */
	void SetupBox(UStaticMeshComponent* Comp, const FVector& WorldCenterCm, const FVector& SizeCm, const FString& MaterialName,
		const FConfessionLayout& Layout, bool bCollision = true);

private:
	bool bUsed = false;
};
