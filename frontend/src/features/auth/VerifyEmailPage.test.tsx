import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import { ApiError } from "@fitician/core";

import i18n from "../../i18n";
import * as api from "./api";
import { VerifyEmailPage } from "./VerifyEmailPage";

vi.mock("./api");

beforeEach(async () => {
  vi.clearAllMocks();
  await i18n.changeLanguage("fa");
});

it("presents the backend verification failure through the shared resolver", async () => {
  vi.mocked(api.verifyEmail).mockRejectedValueOnce(
    new ApiError(503, "private verification provider detail", null, "SERVICE_UNAVAILABLE", {
      requestId: "verify-email-1",
    }),
  );

  render(
    <MemoryRouter initialEntries={["/verify-email?token=token-1"]}>
      <VerifyEmailPage />
    </MemoryRouter>,
  );

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("سرویس موقتاً در دسترس نیست");
  expect(alert).not.toHaveTextContent("private verification provider detail");
  expect(alert).not.toHaveTextContent("verify-email-1");
});
