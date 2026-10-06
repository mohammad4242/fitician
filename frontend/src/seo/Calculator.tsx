import { useState, type FormEvent } from "react";
import { activityFactors, calculateCalories, calculateProtein } from "./calculators";
export function Calculator({ protein = false }: { protein?: boolean }) {
  const [result, setResult] = useState<string>();
  const [error, setError] = useState<string>();
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setError(undefined); setResult(undefined);
    try {
      const weight = Number(data.get("weight"));
      if (protein) {
        const range = calculateProtein(weight);
        setResult(`بازه آموزشی پروتئین روزانه: ${range.low} تا ${range.high} گرم`);
      } else {
        const calories = calculateCalories({ age: Number(data.get("age")), sex: data.get("sex") as "male" | "female", weight, height: Number(data.get("height")), activity: Number(data.get("activity")) });
        setResult(`انرژی استراحت: ${calories.resting} کیلوکالری — کالری نگهدارنده تخمینی: ${calories.maintenance} کیلوکالری در روز`);
      }
    } catch { setError("ورودی‌ها را در محدوده مشخص‌شده وارد کن."); }
  }
  return <section className="public-calculator" aria-label="محاسبه رایگان">
    <h2>{protein ? "محاسبه بازه پروتئین" : "محاسبه انرژی روزانه"}</h2>
    <p>فقط برای بزرگسال سالم{protein ? "ِ فعال" : ""}؛ ورودی‌ها در مرورگر می‌مانند.</p>
    <form onSubmit={submit}>
      {!protein && <><label>سن (سال)<input name="age" type="number" min="18" max="80" step="1" defaultValue="30" required /></label>
        <label>ضریب جنس در معادله<select name="sex" defaultValue="male"><option value="male">مرد</option><option value="female">زن</option></select></label>
        <label>قد (سانتی‌متر)<input name="height" type="number" min="130" max="220" step="0.1" defaultValue="175" required /></label></>}
      <label>وزن (کیلوگرم)<input name="weight" type="number" min="35" max="250" step="0.1" defaultValue="70" required /></label>
      {!protein && <label>سطح فعالیت تخمینی<select name="activity" defaultValue="1.2">{activityFactors.map((factor, index) => <option value={factor} key={factor}>{["کم‌تحرک", "فعالیت سبک", "فعالیت متوسط", "فعالیت زیاد"][index]} ({factor})</option>)}</select></label>}
      <button type="submit">محاسبه</button>
    </form>
    {error && <p role="alert">{error}</p>}
    <output aria-live="polite">{result}</output>
  </section>;
}
