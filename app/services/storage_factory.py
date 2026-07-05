import logging

from app.config import STORAGE_BACKEND
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


def build_storage_service():
    """Returns the configured history storage backend.

    Defaults to local JSON storage. If STORAGE_BACKEND=dynamodb is set but the
    table/credentials aren't reachable, logs a warning and falls back to local
    JSON storage instead of failing to start.
    """
    if STORAGE_BACKEND != "dynamodb":
        return StorageService()

    try:
        from app.services.dynamodb_storage_service import DynamoDBStorageService

        service = DynamoDBStorageService()
        service.healthcheck()
        logger.info("Using DynamoDB storage backend (table=%s)", service.table.table_name)
        return service
    except Exception:
        logger.exception("DynamoDB storage unavailable; falling back to local JSON storage.")
        return StorageService()
