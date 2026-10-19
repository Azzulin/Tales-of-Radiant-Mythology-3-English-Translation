@echo off
setlocal
rem ==========================================================================
rem  For translators: creates an .xdelta patch from YOUR build and checks it.
rem  Usage: make-patch.bat original.iso my-build.iso my-patch.xdelta
rem ==========================================================================
if "%~3"=="" (
  echo Usage: make-patch.bat ^<original.iso^> ^<my-build.iso^> ^<my-patch.xdelta^>
  exit /b 1
)
set "XD=%~dp0xdelta3.exe"
if not exist "%XD%" set "XD=xdelta3"
if exist "%~3" (
  echo "%~3" already exists. Choose another name.
  exit /b 1
)
echo Creating patch (1 GB source window, so it stays small)...
"%XD%" -e -9 -S djw -B 1073741824 -s "%~1" "%~2" "%~3" || exit /b 1
echo Checking: applying the patch to the original again...
"%XD%" -d -f -s "%~1" "%~3" "%~3.check.iso" || exit /b 1
set "A=" & set "B="
for /f "skip=1 delims=" %%h in ('certutil -hashfile "%~2" MD5') do if not defined A set "A=%%h"
for /f "skip=1 delims=" %%h in ('certutil -hashfile "%~3.check.iso" MD5') do if not defined B set "B=%%h"
del "%~3.check.iso"
if /i not "%A%"=="%B%" (
  echo FAILED: the patch does not reproduce your build. Do not share it.
  exit /b 1
)
echo OK: the patch reproduces your build exactly.
echo Share "%~3" together with these MD5s:
for /f "skip=1 delims=" %%h in ('certutil -hashfile "%~1" MD5') do (echo   original : %%h & goto :o)
:o
echo   patched  : %A%
