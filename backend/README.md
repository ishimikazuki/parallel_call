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
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Database Migrations

```bash
# From backend/ directory
alembic upgrade head
```

## Environment Variables

See the repository root `README.md` for step-by-step environment setup and Twilio credentials.
