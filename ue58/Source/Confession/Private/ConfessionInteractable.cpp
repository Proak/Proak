#include "ConfessionInteractable.h"
#include "Components/StaticMeshComponent.h"
AConfessionInteractable::AConfessionInteractable(){
    PrimaryActorTick.bCanEverTick = false;
    Visual = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Visual"));
    SetRootComponent(Visual);
    InteractionLabel = FText::FromString(TEXT("Inspect"));
}
void AConfessionInteractable::Use(AActor* ByActor){
    if (bOneShot && bUsed) return;
    bUsed = true;
    OnUsed.Broadcast(ByActor);
}
