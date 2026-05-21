#!/bin/bash
# Setup script pour MacroBlock Trader (venv + pip)
# Compatible : Linux, macOS, Termux (Android)

set -e

echo "=========================================="
echo "  MacroBlock Trader — Setup"
echo "=========================================="

# Detect Python
PYTHON=${PYTHON:-python3}
if ! command -v "$PYTHON" &> /dev/null; then
    PYTHON=python
fi

PYTHON_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
echo "Python detecte : $PYTHON_VERSION"

# Create virtualenv
if [ ! -d "venv" ]; then
    echo "→ Creation du virtualenv (venv)..."
    $PYTHON -m venv venv --system-site-packages
fi

# Activate
source venv/bin/activate

# Upgrade pip
echo "→ Mise a jour de pip..."
pip install --upgrade pip

# Install project in editable mode
echo "→ Installation des dependances..."
pip install -e ".[dev]"

echo ""
echo "=========================================="
echo "  Installation terminee !"
echo "=========================================="
echo ""
echo "Activation :"
echo "  source venv/bin/activate"
echo ""
echo "Lancement :"
echo "  python src/main.py"
echo ""
echo "Tests :"
echo "  python tests/test_phase0.py"
echo "  python tests/test_phase1.py"
echo "  python tests/modules/test_technical.py"
echo "  python tests/modules/test_macro.py"
echo "  python tests/modules/test_sentiment.py"
echo "  python tests/modules/test_fusion.py"
echo "  python tests/integration/test_event_bus.py"
echo "  python tests/integration/test_data_pipeline.py"
echo "  python tests/integration/test_modules_pipeline.py"
echo ""
