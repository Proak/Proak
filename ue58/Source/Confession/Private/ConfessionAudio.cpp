// The Unfinished Confession - runtime WAV playback (see header).
#include "ConfessionAudio.h"

#include "ConfessionTypes.h"
#include "Components/AudioComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundWaveProcedural.h"
#include "TimerManager.h"

namespace
{
uint32 ReadU32(const TArray<uint8>& B, int32 At)
{
	return static_cast<uint32>(B[At]) | (static_cast<uint32>(B[At + 1]) << 8) | (static_cast<uint32>(B[At + 2]) << 16) |
		(static_cast<uint32>(B[At + 3]) << 24);
}
uint16 ReadU16(const TArray<uint8>& B, int32 At)
{
	return static_cast<uint16>(B[At] | (B[At + 1] << 8));
}

/** Minimal RIFF/WAVE reader: PCM, 16-bit, mono only (the tools/audio contract). */
bool ParseWav(const TArray<uint8>& File, FConfessionPcm& Out, FString& Error)
{
	if (File.Num() < 44 || FMemory::Memcmp(File.GetData(), "RIFF", 4) != 0 || FMemory::Memcmp(File.GetData() + 8, "WAVE", 4) != 0)
	{
		Error = TEXT("not a RIFF/WAVE file");
		return false;
	}
	int32 At = 12;
	bool bFmt = false;
	while (At + 8 <= File.Num())
	{
		const uint32 ChunkSize = ReadU32(File, At + 4);
		const int32 Body = At + 8;
		if (ChunkSize > static_cast<uint32>(File.Num() - Body))
		{
			Error = TEXT("truncated chunk");
			return false;
		}
		if (FMemory::Memcmp(File.GetData() + At, "fmt ", 4) == 0 && ChunkSize >= 16)
		{
			const uint16 Format = ReadU16(File, Body);
			const uint16 Channels = ReadU16(File, Body + 2);
			Out.SampleRate = static_cast<int32>(ReadU32(File, Body + 4));
			const uint16 Bits = ReadU16(File, Body + 14);
			if (Format != 1 || Channels != 1 || Bits != 16)
			{
				Error = FString::Printf(TEXT("unsupported format=%u channels=%u bits=%u (need PCM mono 16-bit)"), Format, Channels, Bits);
				return false;
			}
			bFmt = true;
		}
		else if (FMemory::Memcmp(File.GetData() + At, "data", 4) == 0)
		{
			if (!bFmt)
			{
				Error = TEXT("data before fmt");
				return false;
			}
			Out.Bytes.Append(File.GetData() + Body, static_cast<int32>(ChunkSize & ~1u));
			Out.DurationSeconds = static_cast<float>(Out.Bytes.Num() / 2) / static_cast<float>(FMath::Max(1, Out.SampleRate));
			return Out.Bytes.Num() > 0;
		}
		At = Body + static_cast<int32>(ChunkSize) + static_cast<int32>(ChunkSize & 1u);
	}
	Error = TEXT("no data chunk");
	return false;
}
} // namespace

FString UConfessionAudioSubsystem::PathFor(const FString& SoundId)
{
	return FPaths::ConvertRelativePathToFull(FPaths::ProjectContentDir() / TEXT("Confession/Audio") / (SoundId + TEXT(".wav")));
}

TSharedPtr<FConfessionPcm, ESPMode::ThreadSafe> UConfessionAudioSubsystem::Load(const FString& SoundId)
{
	if (const TSharedPtr<FConfessionPcm, ESPMode::ThreadSafe>* Found = Cache.Find(SoundId))
	{
		return *Found;
	}
	if (SoundId.IsEmpty() || Missing.Contains(SoundId))
	{
		return nullptr;
	}
	TArray<uint8> File;
	FString Error;
	TSharedPtr<FConfessionPcm, ESPMode::ThreadSafe> Pcm = MakeShared<FConfessionPcm, ESPMode::ThreadSafe>();
	if (!FFileHelper::LoadFileToArray(File, *PathFor(SoundId)) || !ParseWav(File, *Pcm, Error))
	{
		UE_LOG(LogConfession, Warning, TEXT("Sound '%s' unavailable (%s) at %s"), *SoundId,
			Error.IsEmpty() ? TEXT("missing file") : *Error, *PathFor(SoundId));
		Missing.Add(SoundId);
		return nullptr;
	}
	Cache.Add(SoundId, Pcm);
	return Pcm;
}

bool UConfessionAudioSubsystem::HasSound(const FString& SoundId) { return Load(SoundId).IsValid(); }

float UConfessionAudioSubsystem::DurationOf(const FString& SoundId)
{
	const TSharedPtr<FConfessionPcm, ESPMode::ThreadSafe> Pcm = Load(SoundId);
	return Pcm.IsValid() ? Pcm->DurationSeconds : 0.0f;
}

USoundWaveProcedural* UConfessionAudioSubsystem::MakeWave(const TSharedPtr<FConfessionPcm, ESPMode::ThreadSafe>& Pcm, bool bLoop)
{
	USoundWaveProcedural* Wave = NewObject<USoundWaveProcedural>(this);
	Wave->SetSampleRate(static_cast<uint32>(Pcm->SampleRate));
	Wave->NumChannels = 1;
	Wave->SoundGroup = SOUNDGROUP_Default;
	Wave->bLooping = bLoop;
	Wave->Duration = bLoop ? INDEFINITELY_LOOPING_DURATION : Pcm->DurationSeconds;
	Wave->QueueAudio(Pcm->Bytes.GetData(), Pcm->Bytes.Num());
	if (bLoop)
	{
		Wave->QueueAudio(Pcm->Bytes.GetData(), Pcm->Bytes.Num());
		// Called from the audio thread when the queue runs low: append another seamless copy.
		Wave->OnSoundWaveProceduralUnderflow.BindLambda([Pcm](USoundWaveProcedural* W, int32 /*SamplesRequired*/)
		{
			W->QueueAudio(Pcm->Bytes.GetData(), Pcm->Bytes.Num());
		});
	}
	return Wave;
}

USoundAttenuation* UConfessionAudioSubsystem::AttenuationFor(float RadiusCm)
{
	const int32 Key = FMath::RoundToInt(RadiusCm / 50.0f);
	if (TObjectPtr<USoundAttenuation>* Found = AttenuationByRadius.Find(Key))
	{
		return Found->Get();
	}
	USoundAttenuation* Att = NewObject<USoundAttenuation>(this);
	FSoundAttenuationSettings& S = Att->Attenuation;
	S.bAttenuate = true;
	S.bSpatialize = true;
	S.AttenuationShape = EAttenuationShape::Sphere;
	S.AttenuationShapeExtents = FVector(60.0, 0.0, 0.0);
	S.FalloffDistance = FMath::Max(100.0f, RadiusCm);
	S.DistanceAlgorithm = EAttenuationDistanceModel::NaturalSound;
	// Walls and closed doors muffle sources: a cheap, physically motivated cue for "where is it".
	S.bEnableOcclusion = true;
	S.OcclusionTraceChannel = ECC_Visibility;
	S.OcclusionLowPassFilterFrequency = 1400.0f;
	S.OcclusionVolumeAttenuation = 0.45f;
	S.OcclusionInterpolationTime = 0.2f;
	AttenuationByRadius.Add(Key, Att);
	return Att;
}

UAudioComponent* UConfessionAudioSubsystem::PlayAt(const FString& SoundId, const FVector& Location, float Volume, float RadiusCm, float Pitch)
{
	const TSharedPtr<FConfessionPcm, ESPMode::ThreadSafe> Pcm = Load(SoundId);
	UWorld* World = GetWorld();
	if (!Pcm.IsValid() || !World)
	{
		return nullptr;
	}
	USoundWaveProcedural* Wave = MakeWave(Pcm, false);
	UAudioComponent* Comp = UGameplayStatics::SpawnSoundAtLocation(World, Wave, Location, FRotator::ZeroRotator, Volume, Pitch,
		0.0f, AttenuationFor(RadiusCm), nullptr, true);
	if (Comp)
	{
		// Procedural waves do not always report completion; stop explicitly after the clip length.
		TWeakObjectPtr<UAudioComponent> Weak(Comp);
		FTimerHandle Handle;
		World->GetTimerManager().SetTimer(Handle, FTimerDelegate::CreateLambda([Weak]()
		{
			if (Weak.IsValid())
			{
				Weak->Stop();
			}
		}), Pcm->DurationSeconds / FMath::Max(0.1f, Pitch) + 0.15f, false);
	}
	return Comp;
}

UAudioComponent* UConfessionAudioSubsystem::CreateAttached(const FString& SoundId, USceneComponent* AttachTo, bool bLoop, float Volume, float RadiusCm)
{
	const TSharedPtr<FConfessionPcm, ESPMode::ThreadSafe> Pcm = Load(SoundId);
	if (!Pcm.IsValid() || !AttachTo)
	{
		return nullptr;
	}
	UAudioComponent* Comp = NewObject<UAudioComponent>(AttachTo->GetOwner());
	Comp->bAutoActivate = false;
	Comp->SetupAttachment(AttachTo);
	Comp->RegisterComponent();
	Comp->SetSound(MakeWave(Pcm, bLoop));
	Comp->SetVolumeMultiplier(Volume);
	Comp->AttenuationSettings = AttenuationFor(RadiusCm);
	return Comp;
}
