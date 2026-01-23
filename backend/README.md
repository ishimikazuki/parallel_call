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

1. Get your Account SID / Auth Token
   - Log in to the Twilio Console Dashboard: https://console.twilio.com/
   - In **Account Info**, copy **Account SID** and **Auth Token**.
2. (Trial accounts) Verify caller IDs
   - Trial accounts can only call verified numbers.
   - Go to Verified Caller IDs and add the destination numbers you want to call:
     https://www.twilio.com/console/phone-numbers/verified
3. Get a Twilio phone number
   - Console: In the Twilio Console, search and select a phone number by area code or number type.
     Docs: https://www.twilio.com/en-us/phone-numbers
     - Note: You may need to complete a verification process before calling or messaging.
   - CLI (optional):
     - Login (creates a CLI profile): `twilio login`
     - List available numbers:
       `twilio api:core:available-phone-numbers:local:list --area-code 503 --country-code US`
     - Purchase a number:
       `twilio api:core:incoming-phone-numbers:create --phone-number "+1XXXXXXXXXX"`
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
