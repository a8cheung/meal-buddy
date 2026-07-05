from fastapi import APIRouter, Depends, Query
from app.models.schemas import (
    CommentPayload,
    HistoryResponse,
    RatingPayload,
    SuggestMealsRequest,
    SuggestMealsResponse,
    SuggestSupplementsRequest,
    SuggestSupplementsResponse,
)
from app.services.meal_service import MealService
from app.services.storage_factory import build_storage_service

router = APIRouter(prefix="/api", tags=["meals"])
meal_service = MealService(storage_service=build_storage_service())


@router.get("/health", response_model=dict)
def health_check():
    return {"status": "ok", "message": "Meal API is running"}


@router.post("/suggest-meals", response_model=SuggestMealsResponse)
def suggest_meals(request: SuggestMealsRequest, user_id: str = Query(default="default")):
    return meal_service.suggest_meals(request, user_id=user_id)


@router.get("/history", response_model=HistoryResponse)
def get_history(user_id: str = Query(default="default")):
    entries = meal_service.storage_service.get_history(user_id=user_id)
    return {"history": entries}


@router.post("/history/rate")
def rate_meal(payload: RatingPayload):
    updated = meal_service.storage_service.update_rating(payload)
    if updated is None:
        return {"ok": False, "message": "Meal not found"}
    return {"ok": True, "entry": updated}


@router.post("/history/comment")
def comment_on_meal(payload: CommentPayload):
    updated = meal_service.storage_service.update_comment(payload)
    if updated is None:
        return {"ok": False, "message": "Meal not found"}
    return {"ok": True, "entry": updated}


@router.post("/suggest-supplements", response_model=SuggestSupplementsResponse)
def suggest_supplements(request: SuggestSupplementsRequest):
    return meal_service.suggest_supplements(request)
