#!/bin/bash
# Script de configuracion para Linux/Mac
set -e

echo "Creando entorno virtual..."
python3 -m venv .venv

echo "Activando entorno virtual..."
source .venv/bin/activate

echo "Instalando dependencias..."
pip install -r requirements.txt

echo ""
echo "Listo. Para iniciar el proyecto:"
echo "  source .venv/bin/activate"
echo "  python main.py"
