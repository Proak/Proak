// The Unfinished Confession - level data loading and shared helpers.
#include "ConfessionTypes.h"

#include "Engine/StaticMesh.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

DEFINE_LOG_CATEGORY(LogConfession);

static TAutoConsoleVariable<int32> CVarConfessionLanguage(
	TEXT("confession.Language"), 0,
	TEXT("0 = Chinese (default), 1 = English. Applies to prompts, objectives, documents and messages."),
	ECVF_Default);

// ------------------------------------------------------------------ ConfessionData
namespace ConfessionData
{
FVector ToUE(const FVector& M) { return FVector(M.X * 100.0, -M.Y * 100.0, M.Z * 100.0); }
FVector ToUESize(const FVector& M) { return FVector(M.X * 100.0, M.Y * 100.0, M.Z * 100.0); }

float YawFromFacing(double FX, double FY)
{
	// Layout facing (FX, FY) maps to UE direction (FX, -FY).
	return static_cast<float>(FMath::RadiansToDegrees(FMath::Atan2(-FY, FX)));
}

FVector GetVec3(const TSharedPtr<FJsonObject>& Obj, const TCHAR* Field, const FVector& Default)
{
	const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
	if (!Obj.IsValid() || !Obj->TryGetArrayField(Field, Arr) || Arr->Num() < 3)
	{
		return Default;
	}
	return FVector((*Arr)[0]->AsNumber(), (*Arr)[1]->AsNumber(), (*Arr)[2]->AsNumber());
}

FVector2D GetVec2(const TSharedPtr<FJsonObject>& Obj, const TCHAR* Field, const FVector2D& Default)
{
	const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
	if (!Obj.IsValid() || !Obj->TryGetArrayField(Field, Arr) || Arr->Num() < 2)
	{
		return Default;
	}
	return FVector2D((*Arr)[0]->AsNumber(), (*Arr)[1]->AsNumber());
}

FString GetString(const TSharedPtr<FJsonObject>& Obj, const TCHAR* Field, const FString& Default)
{
	FString Out;
	return (Obj.IsValid() && Obj->TryGetStringField(Field, Out)) ? Out : Default;
}

double GetNumber(const TSharedPtr<FJsonObject>& Obj, const TCHAR* Field, double Default)
{
	double Out = 0.0;
	return (Obj.IsValid() && Obj->TryGetNumberField(Field, Out)) ? Out : Default;
}

bool GetBool(const TSharedPtr<FJsonObject>& Obj, const TCHAR* Field, bool Default)
{
	bool Out = false;
	return (Obj.IsValid() && Obj->TryGetBoolField(Field, Out)) ? Out : Default;
}

FLinearColor GetColor(const TSharedPtr<FJsonObject>& Obj, const TCHAR* Field, const FLinearColor& Default)
{
	const FVector V = GetVec3(Obj, Field, FVector(Default.R, Default.G, Default.B));
	return FLinearColor(static_cast<float>(V.X), static_cast<float>(V.Y), static_cast<float>(V.Z), 1.0f);
}

bool UseEnglish() { return CVarConfessionLanguage.GetValueOnGameThread() == 1; }

FText LocalizedObject(const TSharedPtr<FJsonObject>& TextObj)
{
	if (!TextObj.IsValid())
	{
		return FText::GetEmpty();
	}
	FString S;
	if (UseEnglish() && TextObj->TryGetStringField(TEXT("en"), S))
	{
		return FText::FromString(S);
	}
	if (TextObj->TryGetStringField(TEXT("zh"), S))
	{
		return FText::FromString(S);
	}
	return FText::GetEmpty();
}

FText Localized(const TSharedPtr<FJsonObject>& Obj, const TCHAR* Field)
{
	const TSharedPtr<FJsonObject>* TextObj = nullptr;
	if (!Obj.IsValid() || !Obj->TryGetObjectField(Field, TextObj))
	{
		return FText::GetEmpty();
	}
	return LocalizedObject(*TextObj);
}
} // namespace ConfessionData

// ------------------------------------------------------------------ FConfessionLayout
FString FConfessionLayout::PathFor(const FString& LevelId)
{
	return FPaths::ConvertRelativePathToFull(
		FPaths::ProjectContentDir() / TEXT("Confession/Data") / (LevelId + TEXT("_layout.json")));
}

static void CollectObjects(const TSharedPtr<FJsonObject>& Root, const TCHAR* Field, TArray<TSharedPtr<FJsonObject>>& Out)
{
	const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
	if (Root->TryGetArrayField(Field, Arr))
	{
		for (const TSharedPtr<FJsonValue>& V : *Arr)
		{
			if (V.IsValid() && V->Type == EJson::Object)
			{
				Out.Add(V->AsObject());
			}
		}
	}
}

bool FConfessionLayout::LoadFromFile(const FString& AbsPath, FString& OutError)
{
	*this = FConfessionLayout();
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *AbsPath))
	{
		OutError = FString::Printf(TEXT("cannot read %s"), *AbsPath);
		return false;
	}
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		OutError = FString::Printf(TEXT("invalid JSON in %s"), *AbsPath);
		return false;
	}

	Id = ConfessionData::GetString(Root, TEXT("id"));
	LayoutVersion = ConfessionData::GetString(Root, TEXT("layout_version"));

	const TSharedPtr<FJsonObject>* Player = nullptr;
	if (Root->TryGetObjectField(TEXT("player"), Player))
	{
		PlayerStartCm = ConfessionData::ToUE(ConfessionData::GetVec3(*Player, TEXT("start")));
		const FVector2D Facing = ConfessionData::GetVec2(*Player, TEXT("facing"), FVector2D(0.0, 1.0));
		PlayerStartYawDeg = ConfessionData::YawFromFacing(Facing.X, Facing.Y);
		UseDistanceCm = static_cast<float>(ConfessionData::GetNumber(*Player, TEXT("use_distance_m"), 2.6) * 100.0);
	}

	const TSharedPtr<FJsonObject>* MatObj = nullptr;
	if (Root->TryGetObjectField(TEXT("materials"), MatObj))
	{
		for (const auto& Pair : (*MatObj)->Values)
		{
			const TSharedPtr<FJsonObject> M = Pair.Value.IsValid() ? Pair.Value->AsObject() : nullptr;
			FConfessionMaterialDef Def;
			Def.Color = ConfessionData::GetColor(M, TEXT("color"), FLinearColor::Gray);
			Def.Roughness = static_cast<float>(ConfessionData::GetNumber(M, TEXT("roughness"), 0.8));
			Def.Metallic = static_cast<float>(ConfessionData::GetNumber(M, TEXT("metallic"), 0.0));
			Def.Emissive = static_cast<float>(ConfessionData::GetNumber(M, TEXT("emissive"), 0.0));
			Materials.Add(Pair.Key, Def);
		}
	}

	TArray<TSharedPtr<FJsonObject>> GeoObjs;
	CollectObjects(Root, TEXT("geometry"), GeoObjs);
	for (const TSharedPtr<FJsonObject>& G : GeoObjs)
	{
		FConfessionBox B;
		B.Id = ConfessionData::GetString(G, TEXT("id"));
		B.CenterCm = ConfessionData::ToUE(ConfessionData::GetVec3(G, TEXT("center")));
		B.SizeCm = ConfessionData::ToUESize(ConfessionData::GetVec3(G, TEXT("size"), FVector(1.0)));
		B.Material = ConfessionData::GetString(G, TEXT("material"));
		B.Group = ConfessionData::GetString(G, TEXT("group"));
		B.bCollision = ConfessionData::GetBool(G, TEXT("collision"), true);
		Geometry.Add(B);
	}

	CollectObjects(Root, TEXT("interactables"), Interactables);
	CollectObjects(Root, TEXT("lights"), Lights);
	CollectObjects(Root, TEXT("audio_emitters"), AudioEmitters);
	CollectObjects(Root, TEXT("flow"), Flow);
	CollectObjects(Root, TEXT("autopilot"), Autopilot);
	CollectObjects(Root, TEXT("shots"), Shots);

	const TSharedPtr<FJsonObject>* Tmp = nullptr;
	if (Root->TryGetObjectField(TEXT("environment"), Tmp)) { Environment = *Tmp; }
	if (Root->TryGetObjectField(TEXT("documents"), Tmp)) { Documents = *Tmp; }
	if (Root->TryGetObjectField(TEXT("messages"), Tmp)) { Messages = *Tmp; }

	bValid = !Id.IsEmpty() && Geometry.Num() > 0 && Flow.Num() > 0;
	if (!bValid)
	{
		OutError = TEXT("layout missing id/geometry/flow");
	}
	return bValid;
}

const FConfessionMaterialDef& FConfessionLayout::MaterialOrDefault(const FString& Name) const
{
	static const FConfessionMaterialDef Fallback;
	const FConfessionMaterialDef* Found = Materials.Find(Name);
	return Found ? *Found : Fallback;
}

TSharedPtr<FJsonObject> FConfessionLayout::FindInteractable(const FString& InteractableId) const
{
	for (const TSharedPtr<FJsonObject>& I : Interactables)
	{
		if (ConfessionData::GetString(I, TEXT("id")) == InteractableId)
		{
			return I;
		}
	}
	return nullptr;
}

FText FConfessionLayout::Message(const FString& MessageId) const
{
	const TSharedPtr<FJsonObject>* M = nullptr;
	if (MessageId.IsEmpty() || !Messages.IsValid() || !Messages->TryGetObjectField(MessageId, M))
	{
		return FText::GetEmpty();
	}
	return ConfessionData::LocalizedObject(*M);
}

bool FConfessionLayout::Document(const FString& DocId, FText& OutTitle, FText& OutBody) const
{
	const TSharedPtr<FJsonObject>* D = nullptr;
	if (DocId.IsEmpty() || !Documents.IsValid() || !Documents->TryGetObjectField(DocId, D))
	{
		return false;
	}
	OutTitle = ConfessionData::Localized(*D, TEXT("title"));
	OutBody = ConfessionData::Localized(*D, TEXT("body"));
	return true;
}

// ------------------------------------------------------------------ ConfessionGreybox
namespace ConfessionGreybox
{
UStaticMesh* CubeMesh()
{
	static TWeakObjectPtr<UStaticMesh> Cached;
	if (!Cached.IsValid())
	{
		Cached = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
		if (!Cached.IsValid())
		{
			UE_LOG(LogConfession, Error, TEXT("Missing /Engine/BasicShapes/Cube - greybox cannot be built"));
		}
	}
	return Cached.Get();
}

UMaterialInstanceDynamic* MakeMaterial(UObject* Outer, const FConfessionMaterialDef& Def)
{
	static TWeakObjectPtr<UMaterialInterface> Base;
	if (!Base.IsValid())
	{
		Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
	}
	if (!Base.IsValid())
	{
		return nullptr;
	}
	UMaterialInstanceDynamic* MID = UMaterialInstanceDynamic::Create(Base.Get(), Outer);
	// BasicShapeMaterial exposes a "Color" vector parameter. Emissive surfaces are faked by
	// brightening the base colour; the real light comes from the layout's light list.
	FLinearColor C = Def.Color;
	if (Def.Emissive > 0.0f)
	{
		C = C * FMath::Clamp(Def.Emissive, 1.0f, 8.0f);
	}
	MID->SetVectorParameterValue(TEXT("Color"), C);
	return MID;
}
} // namespace ConfessionGreybox
