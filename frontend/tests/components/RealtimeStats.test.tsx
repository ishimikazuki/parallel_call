/**
 * RealtimeStats component tests
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RealtimeStats } from "../../src/components/dashboard/RealtimeStats";
import type { CampaignStats } from "../../src/types";

describe("RealtimeStats", () => {
  const mockStats: CampaignStats = {
    total_leads: 1000,
    pending_leads: 500,
    calling_leads: 50,
    connected_leads: 30,
    completed_leads: 300,
    failed_leads: 100,
    dnc_leads: 20,
    abandon_rate: 0.02,
  };

  it("shows loading state", () => {
    render(<RealtimeStats stats={null} isLoading={true} />);

    // Should show skeleton loading
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows empty state when stats is null", () => {
    render(<RealtimeStats stats={null} />);
    expect(screen.getByText("キャンペーンを選択してください")).toBeInTheDocument();
  });

  it("displays all stat values", () => {
    render(<RealtimeStats stats={mockStats} />);

    expect(screen.getByText("1,000")).toBeInTheDocument(); // total_leads
    expect(screen.getByText("500")).toBeInTheDocument(); // pending_leads
    expect(screen.getByText("50")).toBeInTheDocument(); // calling_leads
    expect(screen.getByText("30")).toBeInTheDocument(); // connected_leads
    expect(screen.getByText("300")).toBeInTheDocument(); // completed_leads
    expect(screen.getByText("100")).toBeInTheDocument(); // failed_leads
    expect(screen.getByText("20")).toBeInTheDocument(); // dnc_leads
  });

  it("displays abandon rate as percentage", () => {
    render(<RealtimeStats stats={mockStats} />);
    expect(screen.getByText("2.0%")).toBeInTheDocument();
  });

  it("shows green color for low abandon rate", () => {
    const lowAbandonStats = { ...mockStats, abandon_rate: 0.02 };
    render(<RealtimeStats stats={lowAbandonStats} />);

    const abandonRateElement = screen.getByText("2.0%");
    expect(abandonRateElement).toHaveClass("text-green-600");
  });

  it("shows red color for high abandon rate", () => {
    const highAbandonStats = { ...mockStats, abandon_rate: 0.08 };
    render(<RealtimeStats stats={highAbandonStats} />);

    const abandonRateElement = screen.getByText("8.0%");
    expect(abandonRateElement).toHaveClass("text-red-600");
  });

  it("displays campaign name when provided", () => {
    render(<RealtimeStats stats={mockStats} campaignName="テストキャンペーン" />);
    expect(screen.getByText("テストキャンペーン")).toBeInTheDocument();
  });

  it("displays all stat labels", () => {
    render(<RealtimeStats stats={mockStats} />);

    expect(screen.getByText("総リード数")).toBeInTheDocument();
    expect(screen.getByText("待機中")).toBeInTheDocument();
    expect(screen.getByText("発信中")).toBeInTheDocument();
    expect(screen.getByText("通話中")).toBeInTheDocument();
    expect(screen.getByText("完了")).toBeInTheDocument();
    expect(screen.getByText("失敗")).toBeInTheDocument();
    expect(screen.getByText("DNC")).toBeInTheDocument();
    expect(screen.getByText("放棄率")).toBeInTheDocument();
  });

  it("shows abandon rate target hint", () => {
    render(<RealtimeStats stats={mockStats} />);
    expect(screen.getByText("目標: 3%以下")).toBeInTheDocument();
  });
});
