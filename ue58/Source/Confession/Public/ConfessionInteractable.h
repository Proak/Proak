#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ConfessionInteractable.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FConfessionUsedSignature, AActor*, InstigatorActor);

UCLASS(Blueprintable)
class CONFESSION_API AConfessionInteractable : public AActor {
    GENERATED_BODY()
public:
    AConfessionInteractable();
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Interaction")
    TObjectPtr<UStaticMeshComponent> Visual;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Interaction")
    FText InteractionLabel;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Interaction")
    bool bOneShot = false;
    UPROPERTY(BlueprintAssignable,Category="Interaction")
    FConfessionUsedSignature OnUsed;
    UFUNCTION(BlueprintCallable,Category="Interaction")
    void Use(AActor* ByActor);
private:
    bool bUsed = false;
};
