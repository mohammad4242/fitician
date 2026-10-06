export const activityFactors = [1.2, 1.375, 1.55, 1.725] as const;
export type CalorieInput = { age: number; sex: "male" | "female"; weight: number; height: number; activity: number };
function bounded(value: number, low: number, high: number) {
  if (!Number.isFinite(value) || value < low || value > high) throw new RangeError("مقدار خارج از محدوده است.");
}
export function calculateCalories(input: CalorieInput) {
  bounded(input.age, 18, 80);
  bounded(input.weight, 35, 250);
  bounded(input.height, 130, 220);
  if (!["male", "female"].includes(input.sex) || !activityFactors.some(factor => factor === input.activity)) throw new RangeError("ورودی معتبر نیست.");
  const resting = 10 * input.weight + 6.25 * input.height - 5 * input.age + (input.sex === "male" ? 5 : -161);
  return { resting: Math.round(resting), maintenance: Math.round(resting * input.activity) };
}
export function calculateProtein(weight: number) {
  bounded(weight, 35, 250);
  return { low: Math.round(weight * 1.4), high: Math.round(weight * 2) };
}

export function calculateBmi(height: number, weight: number) {
  bounded(height, 130, 220);
  bounded(weight, 35, 250);
  const value = weight / (height / 100) ** 2;
  // Classify the unrounded ratio; display rounding must not move a boundary.
  return { value, category: value < 18.5 ? 0 : value < 25 ? 1 : value < 30 ? 2 : 3 };
}
export function parseToolNumber(input: string) {
  const normalized = input.trim().replace(/[۰-۹]/g, digit => String(digit.charCodeAt(0) - 0x06f0))
    .replace(/[٠-٩]/g, digit => String(digit.charCodeAt(0) - 0x0660)).replaceAll("٫", ".");
  if (!/^\d+(?:\.\d+)?$/.test(normalized)) throw new RangeError("عدد معتبر وارد کن.");
  const value = Number(normalized);
  if (!Number.isFinite(value)) throw new RangeError("عدد معتبر وارد کن.");
  return value;
}
