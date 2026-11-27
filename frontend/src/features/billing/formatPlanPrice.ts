export function formatPlanPrice(amount: number, currency: string, english: boolean): string {
  if (currency === "IRR") return `${amount / 10}T`;
  return `${new Intl.NumberFormat(english ? "en-US" : "fa-IR").format(amount)} ${currency}`;
}
