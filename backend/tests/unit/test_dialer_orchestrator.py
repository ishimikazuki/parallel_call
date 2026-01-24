"""Unit tests for DialerOrchestrator."""


from app.models.campaign import Campaign, CampaignStats
from app.models.lead import Lead
from app.services.dialer_orchestrator import DialerOrchestrator


class TestDialRatioCalculation:
    """Tests for dial ratio calculation."""

    def test_base_dial_ratio_is_3(self):
        """基本ダイヤル比率は3.0（データ少ない時）"""
        orchestrator = DialerOrchestrator()
        # データが少ない場合は基本比率を返す
        stats = CampaignStats(connected_leads=5, abandoned_leads=0)
        assert orchestrator.calculate_dial_ratio(stats) == 3.0

    def test_reduces_ratio_when_abandon_rate_high(self):
        """放棄率が高いとダイヤル比率を下げる"""
        orchestrator = DialerOrchestrator()
        stats = CampaignStats(
            connected_leads=94,
            abandoned_leads=6,  # 6% 放棄率
        )
        ratio = orchestrator.calculate_dial_ratio(stats)
        assert ratio < 3.0

    def test_increases_ratio_when_abandon_rate_very_low(self):
        """放棄率が非常に低いとダイヤル比率を上げる"""
        orchestrator = DialerOrchestrator()
        stats = CampaignStats(
            connected_leads=100,
            abandoned_leads=0,  # 0% 放棄率
        )
        ratio = orchestrator.calculate_dial_ratio(stats)
        assert ratio > 3.0

    def test_ratio_never_below_minimum(self):
        """ダイヤル比率は最小値(1.0)を下回らない"""
        orchestrator = DialerOrchestrator()
        stats = CampaignStats(
            connected_leads=50,
            abandoned_leads=50,  # 50% 放棄率（異常値）
        )
        ratio = orchestrator.calculate_dial_ratio(stats)
        assert ratio >= 1.0

    def test_ratio_never_above_maximum(self):
        """ダイヤル比率は最大値(5.0)を超えない"""
        orchestrator = DialerOrchestrator()
        stats = CampaignStats(
            connected_leads=1000,
            abandoned_leads=0,
        )
        ratio = orchestrator.calculate_dial_ratio(stats)
        assert ratio <= 5.0


class TestCallsToMakeCalculation:
    """Tests for calculating number of calls to make."""

    def test_calculates_calls_based_on_available_operators(self):
        """待機オペレーター数に基づいて発信数を計算"""
        orchestrator = DialerOrchestrator()

        # 3人待機、ダイヤル比率3.0 → 9発信
        calls = orchestrator.calculate_calls_to_make(
            available_operators=3,
            dial_ratio=3.0,
            pending_calls=0,
        )
        assert calls == 9

    def test_subtracts_pending_calls(self):
        """進行中の発信を差し引く"""
        orchestrator = DialerOrchestrator()

        # 3人待機、ダイヤル比率3.0、進行中5発信 → 4発信
        calls = orchestrator.calculate_calls_to_make(
            available_operators=3,
            dial_ratio=3.0,
            pending_calls=5,
        )
        assert calls == 4

    def test_returns_zero_when_no_available_operators(self):
        """待機オペレーターがいなければ0"""
        orchestrator = DialerOrchestrator()

        calls = orchestrator.calculate_calls_to_make(
            available_operators=0,
            dial_ratio=3.0,
            pending_calls=0,
        )
        assert calls == 0

    def test_returns_zero_when_enough_pending(self):
        """十分な進行中発信があれば0"""
        orchestrator = DialerOrchestrator()

        calls = orchestrator.calculate_calls_to_make(
            available_operators=3,
            dial_ratio=3.0,
            pending_calls=10,
        )
        assert calls == 0

    def test_never_returns_negative(self):
        """マイナスにならない"""
        orchestrator = DialerOrchestrator()

        calls = orchestrator.calculate_calls_to_make(
            available_operators=1,
            dial_ratio=2.0,
            pending_calls=100,
        )
        assert calls >= 0


class TestDialingStrategy:
    """Tests for overall dialing strategy."""

    def test_get_leads_to_dial_respects_campaign_ratio(self):
        """キャンペーンのダイヤル比率を尊重"""
        orchestrator = DialerOrchestrator()

        campaign = Campaign(name="テスト", dial_ratio=2.0)
        for i in range(10):
            campaign.add_lead(Lead(phone_number=f"+8180{i:08d}"))
        campaign.start()

        leads = orchestrator.get_leads_to_dial(
            campaign=campaign,
            available_operators=2,
            pending_calls=0,
        )
        # 2人 × 2.0 = 4件
        assert len(leads) == 4

    def test_get_leads_to_dial_limited_by_available_leads(self):
        """利用可能なリード数で制限"""
        orchestrator = DialerOrchestrator()

        campaign = Campaign(name="テスト", dial_ratio=3.0)
        campaign.add_lead(Lead(phone_number="+818011112222"))
        campaign.add_lead(Lead(phone_number="+818033334444"))
        campaign.start()

        leads = orchestrator.get_leads_to_dial(
            campaign=campaign,
            available_operators=5,  # 多くのオペレーター
            pending_calls=0,
        )
        # リードが2件しかないので2件
        assert len(leads) == 2

    def test_get_leads_to_dial_returns_empty_for_paused_campaign(self):
        """一時停止中のキャンペーンには空"""
        orchestrator = DialerOrchestrator()

        campaign = Campaign(name="テスト")
        campaign.add_lead(Lead(phone_number="+818011112222"))
        campaign.start()
        campaign.pause()

        leads = orchestrator.get_leads_to_dial(
            campaign=campaign,
            available_operators=3,
            pending_calls=0,
        )
        assert len(leads) == 0


class TestAbandonRateTargets:
    """Tests for abandon rate target management."""

    def test_default_target_abandon_rate(self):
        """デフォルトの目標放棄率は3%"""
        orchestrator = DialerOrchestrator()
        assert orchestrator.target_abandon_rate == 0.03

    def test_can_set_custom_target(self):
        """カスタム目標を設定可能"""
        orchestrator = DialerOrchestrator(target_abandon_rate=0.05)
        assert orchestrator.target_abandon_rate == 0.05

    def test_adjustment_factor_based_on_target(self):
        """目標値に基づいて調整係数を計算"""
        orchestrator = DialerOrchestrator(target_abandon_rate=0.03)

        # 放棄率が目標と同じなら調整なし
        stats = CampaignStats(connected_leads=97, abandoned_leads=3)
        ratio = orchestrator.calculate_dial_ratio(stats)
        assert 2.9 <= ratio <= 3.1  # 基本値付近
