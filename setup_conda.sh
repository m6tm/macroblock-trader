#!/bin/bash
# Setup script pour MacroBlock Trader (Conda)
# Compatible : Linux, macOS, Windows (WSL)
# NON compatible : Termux (Android)

set -e

echo "=========================================="
echo "  MacroBlock Trader — Setup (Conda)"
echo "=========================================="

ENV_NAME=${ENV_NAME:-macroblock}

# Check conda/micromamba
if command -v micromamba &> /dev/null; then
    CMD="micromamba"
    ACTIVATE="micromamba activate $ENV_NAME"
elif command -v mamba &> /dev/null; then
    CMD="mamba"
    ACTIVATE="conda activate $ENV_NAME"
elif command -v conda &> /dev/null; then
    CMD="conda"
    ACTIVATE="conda activate $ENV_NAME"
else
    echo "ERREUR : ni conda, ni mamba, ni micromamba trouves."
    echo "Installez Miniconda : https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

echo "→ Utilisation de : $CMD"

# Create env from environment.yml
echo "→ Creation de l'environnement '$ENV_NAME'..."
$CMD env create -f environment.yml -n $ENV_NAME

echo ""
echo "=========================================="
echo "  Installation terminee !"
echo "=========================================="
echo ""
echo "Activation :"
echo "  $ACTIVATE"
echo ""
echo "Installation editable (a faire une fois active) :"
echo "  pip install -e \".[dev]\""
echo ""
echo "Lancement :"
echo "  python src/main.py"
echo ""
