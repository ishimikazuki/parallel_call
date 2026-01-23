# ParallelDialer TDD Implementation - Initial Setup

## Goal
TDDでParallelDialer（テレアポ用並列自動発信システム）の基盤を構築する

## Done

### Phase 0: Project Setup ✅
- docker-compose.yml (PostgreSQL 16 + Redis 7)
- Backend: pyproject.toml, FastAPI基盤
- Frontend: package.json, Vite + Vitest
- Twilio Mock Service (Protocol pattern)
- CI/CD: GitHub Actions

### Phase 1: Domain Models ✅
- Lead model (status transitions: PENDING → CALLING → CONNECTED → COMPLETED)
- Campaign model (stats calculation)
- DialerOrchestrator (predictive dial ratio algorithm)
- OperatorManager (longest-idle-first routing)
- **73 tests passed**

### Phase 2: API Layer ✅
- Auth API (login, refresh, me with JWT)
- Campaign API (CRUD, start/pause/stop, stats, leads)
- Lead Import API (CSV with encoding auto-detection)
- Twilio Webhooks (status, AMD, voice)
- **115 tests passed**

### Phase 3: WebSocket ✅
- ConnectionManager (broadcast, group messaging)
- Operator WebSocket (incoming_call, call_connected, call_ended)
- Dashboard WebSocket (campaign stats, operator list, alerts)
- **131 tests passed**

### Phase 4: Frontend (In Progress)
- Types: Lead, Campaign, Operator, WebSocket messages
- API Client: authApi, campaignApi
- Hooks: useWebSocket, useTwilioDevice
- Components: StatusToggle, CallPopup, RealtimeStats, OperatorList
- Stores: authStore (Zustand)
- **58/60 tests passed** (2 minor test assertion fixes needed)

## Discoveries
- 2025-01-17: bcrypt/passlib がPython 3.13で動かなかったため、開発用にSHA256ハッシュに切り替え
- 2025-01-17: CampaignStats.abandon_rateは計算プロパティで、初期化パラメータではない
- 2025-01-23: フロントエンドテストの一部でDOM構造の想定がずれていた（軽微）

## Decisions
- 2025-01-17: Twilio Mock → Protocol pattern で DI 切り替え可能に
- 2025-01-17: 認証は開発時はシンプルハッシュ、本番はbcryptに差し替え予定
- 2025-01-17: WebSocket認証はクエリパラメータでtoken渡し

## Notes
- Phase 5 (E2E Tests) は未着手
- フロントエンドのOperatorListテスト2件を修正する必要あり
- Twilio実アカウント接続は後日対応
