// The Unfinished Confession - engine-independent gameplay rules.
//
// Everything in this header is plain C++20 with no Unreal includes, so the same code is
//   (a) compiled into the Confession UE module and driven by Actors, and
//   (b) compiled and unit-tested outside the engine (tests/core, CMake + g++/clang).
// Rules that decide fairness (locks, checkpoints, anomaly timing, puzzle reset, enemy senses,
// chase telegraphs) live here so they can be verified without an editor.
//
// Constraints so it builds inside UE: no exceptions, no RTTI, no identifiers that collide with
// UE macros (check/verify/ensure/PI/TEXT).
#pragma once

#include <cstdint>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace ConfessionRules
{

struct Vec3
{
    double X = 0.0, Y = 0.0, Z = 0.0;
};
Vec3 operator-(const Vec3& A, const Vec3& B);
Vec3 operator+(const Vec3& A, const Vec3& B);
Vec3 operator*(const Vec3& A, double S);
double Dot(const Vec3& A, const Vec3& B);
double Length(const Vec3& A);
Vec3 Normalized(const Vec3& A);

// ------------------------------------------------------------------ progress / checkpoint
struct ProgressState
{
    std::set<std::string> Items;
    std::set<std::string> Flags;
    int ObjectiveIndex = 0;

    bool HasItem(const std::string& Id) const { return Items.count(Id) != 0; }
    bool HasFlag(const std::string& Id) const { return !Id.empty() && Flags.count(Id) != 0; }
    void AddItem(const std::string& Id) { if (!Id.empty()) Items.insert(Id); }
    void SetFlag(const std::string& Id) { if (!Id.empty()) Flags.insert(Id); }
};

struct Checkpoint
{
    std::string Id;
    ProgressState State;
    Vec3 Location;
    double YawDeg = 0.0;
    bool bValid = false;
};

// ------------------------------------------------------------------ objectives
struct ObjectiveStep
{
    std::string Id;
    std::string CompleteOnFlag; // empty = terminal step
};

class ObjectiveFlow
{
public:
    void SetSteps(std::vector<ObjectiveStep> InSteps) { Steps = std::move(InSteps); }
    // Advances State.ObjectiveIndex past every step whose flag is already set.
    // Steps can therefore be completed out of order (e.g. picking up the card before the
    // checkpoint) without soft-locking the objective line. Returns true if the index changed.
    bool Advance(ProgressState& State) const;
    const ObjectiveStep* Current(const ProgressState& State) const;
    int Num() const { return static_cast<int>(Steps.size()); }

private:
    std::vector<ObjectiveStep> Steps;
};

// ------------------------------------------------------------------ doors / locks
enum class LockMode : uint8_t { None, Item, RejectOnceThenRelease };
enum class DoorState : uint8_t { Locked, Releasing, Unlocked, Opening, Open };
enum class UseResult : uint8_t { NeedItem, Rejected, Busy, Opening, AlreadyOpen };

class DoorLock
{
public:
    DoorLock() = default;
    DoorLock(LockMode InMode, double InReleaseDelay, double InOpenDuration);

    UseResult Use(bool bHasRequiredItem);
    // Returns true on the tick the latch releases (Releasing -> Unlocked).
    bool Tick(double DeltaSeconds);
    DoorState GetState() const { return State; }
    // 0 = closed, 1 = fully open; a released-but-unpushed door rests ajar so the change is visible.
    double OpenAlpha() const;
    // Restores a persisted state; transient states collapse to their stable neighbour.
    void Restore(bool bWasReleased, bool bWasOpen);
    bool IsReleased() const { return State != DoorState::Locked && State != DoorState::Releasing; }

    static constexpr double AjarAlpha = 0.12;

private:
    LockMode Mode = LockMode::None;
    DoorState State = DoorState::Unlocked;
    double ReleaseDelay = 1.4;
    double OpenDuration = 1.2;
    double Timer = 0.0;
};

// ------------------------------------------------------------------ "moves only when unobserved" anomaly
// DIRECTOR_BEAT_SHEET key moment 01: the empty frame shifts 8 cm once, only after the player has
// actually looked at it and then looked away. Never in view, never twice.
class DisplacementAnomaly
{
public:
    double MinSeenSeconds = 0.6;    // must be looked at this long first
    double MinUnseenSeconds = 0.35; // then out of view this long
    // bInView: inside camera cone + line of sight + within range. Returns true on the trigger tick.
    bool Update(bool bInView, double DeltaSeconds);
    bool HasTriggered() const { return bTriggered; }
    void Restore(bool bWasTriggered) { bTriggered = bWasTriggered; SeenTime = UnseenTime = 0.0; }

private:
    double SeenTime = 0.0;
    double UnseenTime = 0.0;
    bool bTriggered = false;
};

// ------------------------------------------------------------------ twin pressure valve puzzle (VS04 / L0_B04)
// Canon: low -> high -> low. The gauge lags the input; a wrong step vents automatically and resets
// with no penalty. Two non-text hints escalate after failures (sound cue, then worn legend lamp).
enum class Valve : uint8_t { Low, High };
enum class ValveEvent : uint8_t { None, StepAccepted, WrongStepVenting, Ignored, Solved };

class ValvePuzzle
{
public:
    std::vector<Valve> Solution{Valve::Low, Valve::High, Valve::Low};
    double VentSeconds = 2.5;
    double GaugeTimeConstant = 0.8; // seconds; gauge needle lag

    ValveEvent Turn(Valve V);
    void Tick(double DeltaSeconds);
    bool IsSolved() const { return bSolved; }
    bool IsVenting() const { return VentTimer > 0.0; }
    int Progress() const { return Step; }
    int Failures() const { return FailCount; }
    // 0 none, 1 = pressure-sound cue on the correct valve, 2 = legend lamp lit.
    int HintLevel() const { return FailCount >= 4 ? 2 : (FailCount >= 2 ? 1 : 0); }
    double GaugeTarget() const;
    double Gauge() const { return GaugeValue; }

private:
    int Step = 0;
    int FailCount = 0;
    bool bSolved = false;
    double VentTimer = 0.0;
    double GaugeValue = 0.0;
};

// ------------------------------------------------------------------ patrol senses (VS05 / LI_B07)
// The Inspector is not omniscient: it only learns the player's position when it hears or sees them,
// is stopped by doors (handled by navigation) and searches the last known position.
enum class PatrolState : uint8_t { Patrol, Suspicious, Investigate, Chase, Search, Return };

struct PerceptionConfig
{
    double SightRange = 1400.0;      // cm, in full light, standing
    double SightHalfAngleDeg = 50.0;
    double DarkSightScale = 0.35;    // range multiplier at light level 0
    double CrouchSightScale = 0.6;
    double AwarenessGainPerSec = 1.6; // at point blank; falls off linearly with distance
    double AwarenessDecayPerSec = 0.35;
    double SuspiciousThreshold = 0.35;
    double ChaseThreshold = 1.0;
    double LoseSightSeconds = 2.5;   // chase -> search
    double SearchSeconds = 9.0;      // search -> return
    double InvestigateArriveRadius = 120.0;
};

struct SenseInput
{
    Vec3 SelfLocation;
    Vec3 SelfForward{1, 0, 0};
    Vec3 TargetLocation;
    bool bLineOfSight = false;
    double TargetLight = 1.0;  // 0..1 from engine light sampling
    bool bTargetCrouched = false;
    bool bTargetInSafeZone = false;
};

struct NoiseEvent
{
    Vec3 Location;
    double Radius = 0.0;      // cm audible radius at the source
    double Occlusion = 1.0;   // 1 = open air, 0.3 = through a closed door
};

class PatrolBrain
{
public:
    PerceptionConfig Config;

    bool CanSee(const SenseInput& In) const;
    static bool CanHear(const Vec3& Listener, const NoiseEvent& Noise);
    void OnNoise(const Vec3& Listener, const NoiseEvent& Noise);
    void Tick(const SenseInput& In, double DeltaSeconds);
    void ArrivedAtGoal(); // navigation reports arrival at GoalLocation()

    PatrolState GetState() const { return State; }
    double Awareness() const { return AwarenessValue; }
    bool HasGoal() const { return bHasGoal; }
    Vec3 GoalLocation() const { return Goal; }
    Vec3 LastKnownTarget() const { return LastKnown; }

private:
    void Enter(PatrolState S);
    PatrolState State = PatrolState::Patrol;
    double AwarenessValue = 0.0;
    double StateTimer = 0.0;
    double SinceSeen = 0.0;
    bool bHasGoal = false;
    Vec3 Goal;
    Vec3 LastKnown;
};

// ------------------------------------------------------------------ chase fairness (VS06 / LI_B08)
// A chase may only start if an audible telegraph played at least MinLeadSeconds before, and the
// enemy is not placed inside the player's view cone (no teleporting into the middle of the screen).
struct ChaseRequest
{
    double Now = 0.0;
    double LastTelegraphTime = -1e9;
    Vec3 PlayerEye;
    Vec3 PlayerForward{1, 0, 0};
    Vec3 EnemyStart;
    bool bEnemyStartVisibleToPlayer = false; // engine LOS test
};

enum class ChaseVerdict : uint8_t { Allowed, DeniedNoTelegraph, DeniedSpawnInView };

struct ChaseRules
{
    double MinLeadSeconds = 1.0;
    double MaxLeadSeconds = 8.0;     // telegraph too old -> must repeat
    double ViewHalfAngleDeg = 55.0;
    ChaseVerdict Evaluate(const ChaseRequest& R) const;
};

const char* ToString(PatrolState S);
const char* ToString(DoorState S);

} // namespace ConfessionRules
