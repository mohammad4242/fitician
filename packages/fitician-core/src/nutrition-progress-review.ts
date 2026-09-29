import type { components } from "./generated/api.js";
import type { TransportRequest } from "./transport.js";
export type NutritionProgressReview = components["schemas"]["NutritionProgressReviewResponse"];
export type NutritionProgressConfirmation = components["schemas"]["NutritionProgressConfirmationResponse"];
export type NutritionProgressRequest = <T>(input: TransportRequest) => Promise<T>;
const statuses = ["insufficient_data", "continue", "improve_adherence", "adjustment_available", "specialist_review", "cooldown", "new_plan_required"];
export function createNutritionProgressApi(request: NutritionProgressRequest) {
  return {
    async review(): Promise<NutritionProgressReview> {
      const result = await request<NutritionProgressReview>({ path: "/api/v1/nutrition/progress-review", method: "GET" });
      if (!result || !statuses.includes(result.status) || !Array.isArray(result.reason_codes) || typeof result.can_confirm !== "boolean" || typeof result.start !== "string" || typeof result.end !== "string" || !Number.isFinite(Date.parse(result.start)) || !Number.isFinite(Date.parse(result.end))) throw new Error("Invalid progress review response");
      return result;
    },
    async confirm(review: NutritionProgressReview): Promise<NutritionProgressConfirmation> {
      if (!review.can_confirm || !review.plan_id || !review.signature) throw new Error("No available proposal");
      const result = await request<NutritionProgressConfirmation>({ path: "/api/v1/nutrition/progress-review/confirm", method: "POST", body: { expected_plan_id: review.plan_id, signature: review.signature, confirmed: true } });
      if (!result?.estimate_id || result.targets_updated !== true) throw new Error("Invalid confirmation response");
      return result;
    },
  };
}
export function nutritionProgressCopy(status: NutritionProgressReview["status"], english: boolean): string {
  const copy = {
    insufficient_data: ["برای تصمیم‌گیری داده کافی نداریم. حداقل ۱۴ روز کامل ثبت تغذیه و ۴ روز اندازه‌گیری وزن در دو نیمهٔ بازه، با فاصلهٔ حداقل ۱۴ روز لازم است؛ آخرین وزن باید مربوط به هفتهٔ اخیر باشد.", "Not enough data: record at least 14 complete nutrition days and weigh on four distinct days across both halves, spanning at least 14 days, with a measurement in the last week."],
    continue: ["فعلاً برنامه را ادامه بده. روند مشاهده‌شده نیاز به تغییر خودکار هدف نشان نمی‌دهد.", "Continue the plan. The observed trend does not indicate an automatic target change."],
    improve_adherence: ["ابتدا رعایت برنامه و کامل‌بودن ثبت‌ها را بررسی کن؛ کاهش یا افزایش هدف فعلاً پیشنهاد نمی‌شود.", "Review adherence and complete your records first; a target adjustment is not proposed yet."],
    adjustment_available: ["با توجه به روند وزن و ثبت‌های تغذیه، یک اصلاح کوچک در هدف پیشنهاد می‌شود. تا تأیید تو چیزی تغییر نمی‌کند.", "Your weight trend and nutrition records support a small target adjustment. Nothing changes until you confirm."],
    specialist_review: ["این تغییر به بررسی متخصص نیاز دارد؛ از بخش نظارت پزشک یا گفت‌وگوی برنامه پیگیری کن.", "This change needs specialist review. Use doctor supervision or the program conversation."],
    new_plan_required: ["هدف تغذیه تغییر کرده است؛ برنامه‌ای با هدف فعلی دریافت کن و شروع آن را تأیید کن.", "Targets have changed; request a plan with current targets and confirm its start."],
    cooldown: ["برای بازبینی بعدی، حداقل هفت روز از آخرین تغییر هدف بگذرد.", "Allow at least seven days after the last target change before reviewing again."],
  };
  return copy[status][english ? 1 : 0]!;
}
