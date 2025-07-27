#!/bin/bash

set -e

# Directory where the script resides
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME="$(cd "$DIR" && cd .. && pwd)"

VENV_DIR="$HOME/.venv"
REQUIREMENTS_FILE="$HOME/requirements.txt"
BASE_REQUIREMENTS_FILE="$DIR/base_requirements.txt"

echo "🧪 Checking for Python 3..."
if ! command -v python3 &> /dev/null; then
  echo "❌ Python 3 is not installed or not in PATH."
  exit 1
fi
echo "✅ Python version: $(python3 --version)"

echo "📦 Creating virtual environment in $VENV_DIR..."
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
  echo "✅ Virtual environment created."
fi

echo "🔁 Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "📥 Installing 'uv' package in virtual environment..."
pip install --upgrade pip
pip install uv

echo "✅ uv version: $(uv --version)"

# Install base requirements first if present
if [ -f "$BASE_REQUIREMENTS_FILE" ]; then
  echo "📚 Installing base dependencies from $BASE_REQUIREMENTS_FILE..."
  uv pip install -r "$BASE_REQUIREMENTS_FILE"
else
  echo "⚠️ $BASE_REQUIREMENTS_FILE not found. Skipping base dependency installation."
fi

# Then install main requirements
echo "📚 Installing dependencies from $REQUIREMENTS_FILE..."
if [ -f "$REQUIREMENTS_FILE" ]; then
  uv pip install -r "$REQUIREMENTS_FILE"
else
  echo "⚠️ $REQUIREMENTS_FILE not found. Skipping dependency installation."
fi

echo "✅ Setup complete. To activate your environment later:"
echo "    source $VENV_DIR/bin/activate"
