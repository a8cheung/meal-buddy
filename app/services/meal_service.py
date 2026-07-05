import json
import logging
import os
import re
import uuid
from typing import Optional

from app.models.schemas import (
    MealOption,
    SuggestMealsRequest,
    SuggestMealsResponse,
    SuggestSupplementsRequest,
    SuggestSupplementsResponse,
)
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

FOOD_GROUP_SUPPLEMENTS = {
    "Grains": ["Whole grain bread", "Quinoa", "Brown rice"],
    "Protein": ["Grilled chicken", "Chickpeas", "Greek yogurt"],
    "Dairy": ["A glass of milk", "Cottage cheese", "Plain yogurt"],
    "Fruits": ["Sliced apple", "Mixed berries", "An orange"],
    "Vegetables": ["Side salad", "Steamed broccoli", "Roasted carrots"],
    "Fats": ["Avocado slices", "A drizzle of olive oil", "A handful of nuts"],
}

NUTRITION_SCHEMA = {
    "type": "object",
    "properties": {
        "calories": {"type": "integer"},
        "protein_g": {"type": "integer"},
        "carbs_g": {"type": "integer"},
        "fat_g": {"type": "integer"},
        "fiber_g": {"type": "integer"},
        "sodium_mg": {"type": "integer"},
        "sugar_g": {"type": "integer"},
    },
    "required": ["calories", "protein_g"],
    "additionalProperties": False,
}

MEAL_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "meals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "ingredients": {"type": "array", "items": {"type": "string"}},
                    "instructions": {"type": "array", "items": {"type": "string"}},
                    "cuisine": {"type": "string"},
                    "prep_time_minutes": {"type": "integer"},
                    "cook_time_minutes": {"type": "integer"},
                    "difficulty": {"type": "string"},
                    "cookware": {"type": "array", "items": {"type": "string"}},
                    "nutrition": NUTRITION_SCHEMA,
                    "light_option": {
                        "type": "object",
                        "properties": {
                            "swap": {"type": "string"},
                            "changes": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "from": {"type": "string"},
                                        "to": {"type": "string"},
                                    },
                                    "required": ["from", "to"],
                                    "additionalProperties": False,
                                },
                            },
                            "nutrition": NUTRITION_SCHEMA,
                        },
                        "required": ["swap", "changes", "nutrition"],
                        "additionalProperties": False,
                    },
                },
                "required": [
                    "name",
                    "description",
                    "ingredients",
                    "instructions",
                    "cuisine",
                    "prep_time_minutes",
                    "cook_time_minutes",
                    "difficulty",
                    "cookware",
                    "nutrition",
                    "light_option",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["meals"],
    "additionalProperties": False,
}


class MealService:
    def __init__(self, storage_service: Optional[StorageService] = None):
        self.storage_service = storage_service or StorageService()

    def _build_prompt(self, request: SuggestMealsRequest) -> str:
        cuisine = request.cuisine or "any cuisine"
        leftovers = "with leftovers in mind" if request.leftovers else "without leftovers"
        ingredients = ", ".join(request.ingredients)
        return (
            f"You are a meal planning assistant. Suggest 1 meal for the user based on these ingredients: {ingredients}. "
            f"Cuisine preference: {cuisine}. Servings: {request.servings}. {leftovers}. "
            "Return a JSON object with a single key 'meals' whose value is a list containing one meal object with these fields: "
            "name, description, ingredients, instructions, cuisine, prep_time_minutes, cook_time_minutes, difficulty, cookware, nutrition, light_option. "
            "light_option should describe a genuinely lighter version of the same meal: 'swap' is a one-sentence summary of the "
            "main substitution; 'changes' is a list of exact ingredient substitutions, each an object with 'from' (the specific "
            "ingredient and quantity in the regular recipe, e.g. '2 tbsp butter') and 'to' (the exact replacement and quantity, "
            "e.g. '1 tbsp olive oil'); and 'nutrition' is the full nutrition breakdown for that lighter version (it must differ "
            "from the regular nutrition, generally lower in calories, fat, and sodium)."
        )

    def _parse_meal_payload(self, payload: dict) -> MealOption:
        meal_data = payload["meals"][0]
        return MealOption(
            id=str(uuid.uuid4())[:8],
            name=meal_data.get("name", "Untitled meal"),
            description=meal_data.get("description", ""),
            ingredients=meal_data.get("ingredients", []),
            instructions=meal_data.get("instructions", []),
            cuisine=meal_data.get("cuisine"),
            prep_time_minutes=meal_data.get("prep_time_minutes"),
            cook_time_minutes=meal_data.get("cook_time_minutes"),
            difficulty=meal_data.get("difficulty"),
            cookware=meal_data.get("cookware"),
            nutrition=meal_data.get("nutrition"),
            light_option=meal_data.get("light_option"),
        )

    def suggest_meals(self, request: SuggestMealsRequest, user_id: str = "default") -> SuggestMealsResponse:
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if anthropic_api_key:
            try:
                import httpx

                from app.config import ANTHROPIC_MAX_TOKENS, ANTHROPIC_MODEL

                prompt = self._build_prompt(request)
                response = httpx.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": anthropic_api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": ANTHROPIC_MODEL,
                        "max_tokens": ANTHROPIC_MAX_TOKENS,
                        "output_config": {"format": {"type": "json_schema", "schema": MEAL_JSON_SCHEMA}},
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    body = response.json()
                    if body.get("stop_reason") == "max_tokens":
                        logger.warning("Anthropic response truncated at max_tokens; increase max_tokens if this recurs")
                    content = body.get("content", [])
                    text_block = next((item.get("text", "") for item in content if item.get("type") == "text"), "")
                    if text_block:
                        parsed = json.loads(text_block)
                        meal = self._parse_meal_payload(parsed)
                        self.storage_service.save_history_entry(meal, user_id=user_id)
                        return SuggestMealsResponse(meals=[meal], source="anthropic")
                else:
                    logger.error("Anthropic API returned %s: %s", response.status_code, response.text)
            except Exception:
                logger.exception("Failed to get meal suggestion from Anthropic API")

        meal = MealOption(
            id=str(uuid.uuid4())[:8],
            name="Quick Pantry Stir Fry",
            description="A simple meal built from the ingredients you listed.",
            ingredients=request.ingredients[:6],
            instructions=[
                "Heat a pan with a little oil.",
                "Cook the ingredients until tender.",
                "Season and serve warm.",
            ],
            cuisine=request.cuisine or "Any",
            prep_time_minutes=10,
            cook_time_minutes=15,
            difficulty="Easy",
            cookware=["Pan", "Knife", "Cutting board"],
            nutrition={"calories": 480, "protein_g": 24},
            light_option={
                "swap": "Use less oil and add extra vegetables.",
                "changes": [
                    {"from": "2 tbsp cooking oil", "to": "1 tsp cooking oil or oil spray"},
                    {"from": "1 cup mixed vegetables", "to": "2 cups mixed vegetables"},
                ],
                "nutrition": {"calories": 400, "protein_g": 24},
            },
        )

        self.storage_service.save_history_entry(meal, user_id=user_id)
        return SuggestMealsResponse(
            meals=[meal],
            source="local-fallback",
            note="Anthropic API was not available, so a local fallback meal was returned.",
        )

    def _local_supplements(self, request: SuggestSupplementsRequest) -> list[str]:
        supplements = []
        for group in request.missing_food_groups:
            options = FOOD_GROUP_SUPPLEMENTS.get(group)
            if options:
                supplements.append(options[0])
        return supplements

    def _build_supplements_prompt(self, request: SuggestSupplementsRequest) -> str:
        ingredients = ", ".join(request.ingredients) or "unknown ingredients"
        groups = ", ".join(request.missing_food_groups)
        return (
            f"A user is eating '{request.meal_name}', made with: {ingredients}. "
            f"This meal is light on these food groups: {groups}. "
            "Suggest 3-5 simple, easy-to-add ingredients or side items that would bridge this nutritional gap. "
            'Return only valid JSON with this exact shape: {"supplements": ["item1", "item2"]}'
        )

    def suggest_supplements(self, request: SuggestSupplementsRequest) -> SuggestSupplementsResponse:
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if anthropic_api_key:
            try:
                import httpx

                from app.config import ANTHROPIC_MODEL

                response = httpx.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": anthropic_api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": ANTHROPIC_MODEL,
                        "max_tokens": 300,
                        "messages": [{"role": "user", "content": self._build_supplements_prompt(request)}],
                    },
                    timeout=20.0,
                )
                response.raise_for_status()
                content = response.json().get("content", [])
                text = next((item.get("text", "") for item in content if item.get("type") == "text"), "")
                match = re.search(r"\{.*\}", text, flags=re.DOTALL)
                payload = json.loads(match.group(0)) if match else json.loads(text)
                supplements = payload.get("supplements") or []
                if supplements:
                    return SuggestSupplementsResponse(supplements=supplements[:5], source="anthropic")
            except Exception:
                logger.exception("Failed to get supplement suggestions from Anthropic API")

        return SuggestSupplementsResponse(
            supplements=self._local_supplements(request),
            source="local-fallback",
        )
