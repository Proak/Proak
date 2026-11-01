// The Unfinished Confession - base interactable.
#include "ConfessionInteractable.h"

#include "ConfessionCharacter.h"
#include "ConfessionGameMode.h"
#include "ConfessionTypes.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"

AConfessionInteractable::AConfessionInteractable()
{
	PrimaryActorTick.bCanEverTick = false;
	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	SetRootComponent(SceneRoot);
	Visual = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Visual"));
	Visual->SetupAttachment(SceneRoot);
	Visual->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	InteractionLabel = FText::FromString(TEXT("Inspect"));
}

void AConfessionInteractable::InitFromLayout(const TSharedPtr<FJsonObject>& Data, const FConfessionLayout& Layout)
{
	LayoutId = ConfessionData::GetString(Data, TEXT("id"));
	const FText Label = ConfessionData::Localized(Data, TEXT("label"));
	if (!Label.IsEmpty())
	{
		InteractionLabel = Label;
	}
}

bool AConfessionInteractable::CanUse(const AConfessionCharacter* By) const
{
	return !(bOneShot && bUsed) && !IsHidden();
}

FText AConfessionInteractable::GetPrompt(const AConfessionCharacter* By) const
{
	return InteractionLabel;
}

FVector AConfessionInteractable::GetAimPoint() const
{
	return Visual ? Visual->Bounds.Origin : GetActorLocation();
}

void AConfessionInteractable::Use(AActor* ByActor)
{
	AConfessionCharacter* Character = Cast<AConfessionCharacter>(ByActor);
	if (!CanUse(Character))
	{
		return;
	}
	bUsed = true;
	HandleUse(Character);
	OnUsed.Broadcast(ByActor);
}

AConfessionGameMode* AConfessionInteractable::GetConfessionGameMode() const
{
	return GetWorld() ? GetWorld()->GetAuthGameMode<AConfessionGameMode>() : nullptr;
}

void AConfessionInteractable::SetupBox(UStaticMeshComponent* Comp, const FVector& WorldCenterCm, const FVector& SizeCm,
	const FString& MaterialName, const FConfessionLayout& Layout, bool bCollision)
{
	if (!Comp)
	{
		return;
	}
	Comp->SetStaticMesh(ConfessionGreybox::CubeMesh());
	Comp->SetMaterial(0, ConfessionGreybox::MakeMaterial(this, Layout.MaterialOrDefault(MaterialName)));
	Comp->SetWorldScale3D(SizeCm / 100.0); // engine cube is 100 cm with a centred pivot
	Comp->SetWorldLocation(WorldCenterCm);
	Comp->SetCollisionProfileName(bCollision ? UCollisionProfile::BlockAll_ProfileName : UCollisionProfile::NoCollision_ProfileName);
}
