@echo off
python "%~dp0src\cli.py" %*
exit /b %ERRORLEVEL%
