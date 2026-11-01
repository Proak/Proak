// The Unfinished Confession - first-person player.
#include "ConfessionCharacter.h"

#include "ConfessionAudio.h"
#include "ConfessionGameMode.h"
#include "ConfessionHUD.h"
#include "ConfessionInteractable.h"
#include "ConfessionTypes.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "InputAction.h"
#include "InputActionValue.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"

static TAutoConsoleVariable<float> CVarConfessionFOV(
	TEXT("confession.FOV"), 90.0f, TEXT("Horizontal field of view in degrees (accessibility; 70-110)."), ECVF_Default);

namespace
{
constexpr float CapsuleRadius = 35.0f;
constexpr float CapsuleHalfHeight = 92.0f;  // 184 cm standing capsule
constexpr float EyeHeight = 165.0f;         // matches scene spec human_scale.eye_height_cm
}

AConfessionCharacter::AConfessionCharacter()
{
	PrimaryActorTick.bCanEverTick = true;
	GetCapsuleComponent()->InitCapsuleSize(CapsuleRadius, CapsuleHalfHeight);

	FirstPersonCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FirstPersonCamera"));
	FirstPersonCamera->SetupAttachment(GetCapsuleComponent());
	FirstPersonCamera->SetRelativeLocation(FVector(0.0, 0.0, EyeHeight - CapsuleHalfHeight));
	FirstPersonCamera->bUsePawnControlRotation = true;
	FirstPersonCamera->SetFieldOfView(90.0f);

	bUseControllerRotationYaw = true;
	bUseControllerRotationPitch = false;
	bUseControllerRotationRoll = false;

	UCharacterMovementComponent* Move = GetCharacterMovement();
	Move->bOrientRotationToMovement = false;
	Move->MaxWalkSpeed = WalkSpeed;
	Move->MaxWalkSpeedCrouched = 160.0f;
	Move->BrakingDecelerationWalking = 1600.0f;
	Move->GroundFriction = 8.0f;
	Move->MaxStepHeight = 40.0f;
	Move->GetNavAgentPropertiesRef().bCanCrouch = true;
	Move->SetCrouchedHalfHeight(58.0f);
	Move->JumpZVelocity = 0.0f; // no jump in this game: barriers stay barriers
}

void AConfessionCharacter::BeginPlay()
{
	Super::BeginPlay();
	if (const AConfessionGameMode* GM = GetWorld()->GetAuthGameMode<AConfessionGameMode>())
	{
		UseDistanceCm = GM->GetLayout().UseDistanceCm;
	}
	ApplySpeed();
}

void AConfessionCharacter::CreateInputObjects()
{
	if (MappingContext)
	{
		return;
	}
	MappingContext = NewObject<UInputMappingContext>(this, TEXT("IMC_Confession"));
	auto MakeAction = [this](const TCHAR* Name, EInputActionValueType Type)
	{
		UInputAction* A = NewObject<UInputAction>(this, Name);
		A->ValueType = Type;
		return A;
	};
	MoveAction = MakeAction(TEXT("IA_Move"), EInputActionValueType::Axis2D);
	LookAction = MakeAction(TEXT("IA_Look"), EInputActionValueType::Axis2D);
	LookStickAction = MakeAction(TEXT("IA_LookStick"), EInputActionValueType::Axis2D);
	SprintAction = MakeAction(TEXT("IA_Sprint"), EInputActionValueType::Boolean);
	CrouchAction = MakeAction(TEXT("IA_Crouch"), EInputActionValueType::Boolean);
	InteractAction = MakeAction(TEXT("IA_Interact"), EInputActionValueType::Boolean);
	NotebookAction = MakeAction(TEXT("IA_Notebook"), EInputActionValueType::Boolean);

	UInputMappingContext* Ctx = MappingContext;
	auto Map = [Ctx](UInputAction* A, const FKey& Key, bool bSwizzleYX, bool bNegate)
	{
		FEnhancedActionKeyMapping& M = Ctx->MapKey(A, Key);
		if (bSwizzleYX)
		{
			UInputModifierSwizzleAxis* Swizzle = NewObject<UInputModifierSwizzleAxis>(Ctx);
			Swizzle->Order = EInputAxisSwizzle::YXZ; // 1D key -> forward (Y) axis
			M.Modifiers.Add(Swizzle);
		}
		if (bNegate)
		{
			M.Modifiers.Add(NewObject<UInputModifierNegate>(Ctx));
		}
	};
	// Axis2D convention: X = right, Y = forward. GDD controls: WASD / Shift / Ctrl / E / Tab.
	Map(MoveAction, EKeys::W, true, false);
	Map(MoveAction, EKeys::S, true, true);
	Map(MoveAction, EKeys::D, false, false);
	Map(MoveAction, EKeys::A, false, true);
	Map(MoveAction, EKeys::Gamepad_Left2D, false, false);
	Map(LookAction, EKeys::Mouse2D, false, false);
	Map(LookStickAction, EKeys::Gamepad_Right2D, false, false);
	Map(SprintAction, EKeys::LeftShift, false, false);
	Map(SprintAction, EKeys::Gamepad_LeftThumbstick, false, false);
	Map(CrouchAction, EKeys::LeftControl, false, false);
	Map(CrouchAction, EKeys::C, false, false);
	Map(CrouchAction, EKeys::Gamepad_FaceButton_Right, false, false);
	Map(InteractAction, EKeys::E, false, false);
	Map(InteractAction, EKeys::Gamepad_FaceButton_Bottom, false, false);
	Map(NotebookAction, EKeys::Tab, false, false);
	Map(NotebookAction, EKeys::Gamepad_Special_Right, false, false);
}

void AConfessionCharacter::SetupPlayerInputComponent(UInputComponent* Input)
{
	Super::SetupPlayerInputComponent(Input);
	CreateInputObjects();

	if (const APlayerController* PC = Cast<APlayerController>(GetController()))
	{
		if (ULocalPlayer* LP = PC->GetLocalPlayer())
		{
			if (UEnhancedInputLocalPlayerSubsystem* Sub = LP->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>())
			{
				Sub->RemoveMappingContext(MappingContext);
				Sub->AddMappingContext(MappingContext, 0);
			}
		}
	}

	UEnhancedInputComponent* EIC = Cast<UEnhancedInputComponent>(Input);
	if (!EIC)
	{
		UE_LOG(LogConfession, Error, TEXT("Input component is not UEnhancedInputComponent: check Config/DefaultInput.ini"));
		return;
	}
	EIC->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AConfessionCharacter::OnMove);
	EIC->BindAction(LookAction, ETriggerEvent::Triggered, this, &AConfessionCharacter::OnLook);
	EIC->BindAction(LookStickAction, ETriggerEvent::Triggered, this, &AConfessionCharacter::OnLookStick);
	EIC->BindAction(SprintAction, ETriggerEvent::Started, this, &AConfessionCharacter::OnSprintStart);
	EIC->BindAction(SprintAction, ETriggerEvent::Completed, this, &AConfessionCharacter::OnSprintStop);
	EIC->BindAction(CrouchAction, ETriggerEvent::Started, this, &AConfessionCharacter::OnCrouchStart);
	EIC->BindAction(CrouchAction, ETriggerEvent::Completed, this, &AConfessionCharacter::OnCrouchStop);
	EIC->BindAction(InteractAction, ETriggerEvent::Started, this, &AConfessionCharacter::OnInteract);
	EIC->BindAction(NotebookAction, ETriggerEvent::Started, this, &AConfessionCharacter::OnNotebook);
}

void AConfessionCharacter::OnMove(const FInputActionValue& Value)
{
	const FVector2D V = Value.Get<FVector2D>();
	if (!Controller)
	{
		return;
	}
	const FRotator Yaw(0.0f, Controller->GetControlRotation().Yaw, 0.0f);
	const FRotationMatrix M(Yaw);
	AddMovementInput(M.GetUnitAxis(EAxis::X), static_cast<float>(V.Y));
	AddMovementInput(M.GetUnitAxis(EAxis::Y), static_cast<float>(V.X));
}

void AConfessionCharacter::AutopilotMove(const FVector& WorldDirection, float Scale)
{
	AddMovementInput(WorldDirection.GetSafeNormal2D(), Scale);
}

void AConfessionCharacter::ApplyLook(float YawDeg, float PitchDeg)
{
	if (!Controller)
	{
		return;
	}
	// Applied directly to the control rotation so the result does not depend on the project's
	// legacy input-scale settings (which have changed sign/scale between engine versions).
	FRotator R = Controller->GetControlRotation();
	R.Yaw = FRotator::NormalizeAxis(R.Yaw + YawDeg);
	R.Pitch = FMath::Clamp(FRotator::NormalizeAxis(R.Pitch + PitchDeg), -85.0f, 85.0f);
	R.Roll = 0.0f;
	Controller->SetControlRotation(R);
}

void AConfessionCharacter::OnLook(const FInputActionValue& Value)
{
	const FVector2D V = Value.Get<FVector2D>();
	const float Y = static_cast<float>(V.Y) * (bInvertLookY ? -1.0f : 1.0f);
	ApplyLook(static_cast<float>(V.X) * LookSensitivity, Y * LookSensitivity);
}

void AConfessionCharacter::OnLookStick(const FInputActionValue& Value)
{
	const FVector2D V = Value.Get<FVector2D>();
	const float Dt = GetWorld() ? GetWorld()->GetDeltaSeconds() : 0.016f;
	const float Y = static_cast<float>(V.Y) * (bInvertLookY ? -1.0f : 1.0f);
	ApplyLook(static_cast<float>(V.X) * StickTurnRate * Dt, Y * StickTurnRate * 0.7f * Dt);
}

void AConfessionCharacter::ApplySpeed()
{
	GetCharacterMovement()->MaxWalkSpeed = bSprinting ? SprintSpeed : WalkSpeed;
}

void AConfessionCharacter::OnSprintStart(const FInputActionValue&) { bSprinting = true; ApplySpeed(); }
void AConfessionCharacter::OnSprintStop(const FInputActionValue&) { bSprinting = false; ApplySpeed(); }
void AConfessionCharacter::OnCrouchStart(const FInputActionValue&) { Crouch(); }
void AConfessionCharacter::OnCrouchStop(const FInputActionValue&) { UnCrouch(); }

void AConfessionCharacter::OnInteract(const FInputActionValue&)
{
	const APlayerController* PC = Cast<APlayerController>(GetController());
	if (AConfessionHUD* HUD = PC ? Cast<AConfessionHUD>(PC->GetHUD()) : nullptr)
	{
		if (HUD->IsDocumentOpen())
		{
			HUD->CloseDocument();
			return;
		}
		if (HUD->IsNotebookOpen())
		{
			HUD->SetNotebook(false, FText::GetEmpty());
			return;
		}
	}
	TryUse();
}

void AConfessionCharacter::OnNotebook(const FInputActionValue&)
{
	const APlayerController* PC = Cast<APlayerController>(GetController());
	AConfessionHUD* HUD = PC ? Cast<AConfessionHUD>(PC->GetHUD()) : nullptr;
	const AConfessionGameMode* GM = GetWorld()->GetAuthGameMode<AConfessionGameMode>();
	if (HUD && GM)
	{
		HUD->SetNotebook(!HUD->IsNotebookOpen(), GM->BuildNotebookText());
	}
}

void AConfessionCharacter::UpdateFocus()
{
	AConfessionInteractable* Found = nullptr;
	if (FirstPersonCamera && GetWorld())
	{
		const FVector Start = FirstPersonCamera->GetComponentLocation();
		const FVector End = Start + FirstPersonCamera->GetForwardVector() * UseDistanceCm;
		FHitResult Hit;
		FCollisionQueryParams Params(SCENE_QUERY_STAT(ConfessionFocus), false, this);
		// A small sphere is forgiving for thin props (a sheet of paper is 8 mm thick).
		if (GetWorld()->SweepSingleByChannel(Hit, Start, End, FQuat::Identity, ECC_Visibility, FCollisionShape::MakeSphere(5.0f), Params))
		{
			AConfessionInteractable* Candidate = Cast<AConfessionInteractable>(Hit.GetActor());
			if (Candidate && Candidate->CanUse(this))
			{
				Found = Candidate;
			}
		}
	}
	Focused = Found;
	const APlayerController* PC = Cast<APlayerController>(GetController());
	if (AConfessionHUD* HUD = PC ? Cast<AConfessionHUD>(PC->GetHUD()) : nullptr)
	{
		HUD->SetPrompt(Found ? Found->GetPrompt(this) : FText::GetEmpty(), Found != nullptr);
	}
}

void AConfessionCharacter::TryUse()
{
	UpdateFocus();
	if (AConfessionInteractable* Target = Focused.Get())
	{
		Target->Use(this);
		UpdateFocus();
	}
}

void AConfessionCharacter::UpdateFootsteps(float DeltaSeconds)
{
	const UCharacterMovementComponent* Move = GetCharacterMovement();
	const float Speed = static_cast<float>(GetVelocity().Size2D());
	if (!Move->IsMovingOnGround() || Speed < 20.0f)
	{
		StrideAccum = 0.0f;
		return;
	}
	const bool bCrouched = Move->IsCrouching();
	const float Stride = bCrouched ? 55.0f : (bSprinting ? 85.0f : 70.0f);
	StrideAccum += Speed * DeltaSeconds;
	if (StrideAccum < Stride)
	{
		return;
	}
	StrideAccum -= Stride;
	int32 Index = FMath::RandRange(1, 6);
	if (Index == LastFootstep)
	{
		Index = Index % 6 + 1;
	}
	LastFootstep = Index;
	const float Loudness = bCrouched ? 0.25f : (bSprinting ? 0.95f : 0.55f);
	const FVector Feet = GetActorLocation() - FVector(0.0, 0.0, GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
	if (UConfessionAudioSubsystem* Audio = GetWorld()->GetSubsystem<UConfessionAudioSubsystem>())
	{
		Audio->PlayAt(FString::Printf(TEXT("footstep_concrete_%02d"), Index), Feet, Loudness, 1400.0f,
			FMath::FRandRange(0.96f, 1.04f));
	}
	// Gameplay noise for the Inspector's hearing (VS05+): sprinting is audible far, crouching barely.
	MakeNoise(Loudness, this, Feet, bCrouched ? 250.0f : (bSprinting ? 1500.0f : 700.0f));
}

void AConfessionCharacter::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	FirstPersonCamera->SetFieldOfView(FMath::Clamp(CVarConfessionFOV.GetValueOnGameThread(), 70.0f, 110.0f));
	UpdateFocus();
	UpdateFootsteps(DeltaSeconds);
	if (GetActorLocation().Z < -2000.0)
	{
		if (AConfessionGameMode* GM = GetWorld()->GetAuthGameMode<AConfessionGameMode>())
		{
			GM->RespawnAtCheckpoint();
		}
	}
}

void AConfessionCharacter::FellOutOfWorld(const UDamageType& DmgType)
{
	// Never destroy the player for leaving the greybox: return them to the last checkpoint.
	if (AConfessionGameMode* GM = GetWorld()->GetAuthGameMode<AConfessionGameMode>())
	{
		GM->RespawnAtCheckpoint();
		return;
	}
	Super::FellOutOfWorld(DmgType);
}
