// The Unfinished Confession - Slate HUD.
#include "ConfessionHUD.h"

#include "ConfessionGameMode.h"
#include "ConfessionTypes.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

static TAutoConsoleVariable<int32> CVarObjectiveReminder(
	TEXT("confession.ObjectiveReminder"), 1,
	TEXT("1 = keep the current objective faintly on screen after it fades in (accessibility), 0 = hide after showing."),
	ECVF_Default);

AConfessionHUD::AConfessionHUD()
{
	PrimaryActorTick.bCanEverTick = true;
}

void AConfessionHUD::BeginPlay()
{
	Super::BeginPlay();
	UGameViewportClient* Viewport = GetWorld() ? GetWorld()->GetGameViewport() : nullptr;
	if (!Viewport)
	{
		return; // e.g. -nullrhi automation: logic still runs, nothing to draw
	}
	if (const AConfessionGameMode* GM = GetWorld()->GetAuthGameMode<AConfessionGameMode>())
	{
		CloseHint = GM->GetLayout().Message(TEXT("ui_doc_close"));
	}
	TWeakObjectPtr<AConfessionHUD> W(this);
	const FSlateFontInfo Small = FCoreStyle::GetDefaultFontStyle("Regular", 15);
	const FSlateFontInfo Body = FCoreStyle::GetDefaultFontStyle("Regular", 19);
	const FSlateFontInfo Title = FCoreStyle::GetDefaultFontStyle("Bold", 22);
	const FSlateBrush* White = FCoreStyle::Get().GetBrush("WhiteBrush");
	const FLinearColor Paper(0.86f, 0.83f, 0.76f, 1.0f);

	auto Alpha = [](float A, const FLinearColor& C) { return FSlateColor(FLinearColor(C.R, C.G, C.B, A)); };

	Root = SNew(SOverlay)
		// centre dot: brightens when something usable is in focus
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
		[
			SNew(SBox).WidthOverride(4.0f).HeightOverride(4.0f)
			[
				SNew(SBorder).BorderImage(White)
				.BorderBackgroundColor_Lambda([W]() { return FSlateColor(FLinearColor(1, 1, 1, (W.IsValid() && W->bFocus) ? 0.9f : 0.25f)); })
			]
		]
		// interaction prompt just under the dot
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center).Padding(FMargin(0, 70, 0, 0))
		[
			SNew(STextBlock).Font(Small).ShadowOffset(FVector2D(1, 1))
			.Text_Lambda([W]() { return (W.IsValid() && W->bFocus && !W->bDocumentOpen) ? W->Prompt : FText::GetEmpty(); })
			.ColorAndOpacity(FSlateColor(Paper))
		]
		// objective line, top-left
		+ SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Top).Padding(FMargin(42, 36, 0, 0))
		[
			SNew(STextBlock).Font(Small).ShadowOffset(FVector2D(1, 1))
			.Text_Lambda([W]() { return W.IsValid() ? W->Objective : FText::GetEmpty(); })
			.ColorAndOpacity_Lambda([W, Alpha, Paper]() { return Alpha(W.IsValid() ? W->ObjectiveAlpha : 0.0f, Paper); })
		]
		// checkpoint whisper, bottom-right
		+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Bottom).Padding(FMargin(0, 0, 42, 36))
		[
			SNew(STextBlock).Font(Small)
			.Text_Lambda([W]() { return W.IsValid() ? W->CheckpointLabel : FText::GetEmpty(); })
			.ColorAndOpacity_Lambda([W, Alpha, Paper]() { return Alpha(W.IsValid() ? W->CheckpointAlpha * 0.7f : 0.0f, Paper); })
		]
		// message / subtitle line, lower third
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Bottom).Padding(FMargin(0, 0, 0, 120))
		[
			SNew(SBox).MaxDesiredWidth(900.0f)
			[
				SNew(STextBlock).Font(Body).AutoWrapText(true).Justification(ETextJustify::Center).ShadowOffset(FVector2D(1, 1))
				.Text_Lambda([W]() { return W.IsValid() ? W->Message : FText::GetEmpty(); })
				.ColorAndOpacity_Lambda([W, Alpha, Paper]() { return Alpha(W.IsValid() ? W->MessageAlpha : 0.0f, Paper); })
			]
		]
		// document reader
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
		[
			SNew(SBox).WidthOverride(640.0f)
			.Visibility_Lambda([W]() { return (W.IsValid() && W->bDocumentOpen) ? EVisibility::Visible : EVisibility::Collapsed; })
			[
				SNew(SBorder).BorderImage(White).BorderBackgroundColor(FSlateColor(FLinearColor(0.015f, 0.016f, 0.018f, 0.88f)))
				.Padding(FMargin(36, 30))
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 14)
					[
						SNew(STextBlock).Font(Title).ColorAndOpacity(FSlateColor(Paper))
						.Text_Lambda([W]() { return W.IsValid() ? W->DocTitle : FText::GetEmpty(); })
					]
					+ SVerticalBox::Slot().AutoHeight()
					[
						SNew(STextBlock).Font(Body).AutoWrapText(true).ColorAndOpacity(FSlateColor(Paper))
						.Text_Lambda([W]() { return W.IsValid() ? W->DocBody : FText::GetEmpty(); })
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0, 22, 0, 0).HAlign(HAlign_Right)
					[
						SNew(STextBlock).Font(Small).ColorAndOpacity(FSlateColor(FLinearColor(0.6f, 0.6f, 0.58f, 1.0f)))
						.Text_Lambda([W]() { return W.IsValid() ? W->CloseHint : FText::GetEmpty(); })
					]
				]
			]
		]
		// evidence notebook (Tab)
		+ SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Center).Padding(FMargin(42, 0, 0, 0))
		[
			SNew(SBox).WidthOverride(520.0f)
			.Visibility_Lambda([W]() { return (W.IsValid() && W->bNotebookOpen) ? EVisibility::Visible : EVisibility::Collapsed; })
			[
				SNew(SBorder).BorderImage(White).BorderBackgroundColor(FSlateColor(FLinearColor(0.02f, 0.02f, 0.02f, 0.82f)))
				.Padding(FMargin(28, 24))
				[
					SNew(STextBlock).Font(Small).AutoWrapText(true).ColorAndOpacity(FSlateColor(Paper))
					.Text_Lambda([W]() { return W.IsValid() ? W->NotebookText : FText::GetEmpty(); })
				]
			]
		];

	Viewport->AddViewportWidgetContent(Root.ToSharedRef(), 10);
}

void AConfessionHUD::EndPlay(const EEndPlayReason::Type Reason)
{
	if (Root.IsValid())
	{
		if (UGameViewportClient* Viewport = GetWorld() ? GetWorld()->GetGameViewport() : nullptr)
		{
			Viewport->RemoveViewportWidgetContent(Root.ToSharedRef());
		}
		Root.Reset();
	}
	Super::EndPlay(Reason);
}

void AConfessionHUD::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	auto Fade = [DeltaSeconds](float& Timer, float& AlphaOut, float Floor)
	{
		if (Timer > 0.0f)
		{
			Timer -= DeltaSeconds;
			AlphaOut = FMath::FInterpTo(AlphaOut, 1.0f, DeltaSeconds, 6.0f);
		}
		else
		{
			AlphaOut = FMath::FInterpTo(AlphaOut, Floor, DeltaSeconds, 1.5f);
		}
	};
	Fade(ObjectiveTimer, ObjectiveAlpha, CVarObjectiveReminder.GetValueOnGameThread() ? 0.35f : 0.0f);
	Fade(MessageTimer, MessageAlpha, 0.0f);
	Fade(CheckpointTimer, CheckpointAlpha, 0.0f);
}

void AConfessionHUD::SetPrompt(const FText& InPrompt, bool bHasTarget)
{
	Prompt = bHasTarget ? FText::Format(FText::FromString(TEXT("[E]  {0}")), InPrompt) : FText::GetEmpty();
	bFocus = bHasTarget;
}

void AConfessionHUD::ShowObjective(const FText& InObjective)
{
	Objective = InObjective;
	ObjectiveTimer = 6.0f;
}

void AConfessionHUD::ShowMessage(const FText& InMessage, float Seconds)
{
	Message = InMessage;
	MessageTimer = Seconds;
}

void AConfessionHUD::PulseCheckpoint(const FText& Label)
{
	CheckpointLabel = Label;
	CheckpointTimer = 1.6f;
}

void AConfessionHUD::OpenDocument(const FText& Title, const FText& Body)
{
	DocTitle = Title;
	DocBody = Body;
	bDocumentOpen = true;
	bNotebookOpen = false;
}

void AConfessionHUD::CloseDocument() { bDocumentOpen = false; }

void AConfessionHUD::SetNotebook(bool bOpen, const FText& Content)
{
	bNotebookOpen = bOpen;
	NotebookText = Content;
	if (bOpen)
	{
		bDocumentOpen = false;
	}
}
