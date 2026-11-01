#!/usr/bin/env bash
# The Unfinished Confession - build + scripted playtest on Linux/macOS UE 5.8 installs.
# Usage: tools/ue/build_and_playtest.sh /path/to/UE_5.8
set -euo pipefail
UE="${1:?path to UE 5.8 root}"
PROJ="$(cd "$(dirname "$0")/../.." && pwd)/ue58/Confession.uproject"
case "$(uname)" in Darwin) PLAT=Mac; BIN="$UE/Engine/Binaries/Mac";; *) PLAT=Linux; BIN="$UE/Engine/Binaries/Linux";; esac
"$UE/Engine/Build/BatchFiles/RunUBT.sh" ConfessionEditor "$PLAT" Development -Project="$PROJ" -WaitMutex || { echo "BUILD FAILED"; exit 2; }
"$BIN/UnrealEditor-Cmd" "$PROJ" -ExecCmds="Automation RunTests Confession; Quit" -unattended -nullrhi -nosplash || { echo "AUTOMATION FAILED"; exit 3; }
"$BIN/UnrealEditor" "$PROJ" -game -windowed -ResX=1600 -ResY=900 -ConfessionAutoPlaytest -ConfessionAutoQuit || { echo "PLAYTEST FAILED"; exit 4; }
echo "PASS - evidence in ue58/Saved/Confession/Evidence"
