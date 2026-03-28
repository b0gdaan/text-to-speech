@echo off
chcp 65001 >nul
echo =====================================================
echo   Business English TTS — Сборка EXE
echo =====================================================
echo.

echo Установка PyInstaller...
python -m pip install pyinstaller -q

echo.
echo Сборка EXE (займет 1-3 минуты)...
python -m PyInstaller ^
  --noconfirm ^
  --onedir ^
  --windowed ^
  --name "BusinessEnglishTTS" ^
  --icon NONE ^
  --add-data "dialogues;dialogues" ^
  --collect-all customtkinter ^
  --collect-all edge_tts ^
  --collect-all imageio_ffmpeg ^
  --collect-all pygame ^
  --hidden-import customtkinter ^
  --hidden-import edge_tts ^
  --hidden-import imageio_ffmpeg ^
  --hidden-import pygame ^
  --hidden-import asyncio ^
  main.py

if errorlevel 1 (
    echo.
    echo ОШИБКА при сборке!
    pause
    exit /b 1
)

echo.
echo =====================================================
echo  ГОТОВО!
echo  Папка с EXE: dist\BusinessEnglishTTS\
echo  Отправь получателю всю эту папку (ZIP-ом)
echo =====================================================
echo.
echo Открыть папку?
pause
explorer dist\BusinessEnglishTTS
