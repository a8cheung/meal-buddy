import app.services.meal_service as meal_service_module
from app.models.schemas import SuggestMealsRequest
from app.services.meal_service import MealService


class DummyStorage:
    def save_history_entry(self, meal, user_id="default"):
        return None


def test_suggest_meals_uses_anthropic_when_api_key_is_available(monkeypatch):
    class DummyResponse:
        status_code = 200

        def json(self):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": '{"meals": [{"name": "Test Pasta", "description": "A test meal", "ingredients": ["pasta"], "instructions": ["Cook pasta"]}]}'
                    }
                ]
            }

    def fake_post(*args, **kwargs):
        return DummyResponse()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr("httpx.post", fake_post)

    service = MealService(storage_service=DummyStorage())
    request = SuggestMealsRequest(ingredients=["pasta", "tomato"], cuisine="Italian", servings=2)

    response = service.suggest_meals(request)

    assert response.source == "anthropic"
    assert response.meals[0].name == "Test Pasta"
