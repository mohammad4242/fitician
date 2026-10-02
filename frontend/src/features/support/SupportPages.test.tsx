import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { HelpCenterPage, NewTicketPage, SupportTicketPage, MyTicketsPage } from "./SupportPages";

const mocks = vi.hoisted(() => ({ user: null as null | { id: string }, create: vi.fn(), list: vi.fn(), detail: vi.fn(), reply: vi.fn(), read: vi.fn() }));
vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ user: mocks.user }) }));
vi.mock("./api", () => ({ supportApi: mocks }));
const ticket = { id: "ticket", user_id: "member", category: "account", subject: "Login help", status: "open", created_at: "2026-10-01T10:00:00Z", last_activity_at: "2026-10-01T10:00:00Z" };
function mount(element: React.ReactNode, path = "/support") { return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/support" element={element} /><Route path="/support/tickets/:ticketId" element={element} /><Route path="/support/tickets" element={element} /><Route path="/support/new" element={element} /></Routes></MemoryRouter>); }
beforeEach(() => { vi.clearAllMocks(); mocks.user = null; mocks.read.mockResolvedValue(undefined); });
it("renders public searchable help with no authenticated ticket calls", async () => {
  mount(<HelpCenterPage />);
  expect(screen.getByRole("heading", { name: "چطور می‌تونیم کمکت کنیم؟" })).toBeInTheDocument();
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "ورود" } });
  expect(screen.getByText("نمی‌توانم وارد حسابم شوم")).toBeInTheDocument();
  expect(mocks.list).not.toHaveBeenCalled();
});
it("renders a useful empty ticket list", async () => {
  mocks.user = { id: "member" }; mocks.list.mockResolvedValue({ items: [], older_cursor: null });
  mount(<MyTicketsPage />, "/support/tickets");
  expect(await screen.findByText("هنوز درخواستی ثبت نکرده‌ای")).toBeInTheDocument();
});
it("keeps form request id for a failed submission retry", async () => {
  mocks.user = { id: "member" }; mocks.create.mockRejectedValue(new Error("offline"));
  mount(<NewTicketPage />, "/support/new");
  fireEvent.change(screen.getByLabelText("موضوع"), { target: { value: "Help" } });
  fireEvent.change(screen.getByLabelText("توضیحات"), { target: { value: "Question" } });
  fireEvent.click(screen.getByRole("button", { name: "ارسال درخواست" }));
  await waitFor(() => expect(mocks.create).toHaveBeenCalledTimes(1));
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: "ارسال درخواست" }));
  await waitFor(() => expect(mocks.create).toHaveBeenCalledTimes(2));
  expect(mocks.create.mock.calls[0][0].request_id).toEqual(mocks.create.mock.calls[1][0].request_id);
});
it("renders closed tickets without a reply composer", async () => {
  mocks.user = { id: "member" }; mocks.detail.mockResolvedValue({ ticket: { ...ticket, status: "closed" }, viewer_id: "member", messages: [{ id: "message", body: "Resolved", sender_role: "admin", sender_id: "admin", created_at: ticket.created_at }], unread_count: 1, older_cursor: null });
  mount(<SupportTicketPage />, "/support/tickets/ticket");
  expect(await screen.findByText("Resolved")).toBeInTheDocument();
  expect(screen.queryByLabelText("متن پیام")).not.toBeInTheDocument();
});
it("shows approved public contacts and never requests anonymous tickets", () => {
 mount(<HelpCenterPage />);
 expect(screen.getByRole('link', {name:'fitician.fit@gmail.com'})).toHaveAttribute('href','mailto:fitician.fit@gmail.com');
 expect(screen.getByRole('link', {name:/@fitician.fit/})).toHaveAttribute('href','https://www.instagram.com/fitician.fit/');
 expect(mocks.list).not.toHaveBeenCalled();
});
