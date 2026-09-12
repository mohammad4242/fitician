import type { QuotaStatus } from "@fitician/core/entitlements";

import { Notice } from "../ui/components";
import {
  bodyAnalysisAccessMessage,
  type BodyAnalysisAccessState,
} from "./bodyAnalysisAccess";

export function BodyAnalysisAccessNotice({
  quota,
  state,
}: {
  readonly quota: QuotaStatus | null;
  readonly state: BodyAnalysisAccessState;
}) {
  if (state === "allowed") return null;
  return (
    <Notice
      message={bodyAnalysisAccessMessage(state, quota)}
      title={state === "quota_exhausted" ? "سهم تحلیل بدن فعلاً تمام شده" : "تحلیل بدن در دسترس نیست"}
      variant={state === "loading" ? "info" : "warning"}
    />
  );
}
