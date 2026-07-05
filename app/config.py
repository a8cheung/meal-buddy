import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
ANTHROPIC_MAX_TOKENS = int(os.getenv("ANTHROPIC_MAX_TOKENS", "2048"))

# Storage backend for meal history: "local" (JSON file, default) or "dynamodb".
# If "dynamodb" is requested but the table/credentials aren't reachable at startup,
# the app logs a warning and falls back to local JSON storage rather than failing to start.
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "meal-suggester-history")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
