import app.services.storage_factory as storage_factory
from app.services.storage_service import StorageService


def test_build_storage_service_defaults_to_local(monkeypatch):
    monkeypatch.setattr(storage_factory, "STORAGE_BACKEND", "local")
    service = storage_factory.build_storage_service()
    assert isinstance(service, StorageService)


def test_build_storage_service_falls_back_when_dynamodb_unavailable(monkeypatch):
    monkeypatch.setattr(storage_factory, "STORAGE_BACKEND", "dynamodb")

    class BrokenDynamoDBStorageService:
        def __init__(self):
            raise RuntimeError("no AWS credentials in test environment")

    monkeypatch.setattr(
        "app.services.dynamodb_storage_service.DynamoDBStorageService",
        BrokenDynamoDBStorageService,
    )

    service = storage_factory.build_storage_service()
    assert isinstance(service, StorageService)


def test_build_storage_service_uses_dynamodb_when_healthy(monkeypatch):
    monkeypatch.setattr(storage_factory, "STORAGE_BACKEND", "dynamodb")

    class FakeTable:
        table_name = "fake-table"

    class FakeDynamoDBStorageService:
        def __init__(self):
            self.table = FakeTable()

        def healthcheck(self):
            return None

    monkeypatch.setattr(
        "app.services.dynamodb_storage_service.DynamoDBStorageService",
        FakeDynamoDBStorageService,
    )

    service = storage_factory.build_storage_service()
    assert isinstance(service, FakeDynamoDBStorageService)
