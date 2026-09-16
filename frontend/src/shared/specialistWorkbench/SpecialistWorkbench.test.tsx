import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, expect, it, vi } from "vitest";

import {
  SpecialistCaseList,
  SpecialistCaseTabs,
  SpecialistStatusBadge,
  SpecialistWorkbenchNav,
  SpecialistWorkbenchShell,
} from "./index";
import type { SpecialistSection } from "./types";

beforeEach(() => {
  vi.clearAllMocks();
});

it("provides four accessible workbench sections and changes the active section", async () => {
  const user = userEvent.setup();

  function Harness() {
    const [activeSection, setActiveSection] = useState<SpecialistSection>("dashboard");
    return (
      <SpecialistWorkbenchShell
        activeSection={activeSection}
        fa
        onSectionChange={setActiveSection}
        role="coach"
        title="میز کار مربی"
      >
        <p>{activeSection}</p>
      </SpecialistWorkbenchShell>
    );
  }

  render(<Harness />);

  expect(screen.getByRole("tablist", { name: "بخش‌های میز کار" })).toBeInTheDocument();
  expect(screen.getAllByRole("tab")).toHaveLength(4);
  expect(screen.getByRole("tab", { name: "داشبورد" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByText("dashboard")).toBeInTheDocument();

  await user.click(screen.getByRole("tab", { name: "صف بررسی" }));

  expect(screen.getByRole("tab", { name: "صف بررسی" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByText("queue")).toBeInTheDocument();
});

it("localizes status labels by specialist context without exposing raw status", () => {
  render(
    <>
      <SpecialistStatusBadge context="coach" fa status="rejected" />
      <SpecialistStatusBadge context="physician" fa status="rejected" />
      <SpecialistStatusBadge context="physician" fa status="in_review" />
      <SpecialistStatusBadge context="physician" fa status="unexpected_internal_value" />
    </>,
  );

  expect(screen.getByText("برگشت برای اصلاح")).toBeInTheDocument();
  expect(screen.getByText("ردشده")).toBeInTheDocument();
  expect(screen.getByText("در حال بررسی")).toBeInTheDocument();
  expect(screen.getByText("وضعیت پرونده")).toBeInTheDocument();
  expect(screen.queryByText("in_review")).not.toBeInTheDocument();
  expect(screen.queryByText("unexpected_internal_value")).not.toBeInTheDocument();
});

it("renders an RTL compact case list and an explicit empty state", () => {
  render(
    <div dir="rtl">
      <SpecialistCaseList
        emptyDescription="پرونده جدیدی برای نمایش وجود ندارد."
        emptyTitle="صف خالی است"
        fa
        items={[]}
        renderItem={() => null}
        searchLabel="جست‌وجوی نام کاربر"
        searchValue=""
        sortLabel="مرتب‌سازی"
        sortOptions={[{ label: "جدیدترین", value: "newest" }]}
        sortValue="newest"
        onSearchChange={vi.fn()}
        onSortChange={vi.fn()}
      />
    </div>,
  );

  expect(screen.getByText("صف خالی است")).toBeInTheDocument();
  expect(screen.getByText("پرونده جدیدی برای نمایش وجود ندارد.")).toBeInTheDocument();
  expect(screen.getByLabelText("جست‌وجوی نام کاربر")).toBeInTheDocument();
  expect(screen.getByRole("combobox", { name: "مرتب‌سازی" })).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "پرونده‌ها" })).toHaveAttribute("dir", "rtl");
});

it("renders case rows through the shared list contract", () => {
  render(
    <SpecialistCaseList
      emptyDescription=""
      emptyTitle=""
      items={[{ id: "case-1", name: "محمد" }]}
      renderItem={(item) => <li key={item.id}>{item.name}</li>}
      searchLabel="Search"
      searchValue=""
      sortLabel="Sort"
      sortOptions={[{ label: "Newest", value: "newest" }]}
      sortValue="newest"
      onSearchChange={vi.fn()}
      onSortChange={vi.fn()}
    />,
  );

  expect(screen.getByText("محمد")).toBeInTheDocument();
});

it("exports the navigation primitive as a shared component", () => {
  render(
    <SpecialistWorkbenchNav
      activeSection="history"
      fa={false}
      onSectionChange={vi.fn()}
      role="physician"
    />,
  );

  expect(screen.getByRole("tab", { name: "History" })).toHaveAttribute("aria-selected", "true");
});

it("supports arrow-key navigation for case tabs", async () => {
  const user = userEvent.setup();

  function Harness() {
    const [activeTab, setActiveTab] = useState("summary");
    return (
      <>
        <SpecialistCaseTabs
          activeTab={activeTab}
          ariaLabel="Case sections"
          fa={false}
          onChange={setActiveTab}
          panelIdPrefix="case-panel"
          tabIdPrefix="case-tab"
          tabs={[
            { id: "summary", label: "Summary" },
            { id: "plan", label: "Plan" },
            { id: "notes", label: "Notes" },
          ]}
        />
        <p>{activeTab}</p>
      </>
    );
  }

  render(<Harness />);
  const summaryTab = screen.getByRole("tab", { name: "Summary" });
  summaryTab.focus();
  await user.keyboard("{ArrowRight}");

  expect(screen.getByRole("tab", { name: "Plan" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByText("plan")).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Plan" })).toHaveFocus();
});
