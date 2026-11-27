@echo off
:: J.A.R.V.I.S. Stable - Arka Plan Başlatıcı
:: Bu dosya J.A.R.V.I.S.'i Pythonw (Headless) modunda başlatır.
:: Öncelikli olarak izole sanal ortamı (.venv), yoksa sistem Python'unu kullanır.

setlocal
cd /d "%~dp0"

echo [STARTUP] J.A.R.V.I.S. sistemi arka planda uyandırılıyor...

if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" "%~dp0.venv\Scripts\pythonw.exe" "launch_jarvis.pyw"
) else (
    start "" pythonw.exe "launch_jarvis.pyw"
)

exit
