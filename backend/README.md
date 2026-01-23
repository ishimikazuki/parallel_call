# ParallelDialer Backend

Predictive dialer system for telemarketing operations.

## Setup

```bash
pip install -e ".[dev]"
```

## Run Tests

```bash
pytest
```

## Run Server

```bash
uvicorn app.main:app --reload
```

## Database Migrations

```bash
# From backend/ directory
alembic upgrade head
```

## Twilio (Real Account) Setup

1. Find your Twilio credentials
   - Log in to the Twilio Console and open the Dashboard.
   - Copy your Account SID and Auth Token from the Account Info section.
2. Get a Twilio phone number (CLI)
   - List available numbers:
     `twilio api:core:available-phone-numbers:local:list --country-code "US" --area-code "503"`
   - Purchase a number:
     `twilio api:core:incoming-phone-numbers:create --phone-number "+1XXXXXXXXXX"`
   - Requires Twilio CLI to be installed and logged in with your account.
3. (Trial accounts) Verify caller IDs
   - Trial accounts can only call verified numbers; add destinations under Verified Caller IDs.
4. Create `.env` in `backend/`:

```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX
TWILIO_USE_MOCK=false
```

Notes:
- Phone numbers must be in E.164 format (e.g., +14155551212).
- If you want Twilio to send webhooks to your app, expose a public HTTPS URL and return TwiML.
