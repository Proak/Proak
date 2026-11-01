// The Unfinished Confession - hinged doors with access readers.
#include "ConfessionDoor.h"

#include "ConfessionAudio.h"
#include "ConfessionCharacter.h"
#include "ConfessionGameMode.h"
#include "ConfessionTypes.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace
{
const FLinearColor LampRed(1.0f, 0.08f, 0.04f);
const FLinearColor LampAmber(1.0f, 0.55f, 0.1f);
const FLinearColor LampGreen(0.2f, 1.0f, 0.35f);
}

AConfessionDoor::AConfessionDoor()
{
	PrimaryActorTick.bCanEverTick = true;
	Hinge = CreateDefaultSubobject<USceneComponent>(TEXT("Hinge"));
	Hinge->SetupAttachment(SceneRoot);
	Visual->SetupAttachment(Hinge);

	Panel = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Panel"));
	Panel->SetupAttachment(SceneRoot);

	PanelLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("PanelLight"));
	PanelLight->SetupAttachment(SceneRoot);
	PanelLight->SetCastShadows(false);
	PanelLight->SetVisibility(false);
}

void AConfessionDoor::InitFromLayout(const TSharedPtr<FJsonObject>& Data, const FConfessionLayout& Layout)
{
	Super::InitFromLayout(Data, Layout);
	RequiredItem = ConfessionData::GetString(Data, TEXT("requires_item"));
	const FString Mode = ConfessionData::GetString(Data, TEXT("lock_mode"), TEXT("item"));
	const ConfessionRules::LockMode LM = RequiredItem.IsEmpty() ? ConfessionRules::LockMode::None
		: (Mode == TEXT("reject_once_then_release") ? ConfessionRules::LockMode::RejectOnceThenRelease : ConfessionRules::LockMode::Item);
	Lock = ConfessionRules::DoorLock(LM, ConfessionData::GetNumber(Data, TEXT("release_delay_s"), 1.4), 1.3);

	// Layout yaw is counter-clockwise from +X (east) toward +Y (north); UE yaw is the mirror.
	ClosedYaw = -static_cast<float>(ConfessionData::GetNumber(Data, TEXT("closed_yaw_deg"), 0.0));
	OpenYaw = -static_cast<float>(ConfessionData::GetNumber(Data, TEXT("open_yaw_deg"), 90.0));

	LabelLocked = ConfessionData::Localized(Data, TEXT("label_locked"));
	LabelOpen = ConfessionData::Localized(Data, TEXT("label_open"));
	LabelWait = ConfessionData::Localized(Data, TEXT("label_wait"));
	MsgNoItem = ConfessionData::GetString(Data, TEXT("msg_no_item"));
	MsgReject = ConfessionData::GetString(Data, TEXT("msg_reject"));
	MsgRelease = ConfessionData::GetString(Data, TEXT("msg_release"));
	FlagOnOpen = ConfessionData::GetString(Data, TEXT("sets_flag_on_open"));
	PreviousNumber = ConfessionData::GetString(Data, TEXT("previous_number"));

	// Actor root sits on the hinge axis (spawn transform). The leaf extends along local +X.
	const FVector Leaf = ConfessionData::ToUESize(ConfessionData::GetVec3(Data, TEXT("leaf_size"), FVector(1.2, 0.06, 2.2)));
	const FString Mat = ConfessionData::GetString(Data, TEXT("material"));
	Visual->SetStaticMesh(ConfessionGreybox::CubeMesh());
	Visual->SetMaterial(0, ConfessionGreybox::MakeMaterial(this, Layout.MaterialOrDefault(Mat)));
	Visual->SetRelativeLocation(FVector(Leaf.X * 0.5, 0.0, Leaf.Z * 0.5));
	Visual->SetRelativeScale3D(Leaf / 100.0);

	if (Data->HasField(TEXT("panel")))
	{
		Panel->SetStaticMesh(ConfessionGreybox::CubeMesh());
		Panel->SetMaterial(0, ConfessionGreybox::MakeMaterial(this, Layout.MaterialOrDefault(TEXT("iron_dark"))));
		Panel->SetWorldLocation(ConfessionData::ToUE(ConfessionData::GetVec3(Data, TEXT("panel"))));
		Panel->SetWorldScale3D(FVector(0.12, 0.04, 0.18));
		// Both readers face south (the approach side); +Y in UE is south. Keep the lamp just in front of the panel.
		PanelLight->SetWorldLocation(Panel->GetComponentLocation() + FVector(0.0, 8.0, 0.0));
		PanelLight->SetIntensityUnits(ELightUnits::Lumens);
		PanelLight->SetAttenuationRadius(90.0f);
		PanelLight->SetVisibility(true);
		SetLamp(LM == ConfessionRules::LockMode::None ? LampGreen : LampRed, 6.0f);
	}
	else
	{
		Panel->SetVisibility(false);
		Panel->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	}
	ApplyPose();
}

void AConfessionDoor::SetLamp(const FLinearColor& Color, float Lumens)
{
	if (PanelLight && PanelLight->IsVisible())
	{
		PanelLight->SetLightColor(Color);
		PanelLight->SetIntensity(Lumens);
	}
}

void AConfessionDoor::ApplyPose()
{
	const float Alpha = static_cast<float>(Lock.OpenAlpha());
	Hinge->SetRelativeRotation(FRotator(0.0f, FMath::Lerp(ClosedYaw, OpenYaw, Alpha), 0.0f));
}

FText AConfessionDoor::RejectText(const AConfessionGameMode& GM) const
{
	FString Text = GM.GetLayout().Message(MsgReject).ToString();
	Text.ReplaceInline(TEXT("{number}"), *PreviousNumber);
	return FText::FromString(Text);
}

bool AConfessionDoor::PlayerHasItem() const
{
	const AConfessionGameMode* GM = GetConfessionGameMode();
	return RequiredItem.IsEmpty() || (GM && GM->HasItem(RequiredItem));
}

bool AConfessionDoor::CanUse(const AConfessionCharacter* By) const
{
	const ConfessionRules::DoorState S = Lock.GetState();
	// Releasing stays "usable" so the prompt does not vanish mid-beat; Use() is a no-op (Busy) then.
	return S == ConfessionRules::DoorState::Locked || S == ConfessionRules::DoorState::Unlocked || S == ConfessionRules::DoorState::Releasing;
}

FText AConfessionDoor::GetPrompt(const AConfessionCharacter* By) const
{
	switch (Lock.GetState())
	{
	case ConfessionRules::DoorState::Locked: return LabelLocked;
	case ConfessionRules::DoorState::Releasing: return LabelWait.IsEmpty() ? LabelLocked : LabelWait;
	default: return LabelOpen;
	}
}

FVector AConfessionDoor::GetAimPoint() const
{
	// Aim at the middle of the leaf at a comfortable height; the reader panel also routes here.
	return Visual ? Visual->Bounds.Origin : GetActorLocation();
}

void AConfessionDoor::HandleUse(AConfessionCharacter* By)
{
	AConfessionGameMode* GM = GetConfessionGameMode();
	UConfessionAudioSubsystem* Audio = GetWorld()->GetSubsystem<UConfessionAudioSubsystem>();
	const FVector At = Panel && Panel->IsVisible() ? Panel->GetComponentLocation() : GetAimPoint();
	const ConfessionRules::UseResult R = Lock.Use(PlayerHasItem());
	UE_LOG(LogConfession, Log, TEXT("[Door] %s use -> %d (state %s)"), *LayoutId, static_cast<int32>(R), ANSI_TO_TCHAR(ConfessionRules::ToString(Lock.GetState())));
	switch (R)
	{
	case ConfessionRules::UseResult::NeedItem:
		if (Audio) { Audio->PlayAt(TEXT("door_reject"), At, 0.8f, 1200.0f); }
		SetLamp(LampRed, 40.0f);
		LampFlashTimer = 0.6f;
		if (GM) { GM->ShowMessageId(MsgNoItem); }
		break;
	case ConfessionRules::UseResult::Rejected:
		if (Audio) { Audio->PlayAt(TEXT("door_reject"), At, 0.8f, 1200.0f); }
		SetLamp(LampAmber, 25.0f);
		if (GM) { GM->ShowMessage(RejectText(*GM), 6.0f); }
		break;
	case ConfessionRules::UseResult::Opening:
		if (Audio) { Audio->PlayAt(TEXT("door_open"), GetAimPoint(), 0.9f, 1800.0f); }
		SetLamp(LampGreen, 12.0f);
		if (GM)
		{
			GM->SetFlag(FlagOnOpen);
			GM->SetFlag(LayoutId + TEXT(".open"));
		}
		break;
	case ConfessionRules::UseResult::Busy:
	case ConfessionRules::UseResult::AlreadyOpen:
		break;
	}
}

void AConfessionDoor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (Lock.Tick(DeltaSeconds))
	{
		// Latch released by itself after the reader re-showed the previous number.
		if (UConfessionAudioSubsystem* Audio = GetWorld()->GetSubsystem<UConfessionAudioSubsystem>())
		{
			Audio->PlayAt(TEXT("door_release"), GetAimPoint(), 1.0f, 1800.0f);
		}
		SetLamp(LampGreen, 12.0f);
		if (AConfessionGameMode* GM = GetConfessionGameMode())
		{
			// Keep the previous-number line on screen and add the release under it (canon beat stays readable).
			GM->ShowMessage(FText::FromString(RejectText(*GM).ToString() + TEXT("\n") + GM->GetLayout().Message(MsgRelease).ToString()), 4.0f);
			GM->SetFlag(LayoutId + TEXT(".released"));
		}
	}
	if (LampFlashTimer > 0.0f)
	{
		LampFlashTimer -= DeltaSeconds;
		if (LampFlashTimer <= 0.0f && Lock.GetState() == ConfessionRules::DoorState::Locked)
		{
			SetLamp(LampRed, 6.0f);
		}
	}
	ApplyPose();
}

void AConfessionDoor::RestoreFromProgress(const ConfessionRules::ProgressState& State)
{
	const bool bOpen = State.HasFlag(ConfessionData::ToStd(LayoutId + TEXT(".open")));
	const bool bReleased = State.HasFlag(ConfessionData::ToStd(LayoutId + TEXT(".released")));
	Lock.Restore(bReleased, bOpen);
	SetLamp(Lock.IsReleased() ? LampGreen : LampRed, Lock.IsReleased() ? 12.0f : 6.0f);
	ApplyPose();
}
