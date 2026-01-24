"""Dialer orchestrator - predictive dialing algorithm."""

from dataclasses import dataclass
from typing import Any

from app.models.campaign import Campaign, CampaignStats, CampaignStatus
from app.models.lead import Lead


@dataclass
class DialerConfig:
    """Configuration for the dialer orchestrator."""

    base_dial_ratio: float = 3.0
    min_dial_ratio: float = 1.0
    max_dial_ratio: float = 5.0
    target_abandon_rate: float = 0.03  # 3%


class DialerOrchestrator:
    """
    Predictive dialer orchestrator.

    Manages the predictive dialing algorithm that determines:
    - How many calls to make based on available operators
    - Dynamic adjustment of dial ratio based on abandon rate
    - Which leads to call next

    The goal is to maximize operator utilization while keeping
    the abandon rate below the target (typically 3% for compliance).
    """

    def __init__(
        self,
        base_dial_ratio: float = 3.0,
        min_dial_ratio: float = 1.0,
        max_dial_ratio: float = 5.0,
        target_abandon_rate: float = 0.03,
    ):
        """
        Initialize the orchestrator.

        Args:
            base_dial_ratio: Starting dial ratio (calls per operator)
            min_dial_ratio: Minimum allowed dial ratio
            max_dial_ratio: Maximum allowed dial ratio
            target_abandon_rate: Target abandon rate (0.03 = 3%)
        """
        self.base_dial_ratio = base_dial_ratio
        self.min_dial_ratio = min_dial_ratio
        self.max_dial_ratio = max_dial_ratio
        self.target_abandon_rate = target_abandon_rate

    def calculate_dial_ratio(self, stats: CampaignStats) -> float:
        """
        Calculate the optimal dial ratio based on current stats.

        Uses a simple proportional control algorithm:
        - If abandon rate > target: decrease ratio
        - If abandon rate < target: increase ratio

        Args:
            stats: Current campaign statistics

        Returns:
            Calculated dial ratio
        """
        current_abandon_rate = stats.abandon_rate

        # No data yet, use base ratio
        total_calls = stats.connected_leads + stats.abandoned_leads
        if total_calls < 10:
            return self.base_dial_ratio

        # Calculate adjustment factor
        # If abandon rate is at target, factor = 1.0
        # If abandon rate is higher, factor < 1.0 (reduce calls)
        # If abandon rate is lower, factor > 1.0 (increase calls)
        if current_abandon_rate > 0:
            # Proportional adjustment
            error = self.target_abandon_rate - current_abandon_rate
            # Scale factor: small adjustments to avoid oscillation
            adjustment = 1.0 + (error * 10)  # 10x sensitivity
        else:
            # No abandons, can increase slightly
            adjustment = 1.1

        # Apply adjustment to base ratio
        new_ratio = self.base_dial_ratio * adjustment

        # Clamp to min/max bounds
        return max(self.min_dial_ratio, min(self.max_dial_ratio, new_ratio))

    def calculate_calls_to_make(
        self,
        available_operators: int,
        dial_ratio: float,
        pending_calls: int,
    ) -> int:
        """
        Calculate how many new calls to initiate.

        Args:
            available_operators: Number of operators waiting for calls
            dial_ratio: Current dial ratio
            pending_calls: Number of calls already in progress

        Returns:
            Number of new calls to make
        """
        if available_operators <= 0:
            return 0

        # Target number of concurrent calls
        target_calls = int(available_operators * dial_ratio)

        # Subtract already pending calls
        calls_needed = target_calls - pending_calls

        # Never return negative
        return max(0, calls_needed)

    def get_leads_to_dial(
        self,
        campaign: Campaign,
        available_operators: int,
        pending_calls: int,
    ) -> list[Lead]:
        """
        Get the list of leads to dial now.

        Args:
            campaign: The campaign to get leads from
            available_operators: Number of available operators
            pending_calls: Number of calls already in progress

        Returns:
            List of leads to call
        """
        # Only dial for running campaigns
        if campaign.status != CampaignStatus.RUNNING:
            return []

        # Calculate how many calls to make
        stats = campaign.get_stats()
        dial_ratio = self.calculate_dial_ratio(stats)

        # Use campaign's configured ratio if different
        effective_ratio = min(dial_ratio, campaign.dial_ratio)

        calls_to_make = self.calculate_calls_to_make(
            available_operators=available_operators,
            dial_ratio=effective_ratio,
            pending_calls=pending_calls,
        )

        if calls_to_make <= 0:
            return []

        # Get callable leads from campaign
        return campaign.get_callable_leads(calls_to_make)

    def should_pause_dialing(self, stats: CampaignStats) -> bool:
        """
        Check if dialing should be paused due to high abandon rate.

        Args:
            stats: Current campaign statistics

        Returns:
            True if dialing should be paused
        """
        # Pause if abandon rate exceeds 2x target
        return stats.abandon_rate > (self.target_abandon_rate * 2)

    def get_dialing_health(self, stats: CampaignStats) -> dict[str, Any]:
        """
        Get health metrics for the dialing operation.

        Args:
            stats: Current campaign statistics

        Returns:
            Dictionary with health metrics
        """
        abandon_rate = stats.abandon_rate
        target = self.target_abandon_rate

        if abandon_rate <= target:
            status = "healthy"
        elif abandon_rate <= target * 1.5:
            status = "warning"
        else:
            status = "critical"

        return {
            "status": status,
            "current_abandon_rate": abandon_rate,
            "target_abandon_rate": target,
            "recommended_dial_ratio": self.calculate_dial_ratio(stats),
        }
