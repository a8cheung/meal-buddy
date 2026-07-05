from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from app.config import AWS_REGION, DYNAMODB_TABLE_NAME
from app.models.schemas import CommentPayload, HistoryEntry, MealOption, RatingPayload


def _to_dynamo(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _to_dynamo(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_dynamo(v) for v in value]
    return value


def _from_dynamo(value):
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, dict):
        return {k: _from_dynamo(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_from_dynamo(v) for v in value]
    return value


class DynamoDBStorageService:
    """History storage backed by a DynamoDB table with partition key 'user_id' and sort key 'id'."""

    def __init__(self, table_name: Optional[str] = None, region: Optional[str] = None):
        import boto3  # imported lazily so boto3 is only required when this backend is actually used

        self._resource = boto3.resource("dynamodb", region_name=region or AWS_REGION)
        self.table = self._resource.Table(table_name or DYNAMODB_TABLE_NAME)

    def healthcheck(self) -> None:
        """Raises if the table is missing or credentials/network aren't available."""
        status = self.table.table_status
        if status != "ACTIVE":
            raise RuntimeError(f"DynamoDB table '{self.table.table_name}' is not active (status={status})")

    def get_history(self, user_id: str = "default") -> List[HistoryEntry]:
        from boto3.dynamodb.conditions import Key

        response = self.table.query(KeyConditionExpression=Key("user_id").eq(user_id))
        items = [_from_dynamo(item) for item in response.get("Items", [])]
        items.sort(key=lambda entry: entry.get("created_at", ""))
        return [HistoryEntry(**item) for item in items]

    def save_history_entry(self, meal: MealOption, user_id: str = "default") -> HistoryEntry:
        entry = {
            "id": meal.id,
            "meal": meal.model_dump(),
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "rating": None,
            "comment": None,
        }
        self.table.put_item(Item=_to_dynamo(entry))
        return HistoryEntry(**entry)

    def update_rating(self, payload: RatingPayload) -> Optional[HistoryEntry]:
        return self._update_field(
            user_id=payload.user_id or "default",
            meal_id=payload.meal_id,
            field="rating",
            value=payload.rating,
        )

    def update_comment(self, payload: CommentPayload) -> Optional[HistoryEntry]:
        return self._update_field(
            user_id=payload.user_id or "default",
            meal_id=payload.meal_id,
            field="comment",
            value=payload.comment,
        )

    def _update_field(self, user_id: str, meal_id: str, field: str, value) -> Optional[HistoryEntry]:
        try:
            response = self.table.update_item(
                Key={"user_id": user_id, "id": meal_id},
                UpdateExpression=f"SET #{field} = :value",
                ExpressionAttributeNames={f"#{field}": field},
                ExpressionAttributeValues={":value": _to_dynamo(value)},
                ConditionExpression="attribute_exists(id)",
                ReturnValues="ALL_NEW",
            )
        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            return None
        return HistoryEntry(**_from_dynamo(response["Attributes"]))
