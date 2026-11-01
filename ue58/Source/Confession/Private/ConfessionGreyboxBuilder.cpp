// The Unfinished Confession - runtime greybox builder.
#include "ConfessionGreyboxBuilder.h"

#include "ConfessionAudio.h"
#include "ConfessionDoor.h"
#include "ConfessionGameMode.h"
#include "ConfessionPickup.h"
#include "ConfessionTypes.h"
#include "ConfessionWorldActors.h"
#include "Components/AudioComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/RectLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/SpotLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TimerManager.h"

AConfessionGreyboxBuilder::AConfessionGreyboxBuilder()
{
	PrimaryActorTick.bCanEverTick = false;
	USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Root->SetMobility(EComponentMobility::Static); // static geometry may only attach to a static parent
	SetRootComponent(Root);
}

void AConfessionGreyboxBuilder::BeginPlay()
{
	Super::BeginPlay();
	const AConfessionGameMode* GM = GetWorld()->GetAuthGameMode<AConfessionGameMode>();
	if (!GM || !GM->GetLayout().bValid)
	{
		UE_LOG(LogConfession, Error, TEXT("GreyboxBuilder: no valid layout (is the GameMode AConfessionGameMode?)"));
		return;
	}
	Build(GM->GetLayout());
}

void AConfessionGreyboxBuilder::EndPlay(const EEndPlayReason::Type Reason)
{
	if (UWorld* World = GetWorld())
	{
		for (FTimerHandle& H : IntervalTimers)
		{
			World->GetTimerManager().ClearTimer(H);
		}
	}
	Super::EndPlay(Reason);
}

void AConfessionGreyboxBuilder::Build(const FConfessionLayout& Layout)
{
	const double Start = FPlatformTime::Seconds();
	BuildGeometry(Layout);
	BuildLights(Layout);
	BuildEnvironment(Layout);
	BuildAudio(Layout);
	SpawnInteractables(Layout);
	UE_LOG(LogConfession, Display, TEXT("Greybox %s built: %d boxes, %d lights, %d interactables in %.1f ms"), *Layout.Id, NumBoxes,
		NumLights, NumInteractables, (FPlatformTime::Seconds() - Start) * 1000.0);
}

void AConfessionGreyboxBuilder::BuildGeometry(const FConfessionLayout& Layout)
{
	UStaticMesh* Cube = ConfessionGreybox::CubeMesh();
	if (!Cube)
	{
		return;
	}
	TMap<FString, UMaterialInstanceDynamic*> MatCache;
	for (const FConfessionBox& B : Layout.Geometry)
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this, FName(*B.Id));
		C->SetMobility(EComponentMobility::Static);
		C->SetupAttachment(GetRootComponent());
		C->SetStaticMesh(Cube);
		UMaterialInstanceDynamic*& Mat = MatCache.FindOrAdd(B.Material);
		if (!Mat)
		{
			Mat = ConfessionGreybox::MakeMaterial(this, Layout.MaterialOrDefault(B.Material));
		}
		C->SetMaterial(0, Mat);
		C->SetWorldLocation(B.CenterCm);
		C->SetWorldScale3D(B.SizeCm / 100.0);
		const bool bInvisibleBlocker = B.Group == TEXT("collision");
		C->SetCollisionProfileName(B.bCollision ? UCollisionProfile::BlockAll_ProfileName : UCollisionProfile::NoCollision_ProfileName);
		C->SetVisibility(!bInvisibleBlocker);
		C->SetCastShadow(!bInvisibleBlocker);
		C->RegisterComponent();
		Generated.Add(C);
		++NumBoxes;
	}
}

void AConfessionGreyboxBuilder::BuildLights(const FConfessionLayout& Layout)
{
	for (const TSharedPtr<FJsonObject>& L : Layout.Lights)
	{
		const FString Type = ConfessionData::GetString(L, TEXT("type"));
		const FVector Pos = ConfessionData::ToUE(ConfessionData::GetVec3(L, TEXT("pos")));
		const FVector Aim = ConfessionData::ToUE(ConfessionData::GetVec3(L, TEXT("aim"), ConfessionData::GetVec3(L, TEXT("pos")) - FVector(0, 0, 1)));
		const FLinearColor Color = ConfessionData::GetColor(L, TEXT("color"));
		const float Lumens = static_cast<float>(ConfessionData::GetNumber(L, TEXT("lumens"), 800.0));
		const float Radius = static_cast<float>(ConfessionData::GetNumber(L, TEXT("radius_m"), 8.0) * 100.0);
		const bool bShadows = ConfessionData::GetBool(L, TEXT("shadows"), true);
		const FName Name(*ConfessionData::GetString(L, TEXT("id")));

		ULocalLightComponent* Light = nullptr;
		if (Type == TEXT("spot"))
		{
			USpotLightComponent* S = NewObject<USpotLightComponent>(this, Name);
			const float Cone = static_cast<float>(ConfessionData::GetNumber(L, TEXT("cone_deg"), 50.0));
			S->SetOuterConeAngle(Cone * 0.5f);
			S->SetInnerConeAngle(Cone * 0.3f);
			Light = S;
		}
		else if (Type == TEXT("rect"))
		{
			URectLightComponent* R = NewObject<URectLightComponent>(this, Name);
			const FVector2D Size = ConfessionData::GetVec2(L, TEXT("size_m"), FVector2D(1.0, 0.3));
			R->SetSourceWidth(static_cast<float>(Size.X * 100.0));
			R->SetSourceHeight(static_cast<float>(Size.Y * 100.0));
			Light = R;
		}
		else
		{
			Light = NewObject<UPointLightComponent>(this, Name);
		}
		Light->SetMobility(EComponentMobility::Movable);
		Light->SetupAttachment(GetRootComponent());
		Light->SetWorldLocation(Pos);
		Light->SetWorldRotation((Aim - Pos).GetSafeNormal().Rotation()); // lights emit along +X
		Light->SetIntensityUnits(ELightUnits::Lumens);
		Light->SetIntensity(Lumens);
		Light->SetLightColor(Color);
		Light->SetAttenuationRadius(Radius);
		Light->SetCastShadows(bShadows);
		Light->RegisterComponent();
		Generated.Add(Light);
		++NumLights;
	}
}

void AConfessionGreyboxBuilder::BuildEnvironment(const FConfessionLayout& Layout)
{
	const TSharedPtr<FJsonObject>& Env = Layout.Environment;

	// Faint cold moonlight from the east-north-east, low: shapes the arcade columns, barely enters.
	UDirectionalLightComponent* Moon = NewObject<UDirectionalLightComponent>(this, TEXT("Env_Moon"));
	Moon->SetMobility(EComponentMobility::Movable);
	Moon->SetupAttachment(GetRootComponent());
	Moon->SetWorldRotation(FRotator(-18.0f, 160.0f, 0.0f));
	Moon->SetIntensity(0.25f);
	Moon->SetLightColor(FLinearColor(0.55f, 0.65f, 0.9f));
	Moon->RegisterComponent();
	Generated.Add(Moon);

	USkyLightComponent* Sky = NewObject<USkyLightComponent>(this, TEXT("Env_SkyLight"));
	Sky->SetMobility(EComponentMobility::Movable);
	Sky->SetupAttachment(GetRootComponent());
	Sky->SetWorldLocation(FVector(0.0, 1340.0, 250.0)); // capture from the open arcade, not the lobby floor
	Sky->SourceType = ESkyLightSourceType::SLS_CapturedScene;
	Sky->SetIntensity(static_cast<float>(ConfessionData::GetNumber(Env, TEXT("skylight_intensity"), 0.25)));
	Sky->SetLightColor(ConfessionData::GetColor(Env, TEXT("skylight_color"), FLinearColor(0.55f, 0.62f, 0.78f)));
	Sky->bLowerHemisphereIsBlack = true;
	Sky->RegisterComponent();
	Sky->RecaptureSky();
	Generated.Add(Sky);

	UExponentialHeightFogComponent* Fog = NewObject<UExponentialHeightFogComponent>(this, TEXT("Env_Fog"));
	Fog->SetupAttachment(GetRootComponent());
	Fog->SetFogDensity(static_cast<float>(ConfessionData::GetNumber(Env, TEXT("fog_density"), 0.012)));
	Fog->SetFogInscatteringColor(ConfessionData::GetColor(Env, TEXT("fog_color"), FLinearColor(0.18f, 0.21f, 0.26f)));
	Fog->SetFogHeightFalloff(0.6f);
	Fog->RegisterComponent();
	Generated.Add(Fog);

	// Bounded exposure: dark stays dark, but the navigation lights never blow out.
	UPostProcessComponent* PP = NewObject<UPostProcessComponent>(this, TEXT("Env_PostProcess"));
	PP->SetupAttachment(GetRootComponent());
	PP->bUnbound = true;
	FPostProcessSettings& S = PP->Settings;
	S.bOverride_AutoExposureMinBrightness = true;
	S.AutoExposureMinBrightness = static_cast<float>(ConfessionData::GetNumber(Env, TEXT("auto_exposure_min_ev100"), -1.5));
	S.bOverride_AutoExposureMaxBrightness = true;
	S.AutoExposureMaxBrightness = static_cast<float>(ConfessionData::GetNumber(Env, TEXT("auto_exposure_max_ev100"), 2.0));
	S.bOverride_AutoExposureBias = true;
	S.AutoExposureBias = static_cast<float>(ConfessionData::GetNumber(Env, TEXT("exposure_bias"), 0.0));
	S.bOverride_VignetteIntensity = true;
	S.VignetteIntensity = 0.3f;
	S.bOverride_MotionBlurAmount = true;
	S.MotionBlurAmount = 0.0f; // accessibility default: off
	PP->RegisterComponent();
	Generated.Add(PP);
}

void AConfessionGreyboxBuilder::BuildAudio(const FConfessionLayout& Layout)
{
	UConfessionAudioSubsystem* Audio = GetWorld()->GetSubsystem<UConfessionAudioSubsystem>();
	if (!Audio)
	{
		return;
	}
	for (const TSharedPtr<FJsonObject>& E : Layout.AudioEmitters)
	{
		const FString Sound = ConfessionData::GetString(E, TEXT("sound"));
		const FVector Pos = ConfessionData::ToUE(ConfessionData::GetVec3(E, TEXT("pos")));
		const float Volume = static_cast<float>(ConfessionData::GetNumber(E, TEXT("volume"), 1.0));
		const float Radius = static_cast<float>(ConfessionData::GetNumber(E, TEXT("radius_m"), 15.0) * 100.0);
		if (ConfessionData::GetBool(E, TEXT("loop"), false))
		{
			USceneComponent* Anchor = NewObject<USceneComponent>(this, FName(*ConfessionData::GetString(E, TEXT("id"))));
			Anchor->SetupAttachment(GetRootComponent());
			Anchor->SetWorldLocation(Pos);
			Anchor->RegisterComponent();
			Generated.Add(Anchor);
			if (UAudioComponent* AC = Audio->CreateAttached(Sound, Anchor, true, Volume, Radius, true))
			{
				AC->Play(FMath::FRandRange(0.0f, 2.0f));
				Generated.Add(AC);
			}
		}
		else
		{
			FIntervalEmitter IE;
			IE.SoundId = Sound;
			IE.Location = Pos;
			IE.Volume = Volume;
			IE.RadiusCm = Radius;
			IE.IntervalSeconds = ConfessionData::GetVec2(E, TEXT("interval_s"), FVector2D(20.0, 40.0));
			IE.FirstDelaySeconds = ConfessionData::GetVec2(E, TEXT("first_delay_s"), FVector2D(-1.0, -1.0));
			ScheduleIntervalSound(IntervalEmitters.Add(IE));
		}
	}
}

void AConfessionGreyboxBuilder::ScheduleIntervalSound(int32 EmitterIndex)
{
	if (!IntervalEmitters.IsValidIndex(EmitterIndex))
	{
		return;
	}
	FIntervalEmitter& IE = IntervalEmitters[EmitterIndex];
	const FVector2D Range = (!IE.bFirstDone && IE.FirstDelaySeconds.X >= 0.0) ? IE.FirstDelaySeconds : IE.IntervalSeconds;
	IE.bFirstDone = true;
	const float Delay = FMath::FRandRange(static_cast<float>(Range.X), static_cast<float>(Range.Y));
	if (IntervalTimers.Num() <= EmitterIndex)
	{
		IntervalTimers.SetNum(EmitterIndex + 1);
	}
	TWeakObjectPtr<AConfessionGreyboxBuilder> Weak(this);
	GetWorld()->GetTimerManager().SetTimer(IntervalTimers[EmitterIndex], FTimerDelegate::CreateLambda([Weak, EmitterIndex]()
	{
		if (!Weak.IsValid())
		{
			return;
		}
		const FIntervalEmitter& E = Weak->IntervalEmitters[EmitterIndex];
		if (UConfessionAudioSubsystem* A = Weak->GetWorld()->GetSubsystem<UConfessionAudioSubsystem>())
		{
			A->PlayAt(E.SoundId, E.Location, E.Volume, E.RadiusCm, 1.0f, true);
		}
		Weak->ScheduleIntervalSound(EmitterIndex);
	}), Delay, false);
}

void AConfessionGreyboxBuilder::SpawnInteractables(const FConfessionLayout& Layout)
{
	UWorld* World = GetWorld();
	for (const TSharedPtr<FJsonObject>& I : Layout.Interactables)
	{
		const FString Type = ConfessionData::GetString(I, TEXT("type"));
		const FString Id = ConfessionData::GetString(I, TEXT("id"));
		if (Type == TEXT("checkpoint"))
		{
			const FTransform T(ConfessionData::ToUE(ConfessionData::GetVec3(I, TEXT("center"))));
			AConfessionCheckpoint* Cp = World->SpawnActorDeferred<AConfessionCheckpoint>(AConfessionCheckpoint::StaticClass(), T);
			if (Cp)
			{
				Cp->InitFromLayout(I);
				Cp->FinishSpawning(T);
				SpawnedActors.Add(Cp);
				++NumInteractables;
			}
			continue;
		}

		UClass* Class = nullptr;
		FTransform T = FTransform::Identity;
		if (Type == TEXT("door"))
		{
			Class = AConfessionDoor::StaticClass();
			T.SetLocation(ConfessionData::ToUE(ConfessionData::GetVec3(I, TEXT("hinge"))));
		}
		else if (Type == TEXT("pickup") || Type == TEXT("readable"))
		{
			Class = AConfessionPickup::StaticClass();
		}
		else if (Type == TEXT("phone"))
		{
			Class = AConfessionPhone::StaticClass();
		}
		else if (Type == TEXT("displacement_anomaly"))
		{
			Class = AConfessionDisplacementAnomaly::StaticClass();
		}
		if (!Class)
		{
			UE_LOG(LogConfession, Warning, TEXT("Unknown interactable type '%s' (%s)"), *Type, *Id);
			continue;
		}
		if (T.GetLocation().IsZero())
		{
			T.SetLocation(ConfessionData::ToUE(ConfessionData::GetVec3(I, TEXT("center"))));
		}
		AConfessionInteractable* Actor = World->SpawnActorDeferred<AConfessionInteractable>(Class, T);
		if (!Actor)
		{
			continue;
		}
		Actor->InitFromLayout(I, Layout);
		Actor->FinishSpawning(T);
		SpawnedActors.Add(Actor);
		++NumInteractables;
	}
}
