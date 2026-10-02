import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, it, vi } from "vitest";
import { AdminSupportPage } from "./AdminSupportPage";
const mocks = vi.hoisted(() => ({
  list: vi.fn(),
  detail: vi.fn(),
  status: vi.fn(),
  read: vi.fn(),
}));
vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({ user: { id: "admin", is_admin: true } }),
}));
vi.mock("./api", () => ({ adminSupportApi: mocks }));
it("shows open count and filters the support-only queue", async () => {
  mocks.list.mockResolvedValue({
    items: [],
    open_count: 3,
    older_cursor: null,
  });
  render(
    <MemoryRouter>
      <AdminSupportPage />
    </MemoryRouter>,
  );
  expect(await screen.findByText("3")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("وضعیت"), {
    target: { value: "awaiting_user" },
  });
  await waitFor(() =>
    expect(mocks.list).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: "awaiting_user" }),
    ),
  );
  expect(screen.queryByText("اطلاعات پزشکی")).not.toBeInTheDocument();
});
