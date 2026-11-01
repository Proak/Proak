#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "ConfessionCharacter.generated.h"
class UCameraComponent;
UCLASS()
class CONFESSION_API AConfessionCharacter : public ACharacter {
 GENERATED_BODY()
public:
 AConfessionCharacter();
 virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Camera") TObjectPtr<UCameraComponent> FirstPersonCamera;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Interaction") float UseDistanceCm=260.0f;
protected:
 void MoveForward(float Axis);
 void MoveRight(float Axis);
 void TryUse();
};
