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
