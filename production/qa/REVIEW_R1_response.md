# Response to REVIEW_R1_ue_source.md (producer / integration)

Reviewer findings are not edited. Disposition per finding; "FIXED" means changed in source/data, **not** compiled (no UE here).

| ID | Sev | Disposition |
|---|---|---|
| R-01 | P1 | FIXED: `Materials/MaterialInstanceDynamic.h` included in Interactable, Door, GreyboxBuilder. |
| R-02 | P2 | FIXED: `Engine/World.h` included in Door, Pickup. |
| R-03 | P2 | FIXED: `Engine/TimerHandle.h` included in GreyboxBuilder.h. |
| R-04 | P2 | FIXED: file-scope `using namespace` removed from ConfessionDoor.cpp (fully qualified). |
| R-05 | P2 | FIXED: builder root is Static mobility. |
| R-06 | P1 | FIXED: reject line uses `{number}` from `previous_number`, held 6 s; release appends a second line instead of replacing; release delay 1.4 -> 2.6 s. Falsification test kept as an open G9 item. |
| R-07 | P1 | FIXED: door stays focusable while releasing with prompt "读卡中…… / Reading..."; Use() is a no-op then. |
| R-08 | P2 | FIXED: occlusion only for ambient emitters (loops + queue chime); feedback/footstep sounds unoccluded. |
| R-09 | P2 | FIXED: duplicate `L_CardSlotPilot` removed; the pickup's own pilot lamp is the only one and goes out when the card is taken. |
| R-10 | P2 | FIXED: "phone rings once" now fires 0.8 s after the card text is closed; answer window ring + 6 s. |
| R-11 | P2 | PARTIAL: seen range 8 m. Glint / sound offset from the beat sheet NOT built (needs audio + lighting pass). |
| R-12 | P2 | FIXED: checkpoints only advance (reached set). |
| R-13 | P2 | PARTIAL: phones reset ring/relay on respawn; door lamp flash and read-docs policy unchanged. |
| R-14 | P2 | FIXED: on-screen red error with the expected path when the layout fails to load. |
| R-15 | P2 | FIXED: `SetActorLabel` removed from runtime spawns. |
| R-16 | P2 | DEFERRED: greybox material has only Color; real master material needs the editor (M3). |
| R-17 | P2 | FIXED: skylight capture placed in the open arcade (UE 0, 1340, 250). |
| R-18 | P2 | FIXED: first queue chime 5–9 s after start (`first_delay_s`). |
| R-19 | P2 | PARTIAL: number is formatted from data; panel-lamp facing still assumes south-facing readers (true for both doors in L0_B01). |
| R-20 | P2 | DEFERRED: per-play procedural wave allocation; replace with imported USoundWave assets once the editor exists (profile first). |
| R-21 | P2 | DEFERRED: gamepad glyphs (UX task). |
| R-22 | P2 | PARTIAL: stale TP_FirstPerson redirect removed; Entry startup map kept deliberately (no .umap may be authored without the editor); Python/EditorScripting kept for `production/scripts/unreal_import_validate.py`. |
| R-23 | P2 | FIXED: `DefaultEditorPerProjectUserSettings.ini` disables content-directory auto import. |
| R-24 | P2 | FIXED: comment corrected. |
| R-25 | P2 canon | FIXED: phone text back to canon "只听到拨号静音" (dial tone sound removed); invented second-phone line removed. "临时复核员 21" kept: it is canon in GDD v0.2 ("主角 / 临时复核员 21"). |
| R-26 | P2 plan | OPEN -> CR-0002: drawer interaction (VS02) not built; outline says 访客卡 vs bible 工号卡 — director decision. |
