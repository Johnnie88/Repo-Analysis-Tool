@echo off
rem Repository Intelligence CLI Tool
rem Copyright (c) 2024 Repository Intelligence Team
rem
rem Permission is hereby granted, free of charge, to any person obtaining a copy
rem of this software and associated documentation files (the "Software"), to deal
rem in the Software without restriction, including without limitation the rights
rem to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
rem copies of the Software, and to permit persons to whom the Software is
rem furnished to do so, subject to the following conditions:
rem
rem The above copyright notice and this permission notice shall be included in all
rem copies or substantial portions of the Software.
rem
rem THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
rem IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
rem FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
rem AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
rem LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
rem OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
rem SOFTWARE.
rem ==============================================================================
rem Repository Intelligence Runner - easy launcher for the analyzer / TUI / backend
rem
rem Usage:
rem   run                         Interactive analyzer (prompts for input)
rem   run -i .\my-project --mode full
rem   run tui                     Launch the Textual TUI
rem   run backend <args...>       Run the TUI backend API helpers
rem   run help                    Show this help
rem ==============================================================================

setlocal
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

set "PYTHON_BIN="
if exist "%PROJECT_ROOT%venv\Scripts\python.exe" set "PYTHON_BIN=%PROJECT_ROOT%venv\Scripts\python.exe"
if "%PYTHON_BIN%"=="" set "PYTHON_BIN=python"

if defined PYTHONPATH (
    set "PYTHONPATH=%PROJECT_ROOT%src;%PYTHONPATH%"
) else (
    set "PYTHONPATH=%PROJECT_ROOT%src"
)

set "CMD=%~1"

if "%CMD%"=="" (
    "%PYTHON_BIN%" -m repo_analysis.analyzer
    goto :eof
)

if /i "%CMD%"=="help" goto :usage

if /i "%CMD%"=="tui" (
    "%PYTHON_BIN%" -m repo_analysis.tui %2 %3 %4 %5 %6 %7 %8 %9
    goto :eof
)

if /i "%CMD%"=="backend" (
    "%PYTHON_BIN%" -m repo_analysis.tui_backend %2 %3 %4 %5 %6 %7 %8 %9
    goto :eof
)

if /i "%CMD%"=="analyzer" (
    "%PYTHON_BIN%" -m repo_analysis.analyzer %2 %3 %4 %5 %6 %7 %8 %9
    goto :eof
)

"%PYTHON_BIN%" -m repo_analysis.analyzer %*
goto :eof

:usage
echo Usage:
echo   run [analyzer options...]   Run the CLI analyzer (interactive if no args)
echo   run tui                     Launch the Textual TUI
echo   run backend ^<args^>        Run the TUI backend API helpers
echo   run help                    Show this help
echo.
echo Examples:
echo   run -i .\my-project --mode full
echo   run -i https://github.com/user/repo.git
echo   run tui
:eof
endlocal
