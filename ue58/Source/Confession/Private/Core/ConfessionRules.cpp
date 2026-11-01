// The Unfinished Confession - engine-independent gameplay rules (see header).
#include "Core/ConfessionRules.h"

#include <algorithm>
#include <cmath>

namespace ConfessionRules
{

namespace
{
constexpr double DegToRad = 3.14159265358979323846 / 180.0;
}

Vec3 operator-(const Vec3& A, const Vec3& B) { return {A.X - B.X, A.Y - B.Y, A.Z - B.Z}; }
Vec3 operator+(const Vec3& A, const Vec3& B) { return {A.X + B.X, A.Y + B.Y, A.Z + B.Z}; }
Vec3 operator*(const Vec3& A, double S) { return {A.X * S, A.Y * S, A.Z * S}; }
double Dot(const Vec3& A, const Vec3& B) { return A.X * B.X + A.Y * B.Y + A.Z * B.Z; }
double Length(const Vec3& A) { return std::sqrt(Dot(A, A)); }
Vec3 Normalized(const Vec3& A)
{
    const double L = Length(A);
    return L > 1e-9 ? A * (1.0 / L) : Vec3{};
}

// ------------------------------------------------------------------ objectives
bool ObjectiveFlow::Advance(ProgressState& State) const
{
    const int Before = State.ObjectiveIndex;
    while (State.ObjectiveIndex < Num())
    {
        const ObjectiveStep& Step = Steps[static_cast<size_t>(State.ObjectiveIndex)];
        if (Step.CompleteOnFlag.empty() || !State.HasFlag(Step.CompleteOnFlag))
        {
            break;
        }
        ++State.ObjectiveIndex;
    }
    return State.ObjectiveIndex != Before;
}

const ObjectiveStep* ObjectiveFlow::Current(const ProgressState& State) const
{
    if (State.ObjectiveIndex < 0 || State.ObjectiveIndex >= Num())
    {
        return nullptr;
    }
    return &Steps[static_cast<size_t>(State.ObjectiveIndex)];
}

// ------------------------------------------------------------------ doors
DoorLock::DoorLock(LockMode InMode, double InReleaseDelay, double InOpenDuration)
    : Mode(InMode), ReleaseDelay(InReleaseDelay), OpenDuration(std::max(0.05, InOpenDuration))
{
    State = (Mode == LockMode::None) ? DoorState::Unlocked : DoorState::Locked;
}

UseResult DoorLock::Use(bool bHasRequiredItem)
{
    switch (State)
    {
    case DoorState::Locked:
        if (!bHasRequiredItem)
        {
            return UseResult::NeedItem;
        }
        if (Mode == LockMode::RejectOnceThenRelease)
        {
            // Canon: the reader re-shows the previous number, then the latch loosens by itself.
            State = DoorState::Releasing;
            Timer = 0.0;
            return UseResult::Rejected;
        }
        State = DoorState::Opening;
        Timer = 0.0;
        return UseResult::Opening;
    case DoorState::Releasing:
        return UseResult::Busy;
    case DoorState::Unlocked:
        State = DoorState::Opening;
        Timer = 0.0;
        return UseResult::Opening;
    case DoorState::Opening:
        return UseResult::Busy;
    case DoorState::Open:
        // Doors on the critical path never close again: closing them is a soft-lock risk with no
        // gameplay value in this slice.
        return UseResult::AlreadyOpen;
    }
    return UseResult::Busy;
}

bool DoorLock::Tick(double DeltaSeconds)
{
    if (State == DoorState::Releasing)
    {
        Timer += DeltaSeconds;
        if (Timer >= ReleaseDelay)
        {
            State = DoorState::Unlocked;
            Timer = 0.0;
            return true;
        }
    }
    else if (State == DoorState::Opening)
    {
        Timer += DeltaSeconds;
        if (Timer >= OpenDuration)
        {
            State = DoorState::Open;
            Timer = 0.0;
        }
    }
    return false;
}

double DoorLock::OpenAlpha() const
{
    switch (State)
    {
    case DoorState::Locked:
    case DoorState::Releasing:
        return 0.0;
    case DoorState::Unlocked:
        return Mode == LockMode::RejectOnceThenRelease ? AjarAlpha : 0.0;
    case DoorState::Opening:
    {
        const double Start = Mode == LockMode::RejectOnceThenRelease ? AjarAlpha : 0.0;
        const double T = std::clamp(Timer / OpenDuration, 0.0, 1.0);
        const double Eased = T * T * (3.0 - 2.0 * T); // smoothstep: heavy door, no snap
        return Start + (1.0 - Start) * Eased;
    }
    case DoorState::Open:
        return 1.0;
    }
    return 0.0;
}

void DoorLock::Restore(bool bWasReleased, bool bWasOpen)
{
    Timer = 0.0;
    if (bWasOpen)
    {
        State = DoorState::Open;
    }
    else if (bWasReleased || Mode == LockMode::None)
    {
        State = DoorState::Unlocked;
    }
    else
    {
        State = DoorState::Locked;
    }
}

// ------------------------------------------------------------------ anomaly
bool DisplacementAnomaly::Update(bool bInView, double DeltaSeconds)
{
    if (bTriggered)
    {
        return false;
    }
    if (bInView)
    {
        SeenTime += DeltaSeconds;
        UnseenTime = 0.0;
        return false;
    }
    if (SeenTime < MinSeenSeconds)
    {
        // A glance shorter than the threshold does not count as having seen it.
        SeenTime = 0.0;
        return false;
    }
    UnseenTime += DeltaSeconds;
    if (UnseenTime >= MinUnseenSeconds)
    {
        bTriggered = true;
        return true;
    }
    return false;
}

// ------------------------------------------------------------------ valve puzzle
ValveEvent ValvePuzzle::Turn(Valve V)
{
    if (bSolved || IsVenting())
    {
        return ValveEvent::Ignored;
    }
    if (Step < static_cast<int>(Solution.size()) && Solution[static_cast<size_t>(Step)] == V)
    {
        ++Step;
        if (Step == static_cast<int>(Solution.size()))
        {
            bSolved = true;
            return ValveEvent::Solved;
        }
        return ValveEvent::StepAccepted;
    }
    ++FailCount;
    VentTimer = VentSeconds;
    return ValveEvent::WrongStepVenting;
}

double ValvePuzzle::GaugeTarget() const
{
    if (IsVenting())
    {
        return 0.0;
    }
    if (bSolved)
    {
        return 0.5;
    }
    // Pressure the player has built so far: low adds a little, high adds more.
    double P = 0.0;
    for (int i = 0; i < Step; ++i)
    {
        P += Solution[static_cast<size_t>(i)] == Valve::High ? 0.45 : 0.2;
    }
    return std::min(P, 1.0);
}

void ValvePuzzle::Tick(double DeltaSeconds)
{
    if (VentTimer > 0.0)
    {
        VentTimer = std::max(0.0, VentTimer - DeltaSeconds);
        if (VentTimer == 0.0)
        {
            Step = 0; // safe retry, no penalty
        }
    }
    const double K = 1.0 - std::exp(-DeltaSeconds / std::max(1e-3, GaugeTimeConstant));
    GaugeValue += (GaugeTarget() - GaugeValue) * K;
}

// ------------------------------------------------------------------ patrol senses
bool PatrolBrain::CanSee(const SenseInput& In) const
{
    if (!In.bLineOfSight)
    {
        return false;
    }
    const Vec3 To = In.TargetLocation - In.SelfLocation;
    const double Dist = Length(To);
    double Range = Config.SightRange;
    const double Light = std::clamp(In.TargetLight, 0.0, 1.0);
    Range *= Config.DarkSightScale + (1.0 - Config.DarkSightScale) * Light;
    if (In.bTargetCrouched)
    {
        Range *= Config.CrouchSightScale;
    }
    if (Dist > Range)
    {
        return false;
    }
    if (Dist < 1e-6)
    {
        return true;
    }
    const double CosAngle = Dot(Normalized(To), Normalized(In.SelfForward));
    return CosAngle >= std::cos(Config.SightHalfAngleDeg * DegToRad);
}

bool PatrolBrain::CanHear(const Vec3& Listener, const NoiseEvent& Noise)
{
    const double Effective = Noise.Radius * std::clamp(Noise.Occlusion, 0.0, 1.0);
    return Length(Noise.Location - Listener) <= Effective;
}

void PatrolBrain::Enter(PatrolState S)
{
    State = S;
    StateTimer = 0.0;
}

void PatrolBrain::OnNoise(const Vec3& Listener, const NoiseEvent& Noise)
{
    if (!CanHear(Listener, Noise))
    {
        return;
    }
    if (State == PatrolState::Chase)
    {
        return; // already chasing; noise does not reveal more than sight does
    }
    // Hearing gives a position, not certainty: investigate it, do not chase.
    LastKnown = Noise.Location;
    Goal = Noise.Location;
    bHasGoal = true;
    AwarenessValue = std::max(AwarenessValue, Config.SuspiciousThreshold);
    Enter(PatrolState::Investigate);
}

void PatrolBrain::ArrivedAtGoal()
{
    bHasGoal = false;
    if (State == PatrolState::Investigate)
    {
        Enter(PatrolState::Search);
    }
    else if (State == PatrolState::Return)
    {
        Enter(PatrolState::Patrol);
    }
}

void PatrolBrain::Tick(const SenseInput& In, double DeltaSeconds)
{
    StateTimer += DeltaSeconds;
    const bool bSees = CanSee(In) && !In.bTargetInSafeZone;

    if (bSees)
    {
        const double Dist = Length(In.TargetLocation - In.SelfLocation);
        const double Falloff = std::clamp(1.0 - Dist / std::max(1.0, Config.SightRange), 0.15, 1.0);
        AwarenessValue = std::min(1.0, AwarenessValue + Config.AwarenessGainPerSec * Falloff * DeltaSeconds);
        LastKnown = In.TargetLocation;
        SinceSeen = 0.0;
    }
    else
    {
        SinceSeen += DeltaSeconds;
        if (State != PatrolState::Chase)
        {
            AwarenessValue = std::max(0.0, AwarenessValue - Config.AwarenessDecayPerSec * DeltaSeconds);
        }
    }

    switch (State)
    {
    case PatrolState::Patrol:
    case PatrolState::Return:
        if (bSees && AwarenessValue >= Config.SuspiciousThreshold)
        {
            Enter(PatrolState::Suspicious);
        }
        break;
    case PatrolState::Suspicious:
        if (AwarenessValue >= Config.ChaseThreshold)
        {
            Enter(PatrolState::Chase);
        }
        else if (!bSees && AwarenessValue < Config.SuspiciousThreshold * 0.5)
        {
            Goal = LastKnown;
            bHasGoal = true;
            Enter(PatrolState::Investigate);
        }
        break;
    case PatrolState::Investigate:
        if (bSees && AwarenessValue >= Config.ChaseThreshold)
        {
            Enter(PatrolState::Chase);
        }
        else if (bSees)
        {
            Goal = LastKnown;
            bHasGoal = true;
        }
        break;
    case PatrolState::Chase:
        if (In.bTargetInSafeZone || SinceSeen >= Config.LoseSightSeconds)
        {
            // Lost them: go to the last place the target was actually perceived.
            Goal = LastKnown;
            bHasGoal = true;
            AwarenessValue = Config.SuspiciousThreshold;
            Enter(PatrolState::Search);
        }
        else
        {
            Goal = LastKnown;
            bHasGoal = true;
        }
        break;
    case PatrolState::Search:
        if (bSees && AwarenessValue >= Config.ChaseThreshold)
        {
            Enter(PatrolState::Chase);
        }
        else if (StateTimer >= Config.SearchSeconds)
        {
            bHasGoal = false;
            AwarenessValue = 0.0;
            Enter(PatrolState::Return);
        }
        break;
    }
    if (bHasGoal && State != PatrolState::Chase &&
        Length(Goal - In.SelfLocation) <= Config.InvestigateArriveRadius)
    {
        ArrivedAtGoal();
    }
}

// ------------------------------------------------------------------ chase fairness
ChaseVerdict ChaseRules::Evaluate(const ChaseRequest& R) const
{
    const double Lead = R.Now - R.LastTelegraphTime;
    if (Lead < MinLeadSeconds || Lead > MaxLeadSeconds)
    {
        return ChaseVerdict::DeniedNoTelegraph;
    }
    if (R.bEnemyStartVisibleToPlayer)
    {
        const Vec3 To = Normalized(R.EnemyStart - R.PlayerEye);
        if (Dot(To, Normalized(R.PlayerForward)) >= std::cos(ViewHalfAngleDeg * DegToRad))
        {
            return ChaseVerdict::DeniedSpawnInView;
        }
    }
    return ChaseVerdict::Allowed;
}

const char* ToString(PatrolState S)
{
    switch (S)
    {
    case PatrolState::Patrol: return "Patrol";
    case PatrolState::Suspicious: return "Suspicious";
    case PatrolState::Investigate: return "Investigate";
    case PatrolState::Chase: return "Chase";
    case PatrolState::Search: return "Search";
    case PatrolState::Return: return "Return";
    }
    return "?";
}

const char* ToString(DoorState S)
{
    switch (S)
    {
    case DoorState::Locked: return "Locked";
    case DoorState::Releasing: return "Releasing";
    case DoorState::Unlocked: return "Unlocked";
    case DoorState::Opening: return "Opening";
    case DoorState::Open: return "Open";
    }
    return "?";
}

} // namespace ConfessionRules
