@echo off
chcp 65001 >nul
echo Упаковка EXE-версии в ZIP...

powershell -Command "Compress-Archive -Path 'D:\said\dist\BusinessEnglishTTS' -DestinationPath 'D:\said\BusinessEnglishTTS.zip' -Force"

echo.
echo Готово: D:\said\BusinessEnglishTTS.zip
echo Размер:
powershell -Command "(Get-Item 'D:\said\BusinessEnglishTTS.zip').length / 1MB | ForEach-Object { [math]::Round($_,1).ToString() + ' MB' }"
pause
