/**
 * StatusToggle component tests
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StatusToggle } from "../../src/components/operator/StatusToggle";

describe("StatusToggle", () => {
  it("displays current status label", () => {
    render(
      <StatusToggle currentStatus="available" onStatusChange={() => {}} />
    );
    expect(screen.getByText("対応可能")).toBeInTheDocument();
  });

  it("displays offline status correctly", () => {
    render(
      <StatusToggle currentStatus="offline" onStatusChange={() => {}} />
    );
    expect(screen.getByText("オフライン")).toBeInTheDocument();
  });

  it("displays on_break status correctly", () => {
    render(
      <StatusToggle currentStatus="on_break" onStatusChange={() => {}} />
    );
    expect(screen.getByText("休憩中")).toBeInTheDocument();
  });

  it("opens dropdown menu when clicked", () => {
    render(
      <StatusToggle currentStatus="available" onStatusChange={() => {}} />
    );

    // Click the toggle button
    fireEvent.click(screen.getByRole("button"));

    // Should see all selectable options
    expect(screen.getByRole("listbox")).toBeInTheDocument();
    expect(screen.getAllByRole("option")).toHaveLength(3);
  });

  it("calls onStatusChange when a different status is selected", () => {
    const onStatusChange = vi.fn();
    render(
      <StatusToggle currentStatus="available" onStatusChange={onStatusChange} />
    );

    // Open menu
    fireEvent.click(screen.getByRole("button"));

    // Select "休憩中"
    fireEvent.click(screen.getByText("休憩中"));

    expect(onStatusChange).toHaveBeenCalledWith("on_break");
  });

  it("does not allow changing status when on_call", () => {
    const onStatusChange = vi.fn();
    render(
      <StatusToggle currentStatus="on_call" onStatusChange={onStatusChange} />
    );

    // Button should be disabled or not open menu
    const button = screen.getByRole("button");
    fireEvent.click(button);

    // Should not show dropdown
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("does not allow changing status when wrap_up", () => {
    render(
      <StatusToggle currentStatus="wrap_up" onStatusChange={() => {}} />
    );

    fireEvent.click(screen.getByRole("button"));
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("is disabled when disabled prop is true", () => {
    render(
      <StatusToggle
        currentStatus="available"
        onStatusChange={() => {}}
        disabled={true}
      />
    );

    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
  });
});
