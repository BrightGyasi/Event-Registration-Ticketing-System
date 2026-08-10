# Event Registration & Ticketing System

Serverless REST API on AWS that replaces Microsoft Forms + Excel for event
registration. Built with AWS SAM, Python 3.12 Lambda functions, DynamoDB,
API Gateway, CloudWatch, SNS, and AWS Budgets.

## Architecture

```
Client ──▶ API Gateway ──▶ 4 Lambda functions ──▶ DynamoDB (Events, Registrations)
                                   │
                                   ├──▶ SNS (confirmation emails, optional)
                                   └──▶ CloudWatch (logs, metrics, alarms) ──▶ SNS (ops alerts)

GitHub Actions ──(OIDC, no static keys)──▶ sam build / sam deploy ──▶ CloudFormation stack
AWS Budgets ──▶ email alert at 80% actual spend and 100% forecasted spend
```

Each Lambda has its **own IAM role** with only the DynamoDB actions it
actually performs (see `template.yaml` — no `DynamoDBFullAccess` anywhere).

| Endpoint | Function | DynamoDB access |
|---|---|---|
| `POST /register` | `RegisterFunction` | Read Events, conditional update Events, put Registrations |
| `GET /events` | `ListEventsFunction` | Scan Events |
| `GET /registrations/{email}` | `GetRegistrationsFunction` | Query Registrations via `EmailIndex` GSI |
| `DELETE /registration/{id}` | `CancelRegistrationFunction` | Delete Registrations, update Events |

## Repository layout

```
event-ticketing-system/
├── template.yaml                  # SAM/CloudFormation stack definition
├── samconfig.toml                 # sam deploy defaults (dev/prod)
├── layers/common_layer/python/    # shared validation & response helpers
├── src/
│   ├── register/app.py            # POST /register
│   ├── list_events/app.py         # GET /events
│   ├── get_registrations/app.py   # GET /registrations/{email}
│   └── cancel_registration/app.py # DELETE /registration/{id}
├── tests/unit/                    # pytest + moto (mocked AWS, no real account needed)
├── scripts/seed_events.py         # load sample events after first deploy
├── docs/github-oidc-bootstrap.yaml# one-time OIDC role for CI/CD (deploy this by hand first)
└── .github/workflows/ci-cd.yml    # test on every push/PR, deploy on merge to main
```

---

## Phase 1 — Architecture & foundations (done in this repo)

- **Data model**: two tables.
  - `Events` (PK `eventId`): `eventName`, `eventDate`, `location`, `capacity`, `registeredCount`.
  - `Registrations` (PK `registrationId`, GSI `EmailIndex` on `email`): `eventId`, `email`, `name`, `status`, `createdAt`.
  - Capacity is enforced with a **conditional `UpdateItem`** (`registeredCount < capacity`), so two people registering for the last seat at the same instant can't both succeed — no race condition, no separate lock needed.
- **CloudWatch Logs & Alarms**: every Lambda logs to its own log group automatically; alarms are defined in `template.yaml` (see Phase 4).
- **SNS**: optional confirmation-email topic (`EnableConfirmationEmails` parameter), plus a separate ops-alerts topic that CloudWatch alarms and AWS Budgets both notify.
- **AWS Budgets**: a monthly cost budget (`MonthlyBudgetLimit`, default $5) with alerts at 80% actual and 100% forecasted spend, to keep the whole project inside Free Tier.

## Phase 2 — API development (done in this repo)

The four endpoints are implemented in `src/*/app.py`. Each one:
1. Validates and sanitizes input (see `layers/common_layer/python/validation.py`) — type checks, length caps, email regex, printable-character filtering.
2. Returns structured JSON errors with the right HTTP status (`400` validation, `404` not found, `409` conflict/full, `500` unexpected).
3. Uses least-privilege DynamoDB calls only (no scans on the hot path except the intentionally paginated `GET /events`).

Run the tests locally:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/ -v
```

Tests use `moto` to mock DynamoDB — no AWS account or network access required.

## Phase 3 — CI/CD with GitHub Actions

Branching strategy:
- `main` — protected, always deployable, auto-deploys to the `dev` stage on merge.
- `develop` — integration branch for in-progress work (tested but not deployed).
- `feature/*` — one branch per task, opened as a PR into `develop` or `main`.

Pipeline (`.github/workflows/ci-cd.yml`):
1. **`test` job** (every push and PR): `ruff` lint → `pytest` unit tests → `sam validate --lint` → `sam build` as a packaging smoke test. No AWS credentials are used in this job.
2. **`deploy` job** (only on push to `main`, after `test` passes): assumes an AWS IAM role via **GitHub OIDC** (`aws-actions/configure-aws-credentials`) — no long-lived AWS access keys stored as GitHub secrets — then runs `sam build` and `sam deploy`, followed by a smoke test that curls `GET /events` and fails the deploy if it doesn't return `200`.

One-time setup before the pipeline can deploy:
```bash
aws cloudformation deploy \
  --template-file docs/github-oidc-bootstrap.yaml \
  --stack-name event-ticketing-github-oidc \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides GitHubOrgAndRepo=your-org/event-ticketing-system
```
Then add two repository secrets: `AWS_DEPLOY_ROLE_ARN` (from the stack output) and `ALERT_EMAIL`.

Monitor pipeline runs under the repo's **Actions** tab — each run shows the lint, test, build, and deploy steps individually, so a failing stage is easy to isolate.

## Phase 4 — Monitoring & security (done in this repo)

**Monitoring**
- `RegisterErrorsAlarm` — fires if the Register function logs ≥3 errors in 5 minutes.
- `LambdaDurationAlarm` — fires if p90 duration exceeds 8s (80% of the 10s timeout), an early warning before real timeouts start happening.
- `ApiGateway5xxAlarm` — computed as `(5XXError / Count) * 100` over 5 minutes; fires above **5% error rate**, matching the stated requirement.
- All three alarms notify `AlertsTopic` (email via SNS).
- Every Lambda automatically gets a CloudWatch Log Group (`/aws/lambda/<function-name>`), and X-Ray tracing is enabled (`Tracing: Active`) for request tracing across API Gateway → Lambda → DynamoDB.

**Security**
- **Least privilege IAM**: every function's policy lists specific `dynamodb:*` actions against specific table/index ARNs — nothing broader.
- **Input validation & sanitization**: centralized in the shared Lambda layer — email regex, string length caps, printable-character filtering, JSON parse error handling, and integer bounds on pagination `limit`.
- **No secrets in code**: alert email, budget limit, and the SNS toggle are stack parameters, not hardcoded values.
- **API security patterns worth adding next** (not yet in this template, listed for the write-up): API keys + usage plans or a Cognito/JWT authorizer if this stops being a public-registration form; AWS WAF in front of API Gateway for rate limiting and common exploit patterns; DynamoDB encryption at rest is already on (`SSESpecification.SSEEnabled`).

**Cost control**
- `MonthlyBudget` (AWS Budgets) — see Phase 1. DynamoDB is `PAY_PER_REQUEST`, Lambda is 128MB, all comfortably inside AWS Free Tier at capstone-project traffic levels.

---

## Deploying it yourself

```bash
# 1. Install AWS SAM CLI and configure AWS credentials
sam --version
aws configure

# 2. Build
sam build

# 3. First deploy — guided mode asks for Stage, AlertEmail, MonthlyBudgetLimit
sam deploy --guided

# 4. (Optional) seed a few sample events
python scripts/seed_events.py --table Events-dev

# 5. Confirm the SNS email subscription — check your inbox for
#    "AWS Notification - Subscription Confirmation" and click Confirm,
#    or alarms/budget alerts and confirmation emails won't be delivered.
```

Try it:
```bash
API=<ApiEndpoint from the sam deploy output>

curl "$API/events"

curl -X POST "$API/register" -H "Content-Type: application/json" \
  -d '{"eventId":"career-fair-2026","name":"Ada Lovelace","email":"ada@example.com"}'

curl "$API/registrations/ada@example.com"

curl -X DELETE "$API/registration/<registrationId from above>"
```

Tear down:
```bash
sam delete --stack-name event-ticketing-dev
```

## Design notes worth mentioning in the capstone write-up

- **Why one Lambda per endpoint** instead of one monolith Lambda: smaller
  blast radius per deploy, tighter per-function IAM, independent scaling
  and cold-start profile, and clearer CloudWatch metrics/alarms per
  operation.
- **Why a conditional `UpdateItem` for capacity** instead of reading
  `registeredCount` then writing it back: avoids the classic
  read-then-write race condition under concurrent registrations without
  needing DynamoDB transactions.
- **Why a Lambda Layer for validation code**: keeps the four function
  packages small and avoids copy-pasting the same regex/response-builder
  four times — a change to validation rules happens in one file.
- **Why GitHub OIDC instead of access keys**: no long-lived AWS
  credentials sitting in GitHub secrets that could leak; the role can
  only be assumed by workflows running on `main` in this specific repo.
