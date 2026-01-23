"""Unit tests for OperatorManager."""

import pytest
from datetime import datetime, timezone, timedelta

from app.services.operator_manager import (
    OperatorManager,
    OperatorSession,
    OperatorStatus,
)


class TestOperatorSession:
    """Tests for OperatorSession."""

    def test_new_operator_is_offline(self):
        """新規オペレーターはOFFLINE"""
        operator = OperatorSession(id="op1", name="田中")
        assert operator.status == OperatorStatus.OFFLINE

    def test_operator_can_go_online(self):
        """オペレーターはオンラインになれる"""
        operator = OperatorSession(id="op1", name="田中")
        operator.go_online()
        assert operator.status == OperatorStatus.AVAILABLE

    def test_operator_can_go_offline(self):
        """オペレーターはオフラインになれる"""
        operator = OperatorSession(id="op1", name="田中")
        operator.go_online()
        operator.go_offline()
        assert operator.status == OperatorStatus.OFFLINE

    def test_operator_tracks_idle_time(self):
        """待機時間が追跡される"""
        operator = OperatorSession(id="op1", name="田中")
        before = datetime.now(timezone.utc)
        operator.go_online()

        assert operator.idle_since is not None
        assert operator.idle_since >= before

    def test_operator_can_be_on_call(self):
        """オペレーターは通話中になれる"""
        operator = OperatorSession(id="op1", name="田中")
        operator.go_online()
        operator.start_call(call_sid="CA123", lead_id="lead1")

        assert operator.status == OperatorStatus.ON_CALL
        assert operator.current_call_sid == "CA123"
        assert operator.current_lead_id == "lead1"

    def test_operator_becomes_available_after_call(self):
        """通話終了後はAVAILABLEに戻る"""
        operator = OperatorSession(id="op1", name="田中")
        operator.go_online()
        operator.start_call(call_sid="CA123", lead_id="lead1")
        operator.end_call()

        assert operator.status == OperatorStatus.AVAILABLE
        assert operator.current_call_sid is None

    def test_operator_can_go_on_break(self):
        """オペレーターは休憩できる"""
        operator = OperatorSession(id="op1", name="田中")
        operator.go_online()
        operator.go_on_break()

        assert operator.status == OperatorStatus.ON_BREAK

    def test_operator_can_return_from_break(self):
        """休憩から戻れる"""
        operator = OperatorSession(id="op1", name="田中")
        operator.go_online()
        operator.go_on_break()
        operator.return_from_break()

        assert operator.status == OperatorStatus.AVAILABLE


class TestOperatorRouting:
    """Tests for operator routing/selection."""

    def test_selects_longest_idle_operator(self):
        """最も長く待機しているオペレーターを選択"""
        manager = OperatorManager()

        now = datetime.now(timezone.utc)

        op1 = OperatorSession(id="op1", name="田中")
        op1.go_online()
        op1._idle_since = now - timedelta(seconds=10)

        op2 = OperatorSession(id="op2", name="鈴木")
        op2.go_online()
        op2._idle_since = now - timedelta(seconds=30)  # longest idle

        op3 = OperatorSession(id="op3", name="佐藤")
        op3.go_online()
        op3._idle_since = now - timedelta(seconds=20)

        manager.add_operator(op1)
        manager.add_operator(op2)
        manager.add_operator(op3)

        selected = manager.select_operator()
        assert selected is not None
        assert selected.id == "op2"

    def test_returns_none_when_no_available_operators(self):
        """利用可能なオペレーターがいなければNone"""
        manager = OperatorManager()

        op1 = OperatorSession(id="op1", name="田中")
        op1.go_online()
        op1.start_call(call_sid="CA123", lead_id="lead1")

        manager.add_operator(op1)

        selected = manager.select_operator()
        assert selected is None

    def test_skips_operators_on_break(self):
        """休憩中のオペレーターはスキップ"""
        manager = OperatorManager()

        now = datetime.now(timezone.utc)

        op1 = OperatorSession(id="op1", name="田中")
        op1.go_online()
        op1._idle_since = now - timedelta(seconds=100)  # longest but on break
        op1.go_on_break()

        op2 = OperatorSession(id="op2", name="鈴木")
        op2.go_online()
        op2._idle_since = now - timedelta(seconds=10)

        manager.add_operator(op1)
        manager.add_operator(op2)

        selected = manager.select_operator()
        assert selected is not None
        assert selected.id == "op2"


class TestOperatorManagerStats:
    """Tests for operator statistics."""

    def test_counts_available_operators(self):
        """利用可能なオペレーター数をカウント"""
        manager = OperatorManager()

        op1 = OperatorSession(id="op1", name="田中")
        op1.go_online()

        op2 = OperatorSession(id="op2", name="鈴木")
        op2.go_online()
        op2.start_call(call_sid="CA123", lead_id="lead1")

        op3 = OperatorSession(id="op3", name="佐藤")
        # offline

        manager.add_operator(op1)
        manager.add_operator(op2)
        manager.add_operator(op3)

        assert manager.available_count == 1
        assert manager.on_call_count == 1
        assert manager.offline_count == 1

    def test_gets_all_available_operators(self):
        """全利用可能オペレーターを取得"""
        manager = OperatorManager()

        op1 = OperatorSession(id="op1", name="田中")
        op1.go_online()

        op2 = OperatorSession(id="op2", name="鈴木")
        op2.go_online()

        op3 = OperatorSession(id="op3", name="佐藤")
        op3.go_online()
        op3.go_on_break()

        manager.add_operator(op1)
        manager.add_operator(op2)
        manager.add_operator(op3)

        available = manager.get_available_operators()
        assert len(available) == 2


class TestOperatorManagerCallAssignment:
    """Tests for call assignment."""

    def test_assign_call_to_specific_operator(self):
        """特定のオペレーターに通話を割り当て"""
        manager = OperatorManager()

        op1 = OperatorSession(id="op1", name="田中")
        op1.go_online()
        manager.add_operator(op1)

        result = manager.assign_call(
            operator_id="op1",
            call_sid="CA123",
            lead_id="lead1",
        )

        assert result is True
        assert op1.status == OperatorStatus.ON_CALL

    def test_cannot_assign_to_busy_operator(self):
        """通話中のオペレーターには割り当てられない"""
        manager = OperatorManager()

        op1 = OperatorSession(id="op1", name="田中")
        op1.go_online()
        op1.start_call(call_sid="CA999", lead_id="lead0")
        manager.add_operator(op1)

        result = manager.assign_call(
            operator_id="op1",
            call_sid="CA123",
            lead_id="lead1",
        )

        assert result is False

    def test_end_call_for_operator(self):
        """オペレーターの通話を終了"""
        manager = OperatorManager()

        op1 = OperatorSession(id="op1", name="田中")
        op1.go_online()
        manager.add_operator(op1)
        manager.assign_call("op1", "CA123", "lead1")

        manager.end_call("op1")

        assert op1.status == OperatorStatus.AVAILABLE


class TestLongIdleAlert:
    """Tests for long idle time alerts."""

    def test_detects_long_idle_operators(self):
        """長時間待機のオペレーターを検出"""
        manager = OperatorManager(max_idle_seconds=60)

        now = datetime.now(timezone.utc)

        op1 = OperatorSession(id="op1", name="田中")
        op1.go_online()
        op1._idle_since = now - timedelta(seconds=120)  # 2分待機

        op2 = OperatorSession(id="op2", name="鈴木")
        op2.go_online()
        op2._idle_since = now - timedelta(seconds=30)  # 30秒待機

        manager.add_operator(op1)
        manager.add_operator(op2)

        long_idle = manager.get_long_idle_operators()
        assert len(long_idle) == 1
        assert long_idle[0].id == "op1"
