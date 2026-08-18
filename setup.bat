@echo off
REM Script de configuracion para Windows

echo Creando entorno virtual...
python -m venv .venv

echo Activando entorno virtual...
call .venv\Scripts\activate.bat

echo Instalando dependencias...
pip install -r requirements.txt

echo.
echo Listo. Para iniciar el proyecto:
echo   .venv\Scripts\activate
echo   python main.py
