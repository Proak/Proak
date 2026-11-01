// The Unfinished Confession - hinged doors with access readers (entrance gate, basement service door).
#pragma once

#include "CoreMinimal.h"
#include "ConfessionInteractable.h"
#include "ConfessionDoor.generated.h"

class UPointLightComponent;
class UStaticMeshComponent;
class USceneComponent;
class AConfessionGameMode;

UCLASS()
class CONFESSION_API AConfessionDoor : public AConfessionInteractable
{
	GENERATED_BODY()

public:
	AConfessionDoor();

	/** Rotates around Z; Visual (the leaf) hangs off it. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Door")
	TObjectPtr<USceneComponent> Hinge;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Door")
	TObjectPtr<UStaticMeshComponent> Panel;

	/** Reader status lamp: red = refused, amber = processing, green = released. Readable without text. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Door")
	TObjectPtr<UPointLightComponent> PanelLight;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Door")
	FString RequiredItem;

	virtual void InitFromLayout(const TSharedPtr<FJsonObject>& Data, const FConfessionLayout& Layout) override;
	virtual void Tick(float DeltaSeconds) override;
	virtual bool CanUse(const AConfessionCharacter* By) const override;
	virtual FText GetPrompt(const AConfessionCharacter* By) const override;
	virtual FVector GetAimPoint() const override;
	virtual void RestoreFromProgress(const ConfessionRules::ProgressState& State) override;

	ConfessionRules::DoorState GetDoorState() const { return Lock.GetState(); }

protected:
	virtual void HandleUse(AConfessionCharacter* By) override;

private:
	void ApplyPose();
	void SetLamp(const FLinearColor& Color, float Lumens);
	bool PlayerHasItem() const;
	FText RejectText(const AConfessionGameMode& GM) const;

	ConfessionRules::DoorLock Lock;
	float ClosedYaw = 0.0f;
	float OpenYaw = -90.0f;
	float LampFlashTimer = 0.0f;
	FText LabelLocked;
	FText LabelOpen;
	FText LabelWait;
	FString MsgNoItem;
	FString MsgReject;
	FString MsgRelease;
	FString FlagOnOpen;
	FString PreviousNumber;
};
