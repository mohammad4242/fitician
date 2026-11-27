const tomanNumberFormat = new Intl.NumberFormat("en-US");

export function formatPlanPrice(
  amount: number,
  currency: string,
  english: boolean,
  { groupToman = false }: { groupToman?: boolean } = {},
): string {
  if (currency === "IRR") {
    const toman = amount / 10;
    return `${groupToman ? tomanNumberFormat.format(toman) : toman}T`;
  }
  return `${new Intl.NumberFormat(english ? "en-US" : "fa-IR").format(amount)} ${currency}`;
}
