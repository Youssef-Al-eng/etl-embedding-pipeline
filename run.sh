#!/usr/bin/env bash
# ─── Embedding Pipeline Runner ────────────────────────────────────────────────
# Usage:
#   ./run.sh               → demo mode (no API key needed)
#   ./run.sh --live        → real OpenAI API (reads OPENAI_API_KEY from env)

set -e

echo ""
echo "  ⚡ Embedding Pipeline Setup"
echo "  ─────────────────────────────"

# Install deps silently
echo "  📦 Checking dependencies..."
pip install -q -r requirements.txt

# Generate sample data if data/ is empty
if [ -z "$(ls -A data/*.csv 2>/dev/null)" ]; then
  echo "  📄 Generating sample CSV data..."
  python generate_sample_data.py
fi

echo ""

# Run pipeline
if [ "$1" == "--live" ]; then
  if [ -z "$OPENAI_API_KEY" ]; then
    echo "  ❌ OPENAI_API_KEY not set. Export it first:"
    echo "     export OPENAI_API_KEY=sk-..."
    exit 1
  fi
  echo "  🔑 Using live OpenAI API"
  python pipeline.py
else
  echo "  🎭 Running in DEMO MODE (set OPENAI_API_KEY + pass --live for real embeddings)"
  python pipeline.py
fi
