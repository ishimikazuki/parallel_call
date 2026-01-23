"""Unit tests for Campaign model."""

import pytest
from datetime import datetime, timezone

from app.models.campaign import (
    Campaign,
    CampaignStatus,
    CampaignStats,
    InvalidCampaignStateError,
)
from app.models.lead import Lead


class TestCampaignCreation:
    """Tests for Campaign creation."""

    def test_new_campaign_has_draft_status(self):
        """新規キャンペーンはDRAFTステータス"""
        campaign = Campaign(name="テストキャンペーン")
        assert campaign.status == CampaignStatus.DRAFT

    def test_campaign_requires_name(self):
        """キャンペーン名は必須"""
        with pytest.raises(ValueError):
            Campaign(name="")

    def test_campaign_has_default_dial_ratio(self):
        """デフォルトのダイヤル比率は3.0"""
        campaign = Campaign(name="テスト")
        assert campaign.dial_ratio == 3.0

    def test_campaign_can_set_custom_dial_ratio(self):
        """カスタムダイヤル比率を設定可能"""
        campaign = Campaign(name="テスト", dial_ratio=2.5)
        assert campaign.dial_ratio == 2.5

    def test_campaign_tracks_creation_time(self):
        """作成日時が記録される"""
        before = datetime.now(timezone.utc)
        campaign = Campaign(name="テスト")
        after = datetime.now(timezone.utc)

        assert before <= campaign.created_at <= after


class TestCampaignStatusTransitions:
    """Tests for Campaign status transitions."""

    def test_draft_campaign_can_be_started(self):
        """DRAFTのキャンペーンは開始できる"""
        campaign = Campaign(name="テスト")
        campaign.add_lead(Lead(phone_number="+818011112222"))
        campaign.start()
        assert campaign.status == CampaignStatus.RUNNING

    def test_cannot_start_campaign_without_leads(self):
        """リードがないキャンペーンは開始できない"""
        campaign = Campaign(name="テスト")
        with pytest.raises(InvalidCampaignStateError):
            campaign.start()

    def test_running_campaign_can_be_paused(self):
        """RUNNINGのキャンペーンは一時停止できる"""
        campaign = Campaign(name="テスト")
        campaign.add_lead(Lead(phone_number="+818011112222"))
        campaign.start()
        campaign.pause()
        assert campaign.status == CampaignStatus.PAUSED

    def test_paused_campaign_can_be_resumed(self):
        """PAUSEDのキャンペーンは再開できる"""
        campaign = Campaign(name="テスト")
        campaign.add_lead(Lead(phone_number="+818011112222"))
        campaign.start()
        campaign.pause()
        campaign.resume()
        assert campaign.status == CampaignStatus.RUNNING

    def test_running_campaign_can_be_stopped(self):
        """RUNNINGのキャンペーンは停止できる"""
        campaign = Campaign(name="テスト")
        campaign.add_lead(Lead(phone_number="+818011112222"))
        campaign.start()
        campaign.stop()
        assert campaign.status == CampaignStatus.STOPPED

    def test_stopped_campaign_cannot_be_resumed(self):
        """STOPPEDのキャンペーンは再開できない"""
        campaign = Campaign(name="テスト")
        campaign.add_lead(Lead(phone_number="+818011112222"))
        campaign.start()
        campaign.stop()
        with pytest.raises(InvalidCampaignStateError):
            campaign.resume()

    def test_campaign_completes_when_all_leads_processed(self):
        """全リード処理完了でCOMPLETED"""
        campaign = Campaign(name="テスト")
        lead = Lead(phone_number="+818011112222")
        campaign.add_lead(lead)
        campaign.start()

        # リードを処理完了にする
        lead.start_calling()
        lead.connect()
        lead.complete(outcome="interested")

        campaign.check_completion()
        assert campaign.status == CampaignStatus.COMPLETED


class TestCampaignLeadManagement:
    """Tests for Campaign lead management."""

    def test_can_add_lead_to_draft_campaign(self):
        """DRAFTキャンペーンにリードを追加できる"""
        campaign = Campaign(name="テスト")
        lead = Lead(phone_number="+818011112222")
        campaign.add_lead(lead)
        assert len(campaign.leads) == 1
        assert lead.campaign_id == campaign.id

    def test_can_add_lead_to_running_campaign(self):
        """RUNNINGキャンペーンにもリードを追加できる"""
        campaign = Campaign(name="テスト")
        campaign.add_lead(Lead(phone_number="+818011112222"))
        campaign.start()

        new_lead = Lead(phone_number="+818033334444")
        campaign.add_lead(new_lead)
        assert len(campaign.leads) == 2

    def test_cannot_add_duplicate_phone_number(self):
        """同じ電話番号は追加できない"""
        campaign = Campaign(name="テスト")
        campaign.add_lead(Lead(phone_number="+818011112222"))

        with pytest.raises(ValueError):
            campaign.add_lead(Lead(phone_number="+818011112222"))

    def test_get_next_lead_returns_pending_lead(self):
        """get_next_leadはPENDINGのリードを返す"""
        campaign = Campaign(name="テスト")
        lead1 = Lead(phone_number="+818011112222")
        lead2 = Lead(phone_number="+818033334444")
        campaign.add_lead(lead1)
        campaign.add_lead(lead2)
        campaign.start()

        next_lead = campaign.get_next_lead()
        assert next_lead is not None
        assert next_lead.status.value == "pending"

    def test_get_next_lead_returns_none_when_no_pending(self):
        """PENDINGがない場合はNone"""
        campaign = Campaign(name="テスト")
        lead = Lead(phone_number="+818011112222")
        campaign.add_lead(lead)
        campaign.start()

        lead.start_calling()  # PENDINGから変更

        next_lead = campaign.get_next_lead()
        assert next_lead is None


class TestCampaignStats:
    """Tests for Campaign statistics."""

    def test_new_campaign_has_zero_stats(self):
        """新規キャンペーンは統計が0"""
        campaign = Campaign(name="テスト")
        stats = campaign.get_stats()

        assert stats.total_leads == 0
        assert stats.pending_leads == 0
        assert stats.completed_leads == 0
        assert stats.failed_leads == 0

    def test_stats_reflect_lead_statuses(self):
        """統計はリードのステータスを反映"""
        campaign = Campaign(name="テスト")

        lead1 = Lead(phone_number="+818011111111")
        lead2 = Lead(phone_number="+818022222222")
        lead3 = Lead(phone_number="+818033333333")

        campaign.add_lead(lead1)
        campaign.add_lead(lead2)
        campaign.add_lead(lead3)
        campaign.start()

        # lead1: 完了
        lead1.start_calling()
        lead1.connect()
        lead1.complete(outcome="interested")

        # lead2: 失敗
        lead2.start_calling()
        lead2.fail(reason="no_answer")

        # lead3: まだPENDING

        stats = campaign.get_stats()
        assert stats.total_leads == 3
        assert stats.pending_leads == 1
        assert stats.completed_leads == 1
        assert stats.failed_leads == 1

    def test_abandon_rate_calculation(self):
        """放棄率の計算"""
        stats = CampaignStats(
            total_leads=100,
            completed_leads=50,
            connected_leads=48,
            abandoned_leads=2,
        )
        # 放棄率 = 放棄数 / (接続数 + 放棄数)
        assert stats.abandon_rate == pytest.approx(0.04)  # 2 / 50 = 4%

    def test_abandon_rate_zero_when_no_calls(self):
        """通話がない場合は放棄率0"""
        stats = CampaignStats(total_leads=100)
        assert stats.abandon_rate == 0.0


class TestCampaignDialRatio:
    """Tests for dial ratio management."""

    def test_dial_ratio_must_be_positive(self):
        """ダイヤル比率は正の数"""
        with pytest.raises(ValueError):
            Campaign(name="テスト", dial_ratio=0)

        with pytest.raises(ValueError):
            Campaign(name="テスト", dial_ratio=-1)

    def test_can_update_dial_ratio_on_running_campaign(self):
        """RUNNINGでもダイヤル比率を更新できる"""
        campaign = Campaign(name="テスト")
        campaign.add_lead(Lead(phone_number="+818011112222"))
        campaign.start()

        campaign.update_dial_ratio(2.0)
        assert campaign.dial_ratio == 2.0
