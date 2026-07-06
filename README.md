
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

## Operations cheat sheet

Commands worth keeping handy — for this app, or as a reference next time you deploy something similar.

### AWS CLI basics

```bash
aws configure                      # set access key/secret + default region interactively
aws configure set region us-east-1 # set/override just the region
aws configure get region           # check what region is currently configured
```

Use an IAM user for day-to-day CLI work, not root credentials — root should only be used for
account-level tasks (billing, closing the account, etc.).

### DynamoDB

```bash
# Check table status (should be ACTIVE)
aws dynamodb describe-table --table-name meal-suggester-history --query 'Table.TableStatus'

# Look at everything stored (fine for small tables; Scan reads the whole table)
aws dynamodb scan --table-name meal-suggester-history

# Query one user's history (efficient — uses the partition key instead of scanning)
aws dynamodb query \
  --table-name meal-suggester-history \
  --key-condition-expression "user_id = :u" \
  --expression-attribute-values '{":u":{"S":"default"}}'

# Delete the table entirely (irreversible)
aws dynamodb delete-table --table-name meal-suggester-history
```

### EC2: connect to the instance

```bash
chmod 400 ~/Downloads/meal-suggester-key.pem      # required once; key file must not be world-readable
ssh -i ~/Downloads/meal-suggester-key.pem ec2-user@<EC2_PUBLIC_IP>
```

The public IP can change if you stop/start the instance (unless you allocate an Elastic IP) —
check the current one in EC2 console → Instances → your instance → "Public IPv4 address".

If SSH suddenly stops connecting, check the security group's SSH rule first: "My IP" is a
one-time snapshot taken when the rule was created, not something that auto-updates as your
IP changes.

### systemd: managing the app service (run on the EC2 instance)

```bash
sudo systemctl status meal-suggester    # is it running?
sudo systemctl restart meal-suggester   # restart after code changes or .env edits
sudo systemctl stop meal-suggester
sudo systemctl start meal-suggester
sudo journalctl -u meal-suggester -f              # tail live logs (Ctrl+C to stop)
sudo journalctl -u meal-suggester -n 100 --no-pager  # last 100 log lines
```

### nginx: managing the reverse proxy (run on the EC2 instance)

```bash
sudo nginx -t                 # test config for syntax errors before reloading
sudo systemctl reload nginx   # apply a config change without dropping connections
sudo systemctl restart nginx  # full restart
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Deploying a code update

From your Mac: commit and push as usual. Then on the EC2 instance:

```bash
cd ~/meal-suggester
git pull
.venv/bin/pip install -r requirements.txt   # only needed if requirements.txt changed
sudo systemctl restart meal-suggester
```

If `deploy/meal-suggester.service` or `deploy/nginx-meal-suggester.conf` changed, re-copy them:

```bash
sudo cp ~/meal-suggester/deploy/meal-suggester.service /etc/systemd/system/meal-suggester.service
sudo systemctl daemon-reload
sudo cp ~/meal-suggester/deploy/nginx-meal-suggester.conf /etc/nginx/conf.d/meal-suggester.conf
sudo nginx -t && sudo systemctl reload nginx
```

### Quick end-to-end check

```bash
curl -s http://127.0.0.1/api/health          # from inside the EC2 instance
curl -s http://<EC2_PUBLIC_IP>/api/health    # from your Mac
```
