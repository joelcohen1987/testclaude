@echo off
REM Windows: Double-click this file, or drag files onto it to save them to ReadLater.

if "%~1"=="" (
    echo =========================================
    echo   ReadLater - Drop files here to save
    echo =========================================
    echo.
    set /p INPUT="Paste a URL or file path: "
    readlater add "%INPUT%"
) else (
    :loop
    if "%~1"=="" goto done
    readlater add "%~1"
    shift
    goto loop
)

:done
echo.
echo Done!
pause
