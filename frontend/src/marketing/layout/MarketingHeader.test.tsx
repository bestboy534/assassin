import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MarketingHeader } from "./MarketingHeader";

function renderHeader() {
  return render(
    <MemoryRouter>
      <MarketingHeader />
    </MemoryRouter>,
  );
}

test("keeps a mega menu open for two seconds after pointer leaves", () => {
  vi.useFakeTimers();
  renderHeader();
  const trigger = screen.getByRole("button", { name: "为什么选择我们" });

  fireEvent.mouseEnter(trigger);
  expect(screen.getByRole("link", { name: /财务团队/ })).toBeVisible();
  fireEvent.mouseLeave(trigger.parentElement!);

  act(() => {
    vi.advanceTimersByTime(1000);
  });
  expect(screen.getByRole("link", { name: /财务团队/ })).toBeVisible();
  act(() => {
    vi.advanceTimersByTime(1100);
  });
  expect(screen.queryByRole("link", { name: /财务团队/ })).not.toBeInTheDocument();
  vi.useRealTimers();
});

test("entering the menu cancels delayed closing", () => {
  vi.useFakeTimers();
  renderHeader();
  const trigger = screen.getByRole("button", { name: "为什么选择我们" });

  fireEvent.mouseEnter(trigger);
  fireEvent.mouseLeave(trigger.parentElement!);
  fireEvent.mouseEnter(screen.getByRole("link", { name: /财务团队/ }).closest(".mega-menu")!);
  act(() => {
    vi.advanceTimersByTime(2100);
  });

  expect(screen.getByRole("link", { name: /财务团队/ })).toBeVisible();
  vi.useRealTimers();
});

test("supports aria controls, focus opening, and Escape closing", () => {
  renderHeader();
  const trigger = screen.getByRole("button", { name: "解决方案" });

  fireEvent.focus(trigger);
  expect(trigger).toHaveAttribute("aria-expanded", "true");
  expect(trigger).toHaveAttribute("aria-controls");
  fireEvent.keyDown(trigger, { key: "Escape" });
  expect(trigger).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByRole("link", { name: /审批和采购/ })).not.toBeInTheDocument();
});
