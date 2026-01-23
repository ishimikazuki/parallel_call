# ParallelDialer - document.md

## プロジェクト概要
- 目的: テレアポ業務効率化のための並列自動発信（プレディクティブダイヤラー）システム
- 技術スタック:
  - Backend: Python 3.12 + FastAPI + PostgreSQL + Redis
  - Frontend: React 18 + TypeScript + Vite
  - 通話: Twilio Voice SDK (WebRTC)
  - 状態管理: Zustand
- 現在のフェーズ: **全Phase完了** (Phase 0-5)

## 重要ルール・制約
- TDD: テストファースト開発
- Twilio: 開発時はMock、本番は実アカウント
- 認証: JWT (access + refresh token)
- 放棄率目標: 3%以下

## コア機能
1. **Predictive Dialing**: 放棄率に基づいてdial_ratioを動的調整
2. **Operator Routing**: 最長待機オペレーターを優先
3. **WebSocket**: リアルタイム通知（着信、統計、アラート）
4. **CSV Import**: UTF-8/Shift_JIS自動判定

## 今の作業
→ PLANS.md を参照

## 重要な決定事項
- 2025-01-17: Twilio統合はProtocolパターンでDI可能に設計
- 2025-01-17: 開発時認証はシンプルハッシュ（Python 3.13 + bcrypt問題回避）
- 2025-01-23: 全Phase完了、227テスト通過（Backend 167 + Frontend 60）
- 2026-01-23: Campaign/Lead を SQLAlchemy + Alembic で永続化

## ログ参照
→ PROJECT_LOG/INDEX.md
