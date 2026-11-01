// The Unfinished Confession - first-person player: Enhanced Input built in code (no .uasset needed),
// walk / sprint / crouch, focus trace + E interaction, footsteps that also emit gameplay noise.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "ConfessionCharacter.generated.h"

class UCameraComponent;
class UInputAction;
class UInputMappingContext;
class AConfessionInteractable;
class UDamageType;
struct FInputActionValue;

UCLASS()
class CONFESSION_API AConfessionCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	AConfessionCharacter();

	virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void FellOutOfWorld(const UDamageType& DmgType) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera")
	TObjectPtr<UCameraComponent> FirstPersonCamera;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interaction")
	float UseDistanceCm = 260.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float WalkSpeed = 300.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float SprintSpeed = 520.0f;

	/** Degrees per unit of raw mouse delta. Independent of legacy input scale settings. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Input")
	float LookSensitivity = 2.5f;

	/** Gamepad right-stick turn rate, degrees per second at full deflection. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Input")
	float StickTurnRate = 120.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Input")
	bool bInvertLookY = false;

	/** Interact with whatever the focus trace currently hits. Also used by the autopilot. */
	UFUNCTION(BlueprintCallable, Category = "Interaction")
	void TryUse();

	/** The interactable the camera is aimed at this frame (may be null). */
	AConfessionInteractable* GetFocused() const { return Focused.Get(); }
	/** Autopilot hook: steer as if the stick were held. */
	void AutopilotMove(const FVector& WorldDirection, float Scale);
	bool IsSprinting() const { return bSprinting; }

protected:
	virtual void BeginPlay() override;

private:
	void CreateInputObjects();
	void OnMove(const FInputActionValue& Value);
	void OnLook(const FInputActionValue& Value);
	void OnLookStick(const FInputActionValue& Value);
	void ApplyLook(float YawDeg, float PitchDeg);
	void OnSprintStart(const FInputActionValue& Value);
	void OnSprintStop(const FInputActionValue& Value);
	void OnCrouchStart(const FInputActionValue& Value);
	void OnCrouchStop(const FInputActionValue& Value);
	void OnInteract(const FInputActionValue& Value);
	void OnNotebook(const FInputActionValue& Value);
	void UpdateFocus();
	void UpdateFootsteps(float DeltaSeconds);
	void ApplySpeed();

	UPROPERTY(Transient) TObjectPtr<UInputMappingContext> MappingContext;
	UPROPERTY(Transient) TObjectPtr<UInputAction> MoveAction;
	UPROPERTY(Transient) TObjectPtr<UInputAction> LookAction;
	UPROPERTY(Transient) TObjectPtr<UInputAction> LookStickAction;
	UPROPERTY(Transient) TObjectPtr<UInputAction> SprintAction;
	UPROPERTY(Transient) TObjectPtr<UInputAction> CrouchAction;
	UPROPERTY(Transient) TObjectPtr<UInputAction> InteractAction;
	UPROPERTY(Transient) TObjectPtr<UInputAction> NotebookAction;

	TWeakObjectPtr<AConfessionInteractable> Focused;
	bool bSprinting = false;
	float StrideAccum = 0.0f;
	int32 LastFootstep = -1;
};
