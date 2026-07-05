
# Meal Suggester

A simple app that suggest meals based on ingredients and cuisine.

## Run

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
ANTHROPIC_API_KEY="sk-ant-..." .venv/bin/uvicorn main:app --reload --port 8001
```

Open `index.html` in a browser, or serve it from any static file server.

## Configuration

| Env var | Default | Purpose |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | (none) | If unset, the API returns a local fallback meal. |
| `ANTHROPIC_MODEL` | `claude-opus-4-8` | Model used for meal/supplement suggestions. |
| `ANTHROPIC_MAX_TOKENS` | `2048` | Max tokens for the meal-suggestion call. |
| `STORAGE_BACKEND` | `local` | `local` (JSON file in `data/history.json`) or `dynamodb`. |
| `DYNAMODB_TABLE_NAME` | `meal-suggester-history` | Table name when `STORAGE_BACKEND=dynamodb`. |
| `AWS_REGION` | `us-east-1` | Region for the DynamoDB table. |

If `STORAGE_BACKEND=dynamodb` is set but the table or AWS credentials aren't reachable at
startup, the app logs a warning and falls back to local JSON storage rather than failing to boot.

### DynamoDB table setup

Create a table with partition key `user_id` (String) and sort key `id` (String):

```bash
aws dynamodb create-table \
  --table-name meal-suggester-history \
  --attribute-definitions AttributeName=user_id,AttributeType=S AttributeName=id,AttributeType=S \
  --key-schema AttributeName=user_id,KeyType=HASH AttributeName=id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST
```

## Test

```bash
.venv/bin/pytest -q
```
