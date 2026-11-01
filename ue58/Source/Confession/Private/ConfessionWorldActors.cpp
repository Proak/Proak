// The Unfinished Confession - checkpoints, phones, displacement anomaly.
#include "ConfessionWorldActors.h"

#include "ConfessionAudio.h"
#include "ConfessionCharacter.h"
#include "ConfessionGameMode.h"
#include "ConfessionTypes.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

// ------------------------------------------------------------------ checkpoint
AConfessionCheckpoint::AConfessionCheckpoint()
{
	PrimaryActorTick.bCanEverTick = false;
	Volume = CreateDefaultSubobject<UBoxComponent>(TEXT("Volume"));
	SetRootComponent(Volume);
	Volume->SetCollisionProfileName(TEXT("Trigger"));
	Volume->SetGenerateOverlapEvents(true);
	Volume->SetHiddenInGame(true);
}

void AConfessionCheckpoint::InitFromLayout(const TSharedPtr<FJsonObject>& Data)
{
	LayoutId = ConfessionData::GetString(Data, TEXT("id"));
	FlagOnReach = ConfessionData::GetString(Data, TEXT("sets_flag"));
	const FVector Size = ConfessionData::ToUESize(ConfessionData::GetVec3(Data, TEXT("size"), FVector(2.0)));
	Volume->SetBoxExtent(Size * 0.5);
	const FVector2D Facing = ConfessionData::GetVec2(Data, TEXT("respawn_facing"), FVector2D(0.0, 1.0));
	Respawn = FTransform(FRotator(0.0f, ConfessionData::YawFromFacing(Facing.X, Facing.Y), 0.0f),
		ConfessionData::ToUE(ConfessionData::GetVec3(Data, TEXT("respawn"))));
#if WITH_EDITOR
	SetActorLabel(LayoutId);
#endif
}

void AConfessionCheckpoint::NotifyActorBeginOverlap(AActor* OtherActor)
{
	Super::NotifyActorBeginOverlap(OtherActor);
	AConfessionCharacter* Player = Cast<AConfessionCharacter>(OtherActor);
	if (!Player || !Player->IsPlayerControlled())
	{
		return;
	}
	if (AConfessionGameMode* GM = GetWorld()->GetAuthGameMode<AConfessionGameMode>())
	{
		GM->ReachCheckpoint(LayoutId, Respawn, FlagOnReach);
	}
}

// ------------------------------------------------------------------ phone
AConfessionPhone::AConfessionPhone()
{
	PrimaryActorTick.bCanEverTick = true;
}

void AConfessionPhone::InitFromLayout(const TSharedPtr<FJsonObject>& Data, const FConfessionLayout& Layout)
{
	Super::InitFromLayout(Data, Layout);
	RingEvent = ConfessionData::GetString(Data, TEXT("ring_event"));
	AnswerMessage = ConfessionData::GetString(Data, TEXT("on_answer_msg"));
	RelayTo = ConfessionData::GetString(Data, TEXT("relay_to"));
	RelayDelay = static_cast<float>(ConfessionData::GetNumber(Data, TEXT("relay_delay_s"), 2.5));
	SetupBox(Visual, ConfessionData::ToUE(ConfessionData::GetVec3(Data, TEXT("center"))),
		ConfessionData::ToUESize(ConfessionData::GetVec3(Data, TEXT("size"), FVector(0.2))),
		ConfessionData::GetString(Data, TEXT("material")), Layout);
}

bool AConfessionPhone::CanUse(const AConfessionCharacter* By) const
{
	return IsRinging(); // a silent phone is set dressing, not a prompt
}

void AConfessionPhone::OnLevelEvent(const FString& EventId)
{
	if (!RingEvent.IsEmpty() && EventId == RingEvent)
	{
		StartRinging();
	}
}

void AConfessionPhone::StartRinging()
{
	// Canon: the phone rings once. One ring cycle plus a short grace period to answer.
	UConfessionAudioSubsystem* Audio = GetWorld()->GetSubsystem<UConfessionAudioSubsystem>();
	const float RingLength = Audio ? FMath::Max(1.5f, Audio->DurationOf(TEXT("phone_ring"))) : 2.5f;
	if (Audio)
	{
		Audio->PlayAt(TEXT("phone_ring"), GetAimPoint(), 0.9f, 2600.0f);
	}
	RingWindow = RingLength + 3.0f;
	UE_LOG(LogConfession, Log, TEXT("[Phone] %s rings"), *LayoutId);
}

void AConfessionPhone::HandleUse(AConfessionCharacter* By)
{
	RingWindow = 0.0f;
	if (UConfessionAudioSubsystem* Audio = GetWorld()->GetSubsystem<UConfessionAudioSubsystem>())
	{
		Audio->PlayAt(TEXT("phone_pickup"), GetAimPoint(), 0.7f, 600.0f);
		if (!RelayTo.IsEmpty())
		{
			Audio->PlayAt(TEXT("dial_tone"), GetAimPoint(), 0.45f, 300.0f);
		}
	}
	if (AConfessionGameMode* GM = GetConfessionGameMode())
	{
		GM->ShowMessageId(AnswerMessage);
		GM->SetFlag(LayoutId + TEXT(".answered"));
	}
	if (!RelayTo.IsEmpty())
	{
		RelayTimer = RelayDelay; // "after hanging up, the ringing starts at the other end of the hall"
	}
}

void AConfessionPhone::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (RingWindow > 0.0f)
	{
		RingWindow = FMath::Max(0.0f, RingWindow - DeltaSeconds);
	}
	if (RelayTimer >= 0.0f)
	{
		RelayTimer -= DeltaSeconds;
		if (RelayTimer < 0.0f)
		{
			AConfessionGameMode* GM = GetConfessionGameMode();
			if (AConfessionPhone* Other = GM ? Cast<AConfessionPhone>(GM->FindInteractable(RelayTo)) : nullptr)
			{
				Other->StartRinging();
			}
		}
	}
}

// ------------------------------------------------------------------ displacement anomaly
AConfessionDisplacementAnomaly::AConfessionDisplacementAnomaly()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickInterval = 0.05f;
}

void AConfessionDisplacementAnomaly::InitFromLayout(const TSharedPtr<FJsonObject>& Data, const FConfessionLayout& Layout)
{
	Super::InitFromLayout(Data, Layout);
	DocumentId = ConfessionData::GetString(Data, TEXT("document"));
	SeenWithinCm = static_cast<float>(ConfessionData::GetNumber(Data, TEXT("seen_within_m"), 4.5) * 100.0);
	const FVector D = ConfessionData::GetVec3(Data, TEXT("displace"));
	OffsetCm = FVector(D.X * 100.0, -D.Y * 100.0, D.Z * 100.0);
	SetupBox(Visual, ConfessionData::ToUE(ConfessionData::GetVec3(Data, TEXT("center"))),
		ConfessionData::ToUESize(ConfessionData::GetVec3(Data, TEXT("size"), FVector(0.1, 1.0, 1.0))),
		ConfessionData::GetString(Data, TEXT("material")), Layout);
	HomeLocation = Visual->GetComponentLocation();
}

bool AConfessionDisplacementAnomaly::IsInPlayerView() const
{
	const APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!PC || !PC->PlayerCameraManager)
	{
		return false;
	}
	const FVector Eye = PC->PlayerCameraManager->GetCameraLocation();
	const FVector Fwd = PC->PlayerCameraManager->GetCameraRotation().Vector();
	const FVector Target = Visual->Bounds.Origin;
	const FVector To = Target - Eye;
	const double Dist = To.Size();
	if (Dist > SeenWithinCm || Dist < 1.0)
	{
		return false;
	}
	const float HalfFovDeg = PC->PlayerCameraManager->GetFOVAngle() * 0.5f;
	// Count as "seen" only well inside the frame, not at the very edge.
	if (FVector::DotProduct(To / Dist, Fwd) < FMath::Cos(FMath::DegreesToRadians(HalfFovDeg * 0.8f)))
	{
		return false;
	}
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(ConfessionAnomalyLOS), false, PC->GetPawn());
	const bool bBlocked = GetWorld()->LineTraceSingleByChannel(Hit, Eye, Target, ECC_Visibility, Params);
	return !bBlocked || Hit.GetActor() == this;
}

void AConfessionDisplacementAnomaly::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (Rule.Update(IsInPlayerView(), DeltaSeconds))
	{
		Visual->SetWorldLocation(HomeLocation + OffsetCm);
		if (AConfessionGameMode* GM = GetConfessionGameMode())
		{
			GM->SetFlag(LayoutId + TEXT(".moved"));
		}
		UE_LOG(LogConfession, Log, TEXT("[Anomaly] %s displaced by %s cm while unobserved"), *LayoutId, *OffsetCm.ToString());
	}
}

void AConfessionDisplacementAnomaly::HandleUse(AConfessionCharacter* By)
{
	if (AConfessionGameMode* GM = GetConfessionGameMode())
	{
		GM->ShowDocument(DocumentId);
	}
}

void AConfessionDisplacementAnomaly::RestoreFromProgress(const ConfessionRules::ProgressState& State)
{
	const bool bMoved = State.HasFlag(ConfessionData::ToStd(LayoutId + TEXT(".moved")));
	Rule.Restore(bMoved);
	Visual->SetWorldLocation(HomeLocation + (bMoved ? OffsetCm : FVector::ZeroVector));
}
