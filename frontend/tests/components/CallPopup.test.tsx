/**
 * CallPopup component tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { CallPopup } from "../../src/components/operator/CallPopup";
import type { IncomingCall } from "../../src/types";

describe("CallPopup", () => {
  const mockCall: IncomingCall = {
    call_sid: "CA123",
    lead_id: "lead-1",
    phone_number: "09012345678",
    name: "山田太郎",
  };

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders nothing when call is null", () => {
    const { container } = render(
      <CallPopup call={null} onAccept={() => {}} onReject={() => {}} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("displays call information when call is provided", () => {
    render(
      <CallPopup call={mockCall} onAccept={() => {}} onReject={() => {}} />
    );

    expect(screen.getByText("着信があります")).toBeInTheDocument();
    expect(screen.getByText("090-1234-5678")).toBeInTheDocument();
    expect(screen.getByText("山田太郎")).toBeInTheDocument();
  });

  it("formats phone number correctly", () => {
    render(
      <CallPopup call={mockCall} onAccept={() => {}} onReject={() => {}} />
    );

    // 09012345678 -> 090-1234-5678
    expect(screen.getByText("090-1234-5678")).toBeInTheDocument();
  });

  it("calls onAccept when accept button is clicked", () => {
    const onAccept = vi.fn();
    render(
      <CallPopup call={mockCall} onAccept={onAccept} onReject={() => {}} />
    );

    fireEvent.click(screen.getByText("応答"));
    expect(onAccept).toHaveBeenCalledTimes(1);
  });

  it("calls onReject when reject button is clicked", () => {
    const onReject = vi.fn();
    render(
      <CallPopup call={mockCall} onAccept={() => {}} onReject={onReject} />
    );

    fireEvent.click(screen.getByText("拒否"));
    expect(onReject).toHaveBeenCalledTimes(1);
  });

  it("auto-answers after countdown when autoAnswerSeconds is set", () => {
    const onAccept = vi.fn();
    render(
      <CallPopup
        call={mockCall}
        onAccept={onAccept}
        onReject={() => {}}
        autoAnswerSeconds={3}
      />
    );

    // Should show countdown
    expect(screen.getByText("3秒後に自動応答します")).toBeInTheDocument();

    // Advance timer
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getByText("2秒後に自動応答します")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getByText("1秒後に自動応答します")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    // Should have auto-accepted
    expect(onAccept).toHaveBeenCalledTimes(1);
  });

  it("does not show countdown when autoAnswerSeconds is 0", () => {
    render(
      <CallPopup
        call={mockCall}
        onAccept={() => {}}
        onReject={() => {}}
        autoAnswerSeconds={0}
      />
    );

    expect(screen.queryByText(/秒後に自動応答/)).not.toBeInTheDocument();
  });

  it("handles call without name", () => {
    const callWithoutName: IncomingCall = {
      ...mockCall,
      name: null,
    };
    render(
      <CallPopup call={callWithoutName} onAccept={() => {}} onReject={() => {}} />
    );

    expect(screen.getByText("090-1234-5678")).toBeInTheDocument();
    expect(screen.queryByText("山田太郎")).not.toBeInTheDocument();
  });
});
