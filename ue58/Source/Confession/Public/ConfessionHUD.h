// The Unfinished Confession - minimal diegetic-leaning HUD built with Slate (no UMG assets required).
// Shows: centre dot, interaction prompt, one objective line (fades), one message/subtitle line,
// a document reader (E closes) and the evidence notebook (Tab). No meters, no quantified psyche.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "ConfessionHUD.generated.h"

class SWidget;

UCLASS()
class CONFESSION_API AConfessionHUD : public AHUD
{
	GENERATED_BODY()

public:
	AConfessionHUD();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
	virtual void Tick(float DeltaSeconds) override;

	void SetPrompt(const FText& InPrompt, bool bHasTarget);
	void ShowObjective(const FText& InObjective);
	void ShowMessage(const FText& InMessage, float Seconds = 3.5f);
	void PulseCheckpoint(const FText& Label);
	void OpenDocument(const FText& Title, const FText& Body);
	void CloseDocument();
	bool IsDocumentOpen() const { return bDocumentOpen; }
	void SetNotebook(bool bOpen, const FText& Content);
	bool IsNotebookOpen() const { return bNotebookOpen; }

	// Read by Slate attribute lambdas.
	FText Prompt;
	FText Objective;
	FText Message;
	FText CheckpointLabel;
	FText DocTitle;
	FText DocBody;
	FText NotebookText;
	FText CloseHint;
	bool bFocus = false;
	bool bDocumentOpen = false;
	bool bNotebookOpen = false;
	float ObjectiveAlpha = 0.0f;
	float MessageAlpha = 0.0f;
	float CheckpointAlpha = 0.0f;

private:
	TSharedPtr<SWidget> Root;
	float ObjectiveTimer = 0.0f;
	float MessageTimer = 0.0f;
	float CheckpointTimer = 0.0f;
};
