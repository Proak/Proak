@echo off
REM The Unfinished Confession - build the UE 5.8 project and run the scripted greybox playtest.
REM Usage: tools\ue\build_and_playtest.bat "C:\Program Files\Epic Games\UE_5.8"
REM Evidence lands in ue58\Saved\Confession\Evidence\<utc>\ (autoplaytest.json + PNG screenshots)
REM and logs in ue58\Saved\Logs\. Exit code 0 = PASS, non-zero = build or playtest FAIL.
setlocal
set UE=%~1
if "%UE%"=="" set UE=C:\Program Files\Epic Games\UE_5.8
set PROJ=%~dp0..\..\ue58\Confession.uproject

echo [1/3] Building ConfessionEditor (Development Win64)...
call "%UE%\Engine\Build\BatchFiles\Build.bat" ConfessionEditor Win64 Development -Project="%PROJ%" -WaitMutex -NoHotReload
if errorlevel 1 ( echo BUILD FAILED - copy the full log above into an issue & exit /b 2 )

echo [2/3] Automation tests (data + rules, no rendering)...
"%UE%\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "%PROJ%" -ExecCmds="Automation RunTests Confession; Quit" -unattended -nullrhi -nosplash -log=ConfessionAutomation.log
if errorlevel 1 ( echo AUTOMATION FAILED & exit /b 3 )

echo [3/3] Scripted playtest in a real rendered game window (bot walks + uses, then quits)...
"%UE%\Engine\Binaries\Win64\UnrealEditor.exe" "%PROJ%" -game -windowed -ResX=1600 -ResY=900 -ConfessionAutoPlaytest -ConfessionAutoQuit -log=ConfessionPlaytest.log
if errorlevel 1 ( echo PLAYTEST FAILED - see Saved\Confession\Evidence & exit /b 4 )
echo PASS - evidence in ue58\Saved\Confession\Evidence
exit /b 0
