/**
 * OperatorList component tests
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { OperatorList } from "../../src/components/dashboard/OperatorList";
import type { Operator } from "../../src/types";

describe("OperatorList", () => {
  const mockOperators: Operator[] = [
    {
      id: "op-1",
      name: "山田太郎",
      status: "available",
      current_call_sid: null,
      idle_duration_seconds: 120,
      calls_handled: 15,
    },
    {
      id: "op-2",
      name: "鈴木花子",
      status: "on_call",
      current_call_sid: "CA123",
      idle_duration_seconds: 0,
      calls_handled: 23,
    },
    {
      id: "op-3",
      name: "佐藤次郎",
      status: "on_break",
      current_call_sid: null,
      idle_duration_seconds: 300,
      calls_handled: 10,
    },
    {
      id: "op-4",
      name: "田中美咲",
      status: "offline",
      current_call_sid: null,
      idle_duration_seconds: 0,
      calls_handled: 5,
    },
  ];

  it("shows loading state", () => {
    render(<OperatorList operators={[]} isLoading={true} />);

    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows empty state when no operators", () => {
    render(<OperatorList operators={[]} />);
    expect(screen.getByText("オペレーターがいません")).toBeInTheDocument();
  });

  it("displays all operators", () => {
    render(<OperatorList operators={mockOperators} />);

    expect(screen.getByText("山田太郎")).toBeInTheDocument();
    expect(screen.getByText("鈴木花子")).toBeInTheDocument();
    expect(screen.getByText("佐藤次郎")).toBeInTheDocument();
    expect(screen.getByText("田中美咲")).toBeInTheDocument();
  });

  it("displays operator status labels", () => {
    render(<OperatorList operators={mockOperators} />);

    expect(screen.getByText("対応可能")).toBeInTheDocument();
    expect(screen.getByText("通話中")).toBeInTheDocument();
    expect(screen.getByText("休憩中")).toBeInTheDocument();
    expect(screen.getByText("オフライン")).toBeInTheDocument();
  });

  it("displays header with counts", () => {
    render(<OperatorList operators={mockOperators} />);

    expect(screen.getByText("オペレーター一覧")).toBeInTheDocument();
    expect(screen.getByText("対応可能:")).toBeInTheDocument();
    expect(screen.getByText("通話中:")).toBeInTheDocument();
  });

  it("shows correct available count", () => {
    render(<OperatorList operators={mockOperators} />);

    // 1 operator is available - text is "対応可能: 1"
    expect(screen.getByText(/対応可能:/).textContent).toContain("1");
  });

  it("shows correct on_call count", () => {
    render(<OperatorList operators={mockOperators} />);

    // 1 operator is on_call - text is "通話中: 1"
    expect(screen.getByText(/通話中:/).textContent).toContain("1");
  });

  it("displays idle duration for available operators", () => {
    render(<OperatorList operators={mockOperators} />);
    expect(screen.getByText("待機: 2分")).toBeInTheDocument();
  });

  it("displays calls handled count", () => {
    render(<OperatorList operators={mockOperators} />);

    expect(screen.getByText("15件対応")).toBeInTheDocument();
    expect(screen.getByText("23件対応")).toBeInTheDocument();
    expect(screen.getByText("10件対応")).toBeInTheDocument();
    expect(screen.getByText("5件対応")).toBeInTheDocument();
  });

  it("sorts operators by status priority", () => {
    render(<OperatorList operators={mockOperators} />);

    const operatorNames = screen.getAllByText(/太郎|花子|次郎|美咲/);

    // Expected order: on_call > available > on_break > offline
    expect(operatorNames[0].textContent).toBe("鈴木花子"); // on_call
    expect(operatorNames[1].textContent).toBe("山田太郎"); // available
    expect(operatorNames[2].textContent).toBe("佐藤次郎"); // on_break
    expect(operatorNames[3].textContent).toBe("田中美咲"); // offline
  });

  it("displays avatar with first letter of name", () => {
    render(<OperatorList operators={mockOperators} />);

    // Check for avatar initials
    expect(screen.getByText("山")).toBeInTheDocument();
    expect(screen.getByText("鈴")).toBeInTheDocument();
    expect(screen.getByText("佐")).toBeInTheDocument();
    expect(screen.getByText("田")).toBeInTheDocument();
  });

  it("shows 通話中... for operators on call", () => {
    render(<OperatorList operators={mockOperators} />);
    expect(screen.getByText("通話中...")).toBeInTheDocument();
  });
});
