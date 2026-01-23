# DB永続化（Campaign/Lead）

## Goal
- in-memory をやめて PostgreSQL 永続化に切り替える
- Alembic マイグレーションでテーブルを管理できる状態にする

## Done
- SQLAlchemy async engine/session/ORM を追加
- Campaign/Lead API をDB永続化へ切替
- Alembic 初期設定と初回マイグレーションを追加
- ドキュメント更新（README / document.md）

## Discoveries
- Alembic async 実行には greenlet が必要

## Decisions
- 2026-01-23: Campaign/Lead を先にDB化して段階的に移行

## Notes
- alembic はプロジェクトのPython環境で実行すること
