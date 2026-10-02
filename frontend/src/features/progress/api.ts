import { createProgressApi } from "@fitician/core";
import { request } from "../../shared/apiClient";
export const progressApi = createProgressApi((input) =>
  request(input.path, {
    method: input.method,
    body: input.body === undefined ? undefined : JSON.stringify(input.body),
  }),
);
