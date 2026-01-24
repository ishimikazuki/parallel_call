"""Unit tests for Lead model."""

from datetime import UTC, datetime

import pytest

from app.models.lead import InvalidStatusTransitionError, Lead, LeadStatus


class TestLeadCreation:
    """Tests for Lead creation."""

    def test_new_lead_has_pending_status(self):
        """新規リードはPENDINGステータスで作成される"""
        lead = Lead(phone_number="+818011112222")
        assert lead.status == LeadStatus.PENDING

    def test_lead_requires_phone_number(self):
        """電話番号は必須"""
        with pytest.raises(ValueError):
            Lead(phone_number="")

    def test_lead_validates_phone_number_format(self):
        """電話番号はE.164形式"""
        # 有効なフォーマット
        lead = Lead(phone_number="+818011112222")
        assert lead.phone_number == "+818011112222"

        # 無効なフォーマット
        with pytest.raises(ValueError):
            Lead(phone_number="08011112222")  # +なし

    def test_lead_can_have_optional_name(self):
        """名前はオプション"""
        lead = Lead(phone_number="+818011112222", name="田中太郎")
        assert lead.name == "田中太郎"

    def test_lead_tracks_creation_time(self):
        """作成日時が記録される"""
        before = datetime.now(UTC)
        lead = Lead(phone_number="+818011112222")
        after = datetime.now(UTC)

        assert before <= lead.created_at <= after


class TestLeadStatusTransitions:
    """Tests for Lead status transitions."""

    def test_pending_lead_can_start_calling(self):
        """PENDINGのリードは発信開始できる"""
        lead = Lead(phone_number="+818011112222")
        lead.start_calling()
        assert lead.status == LeadStatus.CALLING

    def test_calling_lead_can_be_connected(self):
        """CALLINGのリードは接続状態になれる"""
        lead = Lead(phone_number="+818011112222")
        lead.start_calling()
        lead.connect()
        assert lead.status == LeadStatus.CONNECTED

    def test_connected_lead_can_complete(self):
        """CONNECTEDのリードは完了できる"""
        lead = Lead(phone_number="+818011112222")
        lead.start_calling()
        lead.connect()
        lead.complete(outcome="interested")
        assert lead.status == LeadStatus.COMPLETED
        assert lead.outcome == "interested"

    def test_calling_lead_can_fail(self):
        """CALLINGのリードは失敗状態になれる"""
        lead = Lead(phone_number="+818011112222")
        lead.start_calling()
        lead.fail(reason="no_answer")
        assert lead.status == LeadStatus.FAILED
        assert lead.fail_reason == "no_answer"

    def test_lead_cannot_call_from_dnc_status(self):
        """DNCのリードは発信できない"""
        lead = Lead(phone_number="+818011112222")
        lead.mark_dnc()
        with pytest.raises(InvalidStatusTransitionError):
            lead.start_calling()

    def test_lead_cannot_call_from_completed_status(self):
        """COMPLETEDのリードは再発信できない"""
        lead = Lead(phone_number="+818011112222")
        lead.start_calling()
        lead.connect()
        lead.complete(outcome="not_interested")
        with pytest.raises(InvalidStatusTransitionError):
            lead.start_calling()

    def test_failed_lead_can_be_retried(self):
        """FAILEDのリードはリトライ可能（PENDINGに戻る）"""
        lead = Lead(phone_number="+818011112222")
        lead.start_calling()
        lead.fail(reason="busy")
        lead.retry()
        assert lead.status == LeadStatus.PENDING
        assert lead.retry_count == 1

    def test_lead_has_max_retry_limit(self):
        """リトライ回数に上限がある"""
        lead = Lead(phone_number="+818011112222", max_retries=3)

        for _ in range(3):
            lead.start_calling()
            lead.fail(reason="busy")
            lead.retry()

        # 4回目はリトライ不可
        lead.start_calling()
        lead.fail(reason="busy")
        with pytest.raises(InvalidStatusTransitionError):
            lead.retry()


class TestLeadCallHistory:
    """Tests for Lead call history tracking."""

    def test_lead_records_call_attempts(self):
        """通話試行が記録される"""
        lead = Lead(phone_number="+818011112222")
        lead.start_calling()
        lead.fail(reason="no_answer")

        assert len(lead.call_history) == 1
        assert lead.call_history[0]["reason"] == "no_answer"

    def test_lead_tracks_last_called_at(self):
        """最終発信日時が記録される"""
        lead = Lead(phone_number="+818011112222")
        before = datetime.now(UTC)
        lead.start_calling()

        assert lead.last_called_at is not None
        assert lead.last_called_at >= before


class TestLeadDNC:
    """Tests for Do Not Call functionality."""

    def test_any_lead_can_be_marked_dnc(self):
        """どのステータスのリードもDNCにできる"""
        lead = Lead(phone_number="+818011112222")
        lead.start_calling()
        lead.mark_dnc()
        assert lead.status == LeadStatus.DNC

    def test_dnc_lead_cannot_transition_to_other_status(self):
        """DNCのリードは他のステータスに変更できない"""
        lead = Lead(phone_number="+818011112222")
        lead.mark_dnc()

        with pytest.raises(InvalidStatusTransitionError):
            lead.start_calling()

        with pytest.raises(InvalidStatusTransitionError):
            lead.retry()
