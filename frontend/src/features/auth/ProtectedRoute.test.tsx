import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { expect, it, vi } from "vitest";
import "../../i18n";
vi.mock("./AuthContext", () => ({ useAuth: () => ({user: null, loading: false}) }));
import { ProtectedRoute } from "./ProtectedRoute";
function Destination() { const location = useLocation(); return <span>{location.search}</span>; }
it("preserves the untrusted payment token through login without verifying it", async () => {
  render(<MemoryRouter initialEntries={["/billing/checkout-result?token=opaque&status=paid"]}><Routes>
    <Route element={<ProtectedRoute />}><Route path="/billing/checkout-result" element={<span>private</span>} /></Route>
    <Route path="/login" element={<Destination />} />
  </Routes></MemoryRouter>);
  expect(await screen.findByText("?returnTo=%2Fbilling%2Fcheckout-result%3Ftoken%3Dopaque%26status%3Dpaid")).toBeInTheDocument();
});
