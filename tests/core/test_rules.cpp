// Unit tests for ue58/Source/Confession/Public/Core/ConfessionRules.h (engine independent).
// Each test encodes a design rule from the GDD / beat sheet, including its failure path.
#include "Core/ConfessionRules.h"

#include <cmath>
#include <cstdio>
#include <functional>
#include <string>
#include <vector>

using namespace ConfessionRules;

namespace
{
int GFailures = 0;
int GChecks = 0;
std::string GCurrent;

void Expect(bool bCond, const char* Expr, int Line)
{
    ++GChecks;
    if (!bCond)
    {
        ++GFailures;
        std::printf("  FAIL [%s] line %d: %s\n", GCurrent.c_str(), Line, Expr);
    }
}
#define EXPECT(c) Expect((c), #c, __LINE__)

struct TestCase
{
    const char* Name;
    std::function<void()> Fn;
};

void Run(double Seconds, double Dt, const std::function<void(double)>& Step)
{
    for (double T = 0.0; T < Seconds - 1e-9; T += Dt)
    {
        Step(Dt);
    }
}

// ------------------------------------------------------------------------------------------------
void TestObjectiveFlowInOrder()
{
    ObjectiveFlow Flow;
    Flow.SetSteps({{"find", "has_job_order"}, {"enter", "cp_lobby"}, {"card", "has_access_card"}, {"end", ""}});
    ProgressState S;
    EXPECT(!Flow.Advance(S));
    EXPECT(Flow.Current(S)->Id == "find");
    S.SetFlag("has_job_order");
    EXPECT(Flow.Advance(S));
    EXPECT(Flow.Current(S)->Id == "enter");
    S.SetFlag("cp_lobby");
    S.SetFlag("has_access_card");
    EXPECT(Flow.Advance(S));
    EXPECT(Flow.Current(S)->Id == "end"); // terminal step never auto-completes
    EXPECT(!Flow.Advance(S));
}

void TestObjectiveFlowOutOfOrderDoesNotSoftlock()
{
    // Player grabs the card before the game registered the lobby checkpoint (e.g. sprinting past).
    ObjectiveFlow Flow;
    Flow.SetSteps({{"enter", "cp_lobby"}, {"card", "has_access_card"}, {"door", "cp_service"}, {"end", ""}});
    ProgressState S;
    S.SetFlag("has_access_card");
    EXPECT(!Flow.Advance(S));           // still waiting on 'enter'
    S.SetFlag("cp_lobby");
    EXPECT(Flow.Advance(S));
    EXPECT(Flow.Current(S)->Id == "door"); // skipped the already-done card step
}

void TestEntranceRejectOnceThenRelease()
{
    DoorLock D(LockMode::RejectOnceThenRelease, 1.4, 1.2);
    EXPECT(D.GetState() == DoorState::Locked);
    EXPECT(D.Use(false) == UseResult::NeedItem);   // no work order: feedback, nothing else
    EXPECT(D.GetState() == DoorState::Locked);
    EXPECT(D.Use(true) == UseResult::Rejected);    // shows previous number 21-46
    EXPECT(D.GetState() == DoorState::Releasing);
    EXPECT(D.Use(true) == UseResult::Busy);        // spamming E does not break the sequence
    bool bReleased = false;
    Run(1.5, 1.0 / 60.0, [&](double Dt) { bReleased = D.Tick(Dt) || bReleased; });
    EXPECT(bReleased);
    EXPECT(D.GetState() == DoorState::Unlocked);
    EXPECT(D.OpenAlpha() > 0.0 && D.OpenAlpha() < 0.2); // visibly ajar after the latch clicks
    EXPECT(D.Use(true) == UseResult::Opening);
    Run(1.3, 1.0 / 60.0, [&](double Dt) { D.Tick(Dt); });
    EXPECT(D.GetState() == DoorState::Open);
    EXPECT(std::fabs(D.OpenAlpha() - 1.0) < 1e-9);
    EXPECT(D.Use(true) == UseResult::AlreadyOpen); // critical-path doors never re-close
}

void TestItemDoorOpeningIsMonotonic()
{
    DoorLock D(LockMode::Item, 0.0, 1.0);
    EXPECT(D.Use(false) == UseResult::NeedItem);
    EXPECT(D.Use(true) == UseResult::Opening);
    double Prev = -1.0;
    bool bMonotonic = true;
    Run(1.2, 1.0 / 30.0, [&](double Dt) {
        D.Tick(Dt);
        bMonotonic = bMonotonic && D.OpenAlpha() >= Prev;
        Prev = D.OpenAlpha();
    });
    EXPECT(bMonotonic);
    EXPECT(D.GetState() == DoorState::Open);
}

void TestDoorRestoreFromCheckpoint()
{
    DoorLock D(LockMode::RejectOnceThenRelease, 1.4, 1.2);
    D.Restore(true, false);
    EXPECT(D.GetState() == DoorState::Unlocked);
    D.Restore(false, false);
    EXPECT(D.GetState() == DoorState::Locked);
    D.Restore(false, true);
    EXPECT(D.GetState() == DoorState::Open);
}

void TestCheckpointSnapshotIsIndependent()
{
    ProgressState Live;
    Live.AddItem("job_order_2147");
    Live.SetFlag("cp_lobby");
    Checkpoint Cp{"Checkpoint_Lobby", Live, {0, 800, 0}, -90.0, true};
    Live.AddItem("access_card_21"); // picked up after the checkpoint
    EXPECT(!Cp.State.HasItem("access_card_21"));
    EXPECT(Cp.State.HasItem("job_order_2147"));
    Live = Cp.State; // respawn
    EXPECT(!Live.HasItem("access_card_21"));
}

void TestAnomalyRequiresSeenThenUnseen()
{
    DisplacementAnomaly A;
    // Never seen: never moves.
    bool bTrig = false;
    Run(5.0, 0.05, [&](double Dt) { bTrig = A.Update(false, Dt) || bTrig; });
    EXPECT(!bTrig);
    // Short glance (0.3 s) then away: still does not count.
    Run(0.3, 0.05, [&](double Dt) { bTrig = A.Update(true, Dt) || bTrig; });
    Run(2.0, 0.05, [&](double Dt) { bTrig = A.Update(false, Dt) || bTrig; });
    EXPECT(!bTrig);
    // While watched for a long time: never moves in view.
    Run(10.0, 0.05, [&](double Dt) { bTrig = A.Update(true, Dt) || bTrig; });
    EXPECT(!bTrig);
    // Look away: triggers exactly once.
    int Count = 0;
    Run(3.0, 0.05, [&](double Dt) { Count += A.Update(false, Dt) ? 1 : 0; });
    Run(3.0, 0.05, [&](double Dt) { Count += A.Update(true, Dt) ? 1 : 0; });
    Run(3.0, 0.05, [&](double Dt) { Count += A.Update(false, Dt) ? 1 : 0; });
    EXPECT(Count == 1);
    EXPECT(A.HasTriggered());
}

void TestValvePuzzleSolveAndSafeRetry()
{
    ValvePuzzle P;
    EXPECT(P.Turn(Valve::Low) == ValveEvent::StepAccepted);
    EXPECT(P.Turn(Valve::Low) == ValveEvent::WrongStepVenting); // wrong: should be High
    EXPECT(P.IsVenting());
    EXPECT(P.Turn(Valve::High) == ValveEvent::Ignored);         // input during venting ignored
    Run(2.6, 0.1, [&](double Dt) { P.Tick(Dt); });
    EXPECT(!P.IsVenting());
    EXPECT(P.Progress() == 0);                                  // reset, no penalty
    EXPECT(P.Turn(Valve::Low) == ValveEvent::StepAccepted);
    EXPECT(P.Turn(Valve::High) == ValveEvent::StepAccepted);
    EXPECT(P.Turn(Valve::Low) == ValveEvent::Solved);
    EXPECT(P.IsSolved());
    EXPECT(P.Turn(Valve::High) == ValveEvent::Ignored);
}

void TestValveHintsEscalateAndGaugeLags()
{
    ValvePuzzle P;
    EXPECT(P.HintLevel() == 0);
    for (int i = 0; i < 2; ++i)
    {
        P.Turn(Valve::High);
        Run(2.6, 0.1, [&](double Dt) { P.Tick(Dt); });
    }
    EXPECT(P.HintLevel() == 1);
    for (int i = 0; i < 2; ++i)
    {
        P.Turn(Valve::High);
        Run(2.6, 0.1, [&](double Dt) { P.Tick(Dt); });
    }
    EXPECT(P.HintLevel() == 2);
    P.Turn(Valve::Low);
    P.Turn(Valve::High);
    P.Tick(0.1);
    EXPECT(P.Gauge() < P.GaugeTarget()); // needle lags the input (non-text cue)
    Run(5.0, 0.05, [&](double Dt) { P.Tick(Dt); });
    EXPECT(std::fabs(P.Gauge() - P.GaugeTarget()) < 0.01);
}

SenseInput Facing(Vec3 Self, Vec3 Fwd, Vec3 Target, bool bLos = true, double Light = 1.0, bool bCrouch = false)
{
    SenseInput In;
    In.SelfLocation = Self;
    In.SelfForward = Fwd;
    In.TargetLocation = Target;
    In.bLineOfSight = bLos;
    In.TargetLight = Light;
    In.bTargetCrouched = bCrouch;
    return In;
}

void TestSightRules()
{
    PatrolBrain B;
    const Vec3 O{0, 0, 0}, F{1, 0, 0};
    EXPECT(B.CanSee(Facing(O, F, {800, 0, 0})));
    EXPECT(!B.CanSee(Facing(O, F, {-800, 0, 0})));               // behind
    EXPECT(!B.CanSee(Facing(O, F, {800, 0, 0}, false)));         // occluded
    EXPECT(!B.CanSee(Facing(O, F, {800, 0, 0}, true, 0.0)));     // dark: range 490 cm
    EXPECT(B.CanSee(Facing(O, F, {400, 0, 0}, true, 0.0)));
    EXPECT(!B.CanSee(Facing(O, F, {1000, 0, 0}, true, 1.0, true))); // crouched: 840 cm
}

void TestHearingThroughDoorIsReduced()
{
    NoiseEvent Step{{600, 0, 0}, 900.0, 1.0};
    EXPECT(PatrolBrain::CanHear({0, 0, 0}, Step));
    Step.Occlusion = 0.3; // closed door
    EXPECT(!PatrolBrain::CanHear({0, 0, 0}, Step));
}

void TestPatrolInvestigatesNoiseButDoesNotChase()
{
    PatrolBrain B;
    B.OnNoise({0, 0, 0}, NoiseEvent{{500, 300, 0}, 1200.0, 1.0});
    EXPECT(B.GetState() == PatrolState::Investigate);
    EXPECT(B.HasGoal());
    // Player hides out of sight: the brain only knows the noise position.
    SenseInput Hidden = Facing({0, 0, 0}, {1, 0, 0}, {-2000, 0, 0}, false);
    B.Tick(Hidden, 0.1);
    EXPECT(B.GetState() == PatrolState::Investigate);
    EXPECT(std::fabs(B.GoalLocation().X - 500) < 1e-9);
    // Arrive -> search -> eventually return to patrol (never omniscient).
    Hidden.SelfLocation = {500, 300, 0};
    B.Tick(Hidden, 0.1);
    EXPECT(B.GetState() == PatrolState::Search);
    Run(10.0, 0.1, [&](double Dt) { B.Tick(Hidden, Dt); });
    EXPECT(B.GetState() == PatrolState::Return);
}

void TestChaseThenLoseTargetSearchesLastKnown()
{
    PatrolBrain B;
    SenseInput See = Facing({0, 0, 0}, {1, 0, 0}, {300, 0, 0});
    Run(2.0, 0.05, [&](double Dt) { B.Tick(See, Dt); });
    EXPECT(B.GetState() == PatrolState::Chase);
    // Player breaks line of sight at x=300 and keeps running to x=2000 unseen.
    SenseInput Lost = Facing({100, 0, 0}, {1, 0, 0}, {2000, 0, 0}, false);
    Run(3.0, 0.05, [&](double Dt) { B.Tick(Lost, Dt); });
    EXPECT(B.GetState() == PatrolState::Search);
    EXPECT(std::fabs(B.LastKnownTarget().X - 300) < 1e-9); // not the true position (2000)
}

void TestSafeRoomEndsChase()
{
    PatrolBrain B;
    SenseInput See = Facing({0, 0, 0}, {1, 0, 0}, {300, 0, 0});
    Run(2.0, 0.05, [&](double Dt) { B.Tick(See, Dt); });
    EXPECT(B.GetState() == PatrolState::Chase);
    See.bTargetInSafeZone = true; // beat sheet: reaching the safe room immediately loses pursuit
    B.Tick(See, 0.05);
    EXPECT(B.GetState() == PatrolState::Search);
    Run(1.0, 0.05, [&](double Dt) { B.Tick(See, Dt); });
    EXPECT(B.GetState() != PatrolState::Chase); // still visible but safe: no re-chase
}

void TestChaseFairness()
{
    ChaseRules R;
    ChaseRequest Q;
    Q.Now = 10.0;
    Q.PlayerEye = {0, 0, 165};
    Q.PlayerForward = {1, 0, 0};
    Q.EnemyStart = {-1500, 0, 165}; // behind the player
    EXPECT(R.Evaluate(Q) == ChaseVerdict::DeniedNoTelegraph); // no audible warning yet
    Q.LastTelegraphTime = 9.5;
    EXPECT(R.Evaluate(Q) == ChaseVerdict::DeniedNoTelegraph); // too short a lead
    Q.LastTelegraphTime = 8.2;
    EXPECT(R.Evaluate(Q) == ChaseVerdict::Allowed);
    Q.EnemyStart = {1200, 100, 165};
    Q.bEnemyStartVisibleToPlayer = true; // would pop into the middle of the screen
    EXPECT(R.Evaluate(Q) == ChaseVerdict::DeniedSpawnInView);
    Q.bEnemyStartVisibleToPlayer = false; // behind a door in front: allowed (heard first)
    EXPECT(R.Evaluate(Q) == ChaseVerdict::Allowed);
}

} // namespace

int main()
{
    const std::vector<TestCase> Tests = {
        {"ObjectiveFlowInOrder", TestObjectiveFlowInOrder},
        {"ObjectiveFlowOutOfOrderDoesNotSoftlock", TestObjectiveFlowOutOfOrderDoesNotSoftlock},
        {"EntranceRejectOnceThenRelease", TestEntranceRejectOnceThenRelease},
        {"ItemDoorOpeningIsMonotonic", TestItemDoorOpeningIsMonotonic},
        {"DoorRestoreFromCheckpoint", TestDoorRestoreFromCheckpoint},
        {"CheckpointSnapshotIsIndependent", TestCheckpointSnapshotIsIndependent},
        {"AnomalyRequiresSeenThenUnseen", TestAnomalyRequiresSeenThenUnseen},
        {"ValvePuzzleSolveAndSafeRetry", TestValvePuzzleSolveAndSafeRetry},
        {"ValveHintsEscalateAndGaugeLags", TestValveHintsEscalateAndGaugeLags},
        {"SightRules", TestSightRules},
        {"HearingThroughDoorIsReduced", TestHearingThroughDoorIsReduced},
        {"PatrolInvestigatesNoiseButDoesNotChase", TestPatrolInvestigatesNoiseButDoesNotChase},
        {"ChaseThenLoseTargetSearchesLastKnown", TestChaseThenLoseTargetSearchesLastKnown},
        {"SafeRoomEndsChase", TestSafeRoomEndsChase},
        {"ChaseFairness", TestChaseFairness},
    };
    for (const TestCase& T : Tests)
    {
        GCurrent = T.Name;
        const int Before = GFailures;
        T.Fn();
        std::printf("%s %s\n", GFailures == Before ? "[ OK ]" : "[FAIL]", T.Name);
    }
    std::printf("%zu tests, %d checks, %d failures\n", Tests.size(), GChecks, GFailures);
    return GFailures == 0 ? 0 : 1;
}
