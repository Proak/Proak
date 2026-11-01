// The Unfinished Confession - items and readable documents (work order, staff card, notice).
#pragma once

#include "CoreMinimal.h"
#include "ConfessionInteractable.h"
#include "ConfessionPickup.generated.h"

class UPointLightComponent;

UCLASS()
class CONFESSION_API AConfessionPickup : public AConfessionInteractable
{
	GENERATED_BODY()

public:
	AConfessionPickup();

	/** Item id added to the inventory; empty for readables that stay in the world. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Pickup")
	FString ItemId;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Pickup")
	FString FlagOnUse;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Pickup")
	FString DocumentId;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Pickup")
	FString SoundId;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Pickup")
	FString EventOnUse;

	/** Small pilot lamp next to the item: a non-text hint (e.g. the card slot). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Pickup")
	TObjectPtr<UPointLightComponent> PilotLight;

	virtual void InitFromLayout(const TSharedPtr<FJsonObject>& Data, const FConfessionLayout& Layout) override;
	virtual void RestoreFromProgress(const ConfessionRules::ProgressState& State) override;
	virtual bool CanUse(const AConfessionCharacter* By) const override;

protected:
	virtual void HandleUse(AConfessionCharacter* By) override;

private:
	bool bConsumes = true;
	bool bHasPilot = false;
	void SetTaken(bool bTaken);
};
