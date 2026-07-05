from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SuggestMealsRequest(BaseModel):
    ingredients: List[str] = Field(..., min_length=1)
    cuisine: Optional[str] = None
    servings: int = Field(default=2, ge=1, le=12)
    leftovers: bool = False
    include_history_context: bool = True


class MealOption(BaseModel):
    id: str
    name: str
    description: str
    ingredients: List[str]
    instructions: List[str]
    cuisine: Optional[str] = None
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    difficulty: Optional[str] = None
    cookware: Optional[List[str]] = None
    nutrition: Optional[Dict[str, Any]] = None
    light_option: Optional[Dict[str, Any]] = None


class SuggestMealsResponse(BaseModel):
    meals: List[MealOption]
    source: str = "local-fallback"
    note: Optional[str] = None


class SaveHistoryItem(BaseModel):
    meal: MealOption
    user_id: Optional[str] = "default"
    source: str = "generated"


class HistoryEntry(BaseModel):
    id: str
    meal: MealOption
    user_id: str
    created_at: str
    rating: Optional[int] = None
    comment: Optional[str] = None


class HistoryResponse(BaseModel):
    history: List[HistoryEntry]


class RatingPayload(BaseModel):
    meal_id: str
    rating: int = Field(..., ge=1, le=5)
    user_id: Optional[str] = "default"


class CommentPayload(BaseModel):
    meal_id: str
    comment: str = Field(..., min_length=1)
    user_id: Optional[str] = "default"


class HealthResponse(BaseModel):
    status: str
    message: str


class SuggestSupplementsRequest(BaseModel):
    meal_name: str
    ingredients: List[str] = Field(default_factory=list)
    missing_food_groups: List[str] = Field(..., min_length=1)


class SuggestSupplementsResponse(BaseModel):
    supplements: List[str]
    source: str = "local-fallback"
