# ParallelDialer

Predictive dialer system for telemarketing operations (FastAPI + React + Twilio).

## Requirements

- Docker + Docker Compose
- Python 3.12+
- Node.js 20+

## Local Quickstart

```bash
# 1) Start DB/Redis
docker-compose up -d

# 2) Backend
cd backend
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload

# 3) Frontend (new terminal)
cd frontend
npm ci
cp .env.example .env
npm run dev
```

Open: http://localhost:5173

## Environment Variables (Step-by-step)

### Backend (`backend/.env`)

Copy template:

```bash
cp backend/.env.example backend/.env
```

Then fill these values:

#### 1) DATABASE_URL / REDIS_URL

- **Local** (Docker Compose default):
  - `DATABASE_URL=postgresql+asyncpg://parallel_dialer:dev_password@localhost:5432/parallel_dialer`
  - `REDIS_URL=redis://localhost:6379`
- **Production**: use your managed Postgres / Redis connection strings.

#### 2) SECRET_KEY

Generate a strong secret key:

```bash
python - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
```

Set:

```
SECRET_KEY=<generated value>
```

#### 3) CORS_ORIGINS / CORS_ORIGIN_REGEX

`CORS_ORIGINS` は JSON 配列で指定。
ローカルでポートが変わる場合は `CORS_ORIGIN_REGEX` を使うと便利。

例（固定）:
```
CORS_ORIGINS=["https://your-frontend.example.com"]
```

例（ローカルの任意ポートを許可）:
```
CORS_ORIGINS=[]
CORS_ORIGIN_REGEX=^http://localhost:\\d+$
```

#### 4) PUBLIC_BASE_URL (for Twilio webhook signature validation)

Set to the public HTTPS base URL that Twilio calls (e.g., ngrok URL).

```
PUBLIC_BASE_URL=https://xxxx.ngrok-free.app
```

Example (ngrok):

```bash
ngrok http 8000
```

#### 5) Twilio (Real Account)

If you only want mock calls in development, keep:

```
TWILIO_USE_MOCK=true
```

For real calls, set `TWILIO_USE_MOCK=false` and configure these:

```
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
TWILIO_API_KEY_SID=
TWILIO_API_KEY_SECRET=
TWILIO_APP_SID=
TWILIO_VALIDATE_SIGNATURE=true
```

**How to get each value (latest Twilio Console steps):**

1) **Account SID / Auth Token**
   - Log in to Twilio Console.
   - In the Console dashboard, open **Account → General Settings**.
   - Copy **Account SID** and **Auth Token** (click **Show** for the Auth Token).

2) **Buy a Phone Number**
   - Go to **Phone Numbers → Manage → Buy a number**.
   - Choose a number with **Voice** capability.
   - Set `TWILIO_PHONE_NUMBER` in E.164 format (e.g., `+14155551212`).
   - Trial accounts can only call **verified** numbers. Add verified caller IDs if needed.

3) **Create an API Key**
   - Go to **Admin → Account management → API keys & tokens**.
   - Create a **Standard** (or **Main**) API key.
   - Copy the **API Key SID** and **API Key Secret**.
   - Note: Use **Standard/Main** for Voice SDK Access Tokens.

4) **Create a TwiML App**
   - Go to **TwiML Apps** and create a new app.
   - Set **Voice Configuration** → **Request URL** to:
     - `https://<PUBLIC_BASE_URL>/webhooks/twilio/voice`
   - Save and copy the **TwiML App SID** (`TWILIO_APP_SID`).

5) **Webhook URLs**
   - Status Callback (for call lifecycle):
     - `https://<PUBLIC_BASE_URL>/webhooks/twilio/status`
   - AMD Callback (if using async AMD):
     - `https://<PUBLIC_BASE_URL>/webhooks/twilio/amd`

6) **Enable Signature Validation (recommended)**
   - Set `TWILIO_VALIDATE_SIGNATURE=true`
   - Ensure `PUBLIC_BASE_URL` is correct and uses HTTPS.

7) **Voice SDK Access Token**
   - Frontend can request a token from: `POST /api/v1/twilio/token`
   - Requires a valid JWT (login first).

### Frontend (`frontend/.env`)

Copy template:

```bash
cp frontend/.env.example frontend/.env
```

Optional values for split frontend/backend deployments:

```
VITE_API_BASE_URL=https://api.example.com/api/v1
VITE_WS_BASE_URL=wss://api.example.com
```

## Tests

### Backend

```bash
cd backend
pytest -m unit
```

### Frontend

```bash
cd frontend
npm run test:unit
```

### E2E

```bash
cd frontend
npx playwright test
```

## Notes

- Default demo login credentials (dev only):
  - `admin / admin123`
  - `operator1 / operator123`
- Real deployments should replace the in-memory user store with DB-backed users + bcrypt.
