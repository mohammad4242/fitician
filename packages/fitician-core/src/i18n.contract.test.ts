import en from "./i18n/en.js";
import fa from "./i18n/fa.js";

const resources = { en, fa } as const;
const languages = Object.keys(resources) as Array<keyof typeof resources>;

void languages;
void resources.en;
void resources.fa;

if (fa.translation.billing.viewPlans !== "مشاهده پلن‌ها") {
  throw new Error("Persian billing translations are incomplete");
}
if (en.translation.billing.continueToPayment !== "Continue to payment") {
  throw new Error("English billing translations are incomplete");
}
