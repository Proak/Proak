#include "ConfessionCharacter.h"
#include "ConfessionInteractable.h"
#include "Camera/CameraComponent.h"
#include "Components/InputComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
AConfessionCharacter::AConfessionCharacter(){
 PrimaryActorTick.bCanEverTick = false;
 FirstPersonCamera=CreateDefaultSubobject<UCameraComponent>(TEXT("FirstPersonCamera"));
 FirstPersonCamera->SetupAttachment(GetCapsuleComponent());
 FirstPersonCamera->SetRelativeLocation(FVector(0,0,64));
 FirstPersonCamera->bUsePawnControlRotation=true;
 bUseControllerRotationYaw=true;
 GetCharacterMovement()->bOrientRotationToMovement=false;
 GetCharacterMovement()->MaxWalkSpeed=380.f;
}
void AConfessionCharacter::SetupPlayerInputComponent(UInputComponent* Input){
 Super::SetupPlayerInputComponent(Input);
 Input->BindAxis(TEXT("MoveForward"),this,&AConfessionCharacter::MoveForward);
 Input->BindAxis(TEXT("MoveRight"),this,&AConfessionCharacter::MoveRight);
 Input->BindAxis(TEXT("Turn"),this,&ACharacter::AddControllerYawInput);
 Input->BindAxis(TEXT("LookUp"),this,&ACharacter::AddControllerPitchInput);
 Input->BindAction(TEXT("Interact"),IE_Pressed,this,&AConfessionCharacter::TryUse);
}
void AConfessionCharacter::MoveForward(float V){if(Controller && V!=0.f) AddMovementInput(GetActorForwardVector(),V);}
void AConfessionCharacter::MoveRight(float V){if(Controller && V!=0.f) AddMovementInput(GetActorRightVector(),V);}
void AConfessionCharacter::TryUse(){
 if(!GetWorld()) return;
 const FVector Start=FirstPersonCamera->GetComponentLocation();
 const FVector End=Start+FirstPersonCamera->GetForwardVector()*UseDistanceCm;
 FHitResult Hit;
 FCollisionQueryParams Params;
 Params.AddIgnoredActor(this);
 if(GetWorld()->LineTraceSingleByChannel(Hit,Start,End,ECC_Visibility,Params)){
   if(AConfessionInteractable* Target=Cast<AConfessionInteractable>(Hit.GetActor())) Target->Use(this);
 }
}
