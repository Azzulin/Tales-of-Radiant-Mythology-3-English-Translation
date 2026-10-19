@echo off
setlocal EnableDelayedExpansion
rem ==========================================================================
rem  Tales of the World: Radiant Mythology 3 - English patch
rem  Applies the .xdelta in this folder to YOUR copy of the Japanese ISO.
rem  Usage: drag the original .iso onto this file, or double-click it and
rem  type/paste the path when asked. Nothing is changed in the original ISO.
rem ==========================================================================
cd /d "%~dp0"
set "ORIG_MD5=5d63d1652b851e005d27fe42db7d6241"

set "XD="
if exist "%~dp0xdelta3.exe" set "XD=%~dp0xdelta3.exe"
if not defined XD for /f "delims=" %%x in ('where xdelta3 2^>nul') do if not defined XD set "XD=%%x"
if not defined XD (
  echo xdelta3.exe was not found next to this script.
  echo Download it from https://github.com/jmacd/xdelta-gpl/releases
  echo and put it in this folder, named xdelta3.exe.
  goto :fim
)

set "PATCH="
for %%f in (*.xdelta) do if not defined PATCH set "PATCH=%%f"
if not defined PATCH (
  echo No .xdelta file found in this folder.
  echo Download it from the Releases page and put it next to this script.
  goto :fim
)

set "ORIG=%~1"
if not defined ORIG set /p "ORIG=Drag your ORIGINAL Japanese ISO here and press Enter: "
set "ORIG=%ORIG:"=%"
if not exist "%ORIG%" (
  echo File not found: "%ORIG%"
  goto :fim
)

set "OUT=%~dp0%PATCH:.xdelta=.iso%"
if exist "%OUT%" (
  echo "%OUT%" already exists. Delete or rename it first.
  goto :fim
)

echo Checking your ISO (MD5), this takes a few seconds...
set "H="
for /f "skip=1 delims=" %%h in ('certutil -hashfile "%ORIG%" MD5') do if not defined H set "H=%%h"
set "H=!H: =!"
if /i not "!H!"=="%ORIG_MD5%" (
  echo.
  echo  Your ISO's MD5 is  !H!
  echo  The patch needs    %ORIG_MD5%
  echo  This is not the original Japanese dump ^(NPJH50353^), or it was modified.
  echo  The patch would fail. Use a clean dump of the game.
  goto :fim
)
echo OK, original ISO recognized.

echo Applying %PATCH% ...
"%XD%" -d -s "%ORIG%" "%~dp0%PATCH%" "%OUT%"
if errorlevel 1 (
  echo.
  echo xdelta3 reported an error. The patched ISO was not created correctly.
  if exist "%OUT%" del "%OUT%"
  goto :fim
)
echo.
echo Done: "%OUT%"
echo Play it on PPSSPP or a PSP/Vita with custom firmware.
echo Do NOT use the in-game Data Install.

:fim
echo.
pause
