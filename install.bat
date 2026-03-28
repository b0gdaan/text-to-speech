@echo off
chcp 65001 >nul
echo =====================================================
echo   Business English TTS — Установка  (D:\said)
echo =====================================================
echo.

echo Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  !! Python не найден !!
    echo  Скачай с https://www.python.org/downloads/
    echo  При установке отметь "Add Python to PATH"
    pause
    exit /b 1
)
python --version

echo.
echo Установка зависимостей...
python -m pip install customtkinter edge-tts pygame-ce imageio-ffmpeg
if errorlevel 1 ( echo ОШИБКА & pause & exit /b 1 )

echo.
echo =====================================================
echo  Готово! Запуск: run.bat
echo =====================================================
pause
