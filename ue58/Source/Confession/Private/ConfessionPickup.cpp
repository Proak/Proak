// The Unfinished Confession - items and readable documents.
#include "ConfessionPickup.h"

#include "ConfessionAudio.h"
#include "ConfessionCharacter.h"
#include "ConfessionGameMode.h"
#include "ConfessionTypes.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"

AConfessionPickup::AConfessionPickup()
{
	PilotLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("PilotLight"));
	PilotLight->SetupAttachment(SceneRoot);
	PilotLight->SetVisibility(false);
	PilotLight->SetCastShadows(false);
}

void AConfessionPickup::InitFromLayout(const TSharedPtr<FJsonObject>& Data, const FConfessionLayout& Layout)
{
	Super::InitFromLayout(Data, Layout);
	ItemId = ConfessionData::GetString(Data, TEXT("item"));
	FlagOnUse = ConfessionData::GetString(Data, TEXT("sets_flag"));
	DocumentId = ConfessionData::GetString(Data, TEXT("document"));
	SoundId = ConfessionData::GetString(Data, TEXT("sound"));
	EventOnUse = ConfessionData::GetString(Data, TEXT("on_pickup_event"));
	bConsumes = ConfessionData::GetString(Data, TEXT("type")) == TEXT("pickup");

	const FVector Center = ConfessionData::ToUE(ConfessionData::GetVec3(Data, TEXT("center")));
	const FVector Size = ConfessionData::ToUESize(ConfessionData::GetVec3(Data, TEXT("size"), FVector(0.2)));
	SetupBox(Visual, Center, Size, ConfessionData::GetString(Data, TEXT("material")), Layout);

	if (Data->HasField(TEXT("pilot_light")))
	{
		PilotLight->SetWorldLocation(ConfessionData::ToUE(ConfessionData::GetVec3(Data, TEXT("pilot_light"))));
		PilotLight->SetIntensityUnits(ELightUnits::Lumens);
		PilotLight->SetIntensity(35.0f);
		PilotLight->SetAttenuationRadius(160.0f);
		PilotLight->SetLightColor(FLinearColor(1.0f, 0.55f, 0.2f));
		PilotLight->SetVisibility(true);
		bHasPilot = true;
	}
}

bool AConfessionPickup::CanUse(const AConfessionCharacter* By) const
{
	return Super::CanUse(By);
}

void AConfessionPickup::SetTaken(bool bTaken)
{
	SetActorHiddenInGame(bTaken);
	SetActorEnableCollision(!bTaken);
	if (PilotLight && PilotLight->IsVisible() && bTaken)
	{
		PilotLight->SetVisibility(false); // the slot is empty now: the pilot lamp goes out
	}
}

void AConfessionPickup::HandleUse(AConfessionCharacter* By)
{
	AConfessionGameMode* GM = GetConfessionGameMode();
	if (!GM)
	{
		return;
	}
	if (UConfessionAudioSubsystem* Audio = GetWorld()->GetSubsystem<UConfessionAudioSubsystem>())
	{
		Audio->PlayAt(SoundId, GetAimPoint(), 0.8f, 900.0f);
	}
	if (bConsumes)
	{
		GM->GiveItem(ItemId);
		SetTaken(true);
	}
	GM->SetFlag(FlagOnUse);
	if (!DocumentId.IsEmpty())
	{
		GM->ShowDocument(DocumentId);
	}
	if (!EventOnUse.IsEmpty())
	{
		GM->FireEvent(EventOnUse);
	}
	UE_LOG(LogConfession, Log, TEXT("[Pickup] %s used (item=%s flag=%s)"), *LayoutId, *ItemId, *FlagOnUse);
}

void AConfessionPickup::RestoreFromProgress(const ConfessionRules::ProgressState& State)
{
	if (bConsumes)
	{
		const bool bTaken = State.HasItem(ConfessionData::ToStd(ItemId));
		SetTaken(bTaken);
		if (!bTaken && bHasPilot && PilotLight)
		{
			PilotLight->SetVisibility(true);
		}
	}
}
