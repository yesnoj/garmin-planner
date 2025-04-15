@echo off
echo Creazione del primo eseguibile...
pyinstaller --onefile --windowed --icon=assets/garmin_planner_icon.ico license_extractor.py
echo Creazione del secondo eseguibile...
pyinstaller --onefile --windowed --icon=assets/garmin_planner_icon.ico license_generator.py
echo Eseguibili creati con successo!
pause