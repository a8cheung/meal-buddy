import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from app.config import DATA_DIR
from app.models.schemas import HistoryEntry, MealOption, RatingPayload, CommentPayload


class StorageService:
    def __init__(self):
        self.history_path = DATA_DIR / "history.json"
        self.history_path.touch(exist_ok=True)
        self._ensure_history_file()

    def _ensure_history_file(self) -> None:
        if self.history_path.stat().st_size == 0:
            self.history_path.write_text("[]", encoding="utf-8")

    def _load_history(self) -> List[Dict]:
        with self.history_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def _save_history(self, entries: List[Dict]) -> None:
        with self.history_path.open("w", encoding="utf-8") as fh:
            json.dump(entries, fh, indent=2)

    def get_history(self, user_id: str = "default") -> List[HistoryEntry]:
        entries = self._load_history()
        user_entries = [entry for entry in entries if entry.get("user_id") == user_id]
        return [HistoryEntry(**entry) for entry in user_entries]

    def save_history_entry(self, meal: MealOption, user_id: str = "default") -> HistoryEntry:
        entries = self._load_history()
        entry = {
            "id": meal.id,
            "meal": meal.model_dump(),
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "rating": None,
            "comment": None,
        }
        entries.append(entry)
        self._save_history(entries)
        return HistoryEntry(**entry)

    def update_rating(self, payload: RatingPayload) -> Optional[HistoryEntry]:
        entries = self._load_history()
        for entry in entries:
            if entry.get("id") == payload.meal_id and entry.get("user_id") == (payload.user_id or "default"):
                entry["rating"] = payload.rating
                self._save_history(entries)
                return HistoryEntry(**entry)
        return None

    def update_comment(self, payload: CommentPayload) -> Optional[HistoryEntry]:
        entries = self._load_history()
        for entry in entries:
            if entry.get("id") == payload.meal_id and entry.get("user_id") == (payload.user_id or "default"):
                entry["comment"] = payload.comment
                self._save_history(entries)
                return HistoryEntry(**entry)
        return None
