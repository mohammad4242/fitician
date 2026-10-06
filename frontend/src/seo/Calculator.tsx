import { useEffect, useId, useState, type FormEvent } from "react";
import { activityFactors, calculateBmi, calculateCalories, calculateProtein, parseToolNumber } from "./calculators";
import { ToolIcon, ToolSwitcher } from "./Tools";
import type { ToolKind } from "./tools";

type Result = { kind: "calorie"; resting: number; maintenance: number } | { kind: "protein"; low: number; high: number } | { kind: "bmi"; value: number; category: number };
type FieldError = { field: string; message: string };
const bmiLabels = ["پایین‌تر از بازه میانی", "بازه میانی مرجع", "بالاتر از بازه میانی", "بالاتر از محدوده مرجع"];
const bmiRanges = ["<18.5", "18.5–24.9", "25–29.9", "30+"];
const formatNumber = (value: number) => new Intl.NumberFormat("en-US").format(value);
function NumberField({ name, label, unit, low, high, value, error, errorId }: {
  name: string; label: string; unit: string; low: number; high: number; value: number; error?: FieldError; errorId: string;
}) {
  const id = useId();
  return <div className="tool-field"><label htmlFor={id}>{label}</label><div className="tool-input-wrap"><input id={id} name={name} type="text" inputMode={name === "age" ? "numeric" : "decimal"} autoComplete="off" required defaultValue={value} dir="ltr" aria-invalid={error?.field === name || undefined} aria-describedby={`${id}-hint${error?.field === name ? ` ${errorId}` : ""}`} data-label={label} data-low={low} data-high={high} /><span className="tool-unit">{unit}</span></div><span id={`${id}-hint`} className="tool-hint">{low} تا {high} {unit}</span></div>;
}
function ResultContent({ result }: { result: Result }) {
  if (result.kind === "calorie") return <><span className="tool-result-label">کالری نگهدارنده تخمینی</span><strong className="tool-result-number" dir="ltr">{formatNumber(result.maintenance)}</strong><span className="tool-result-unit">کیلوکالری / روز</span><span className="tool-secondary"><span>انرژی استراحت</span><strong dir="ltr">{formatNumber(result.resting)} <small>kcal</small></strong></span><span className="tool-result-note">این عدد تخمین است؛ هدف کاهش یا افزایش وزن نیست.</span></>;
  if (result.kind === "protein") return <><span className="tool-result-label">بازه آموزشی پروتئین روزانه</span><strong className="tool-result-number tool-result-range" dir="ltr">{result.low} – {result.high}</strong><span className="tool-result-unit">گرم / روز</span><span className="tool-protein-scale" aria-hidden="true"><span /></span><span className="tool-scale-ends" dir="ltr"><span>1.4 g/kg</span><span>2.0 g/kg</span></span><span className="tool-result-note">۱٫۴ تا ۲ گرم به ازای هر کیلوگرم؛ مقدار بالاتر الزاماً بهتر نیست.</span></>;
  // Four equal visual bands with linear interpolation within each band.
  const value = result.value;
  const position = value < 18.5 ? value / 18.5 * 25 : value < 25 ? 25 + (value - 18.5) / 6.5 * 25 : value < 30 ? 50 + (value - 25) / 5 * 25 : 75 + Math.min((value - 30) / 10, 1) * 25;
  return <><span className="tool-result-label">شاخص توده بدنی</span><strong className="tool-result-number" dir="ltr">{value.toFixed(1)}</strong><span className="tool-bmi-label">{bmiLabels[result.category]}</span><span className="tool-bmi-scale" dir="ltr" aria-hidden="true"><span /><span /><span /><span /><i style={{ left: `${Math.max(2, Math.min(98, position))}%` }} /></span><span className="tool-bmi-legend">{bmiRanges.map((range, index) => <span key={range} className={result.category === index ? "is-current" : undefined}><strong dir="ltr">{range}</strong><span>{bmiLabels[index]}</span>{result.category === index && <b>بازه شما</b>}</span>)}</span><span className="tool-result-note">نوار فقط راهنمای بازه‌هاست؛ دو سر آن محدود شده‌اند. دسته‌بندی با عدد گردنشده انجام می‌شود.</span><span className="tool-result-note">BMI اندازه‌گیری چربی یا عضله و تشخیص پزشکی نیست.</span></>;
}
export function Calculator({ kind = "calorie" }: { kind?: ToolKind }) {
  const [ready, setReady] = useState(false);
  useEffect(() => { setReady(true); }, []);
  const [result, setResult] = useState<Result>();
  const [error, setError] = useState<FieldError>();
  const errorId = useId();
  const titleId = useId();
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setError(undefined); setResult(undefined);
    const numbers: Record<string, number> = {};
    for (const input of form.querySelectorAll<HTMLInputElement>("input")) {
      try {
        const value = parseToolNumber(input.value);
        if (value < Number(input.dataset.low) || value > Number(input.dataset.high) || (input.name === "age" && !Number.isInteger(value))) throw new RangeError();
        numbers[input.name] = value;
      } catch {
        setError({ field: input.name, message: `${input.dataset.label} را با عدد معتبر از ${input.dataset.low} تا ${input.dataset.high}${input.name === "age" ? " (سال کامل)" : ""} وارد کن.` });
        input.focus(); return;
      }
    }
    const data = new FormData(form);
    try {
      if (kind === "bmi") setResult({ kind, ...calculateBmi(numbers.height, numbers.weight) });
      else if (kind === "protein") setResult({ kind, ...calculateProtein(numbers.weight) });
      else setResult({ kind, ...calculateCalories({ age: numbers.age, sex: data.get("sex") as "male" | "female", weight: numbers.weight, height: numbers.height, activity: Number(data.get("activity")) }) });
    } catch { setError({ field: "", message: "ورودی‌ها را در محدوده مشخص‌شده وارد کن." }); }
  }
  return <section className={`fitician-tool fitician-tool-${kind}`} aria-labelledby={titleId}>
    <ToolSwitcher kind={kind} />
    <div className="tool-workspace"><form className="tool-form" onSubmit={submit} noValidate onChange={() => { setResult(undefined); setError(undefined); }}>
      <div className="tool-form-heading"><span className="tool-form-icon"><ToolIcon /></span><div><h2 id={titleId}>اطلاعات اولیه</h2><p>{kind === "bmi" ? "برای بزرگسالان ۲۰ سال و بالاتر" : kind === "protein" ? "برای بزرگسال سالم و فعال" : "برای بزرگسال سالم، ۱۸ تا ۸۰ سال"}</p></div></div>
      <div className="tool-fields">
        {kind === "calorie" && <><NumberField name="age" label="سن" unit="سال" low={18} high={80} value={30} error={error} errorId={errorId} /><div className="tool-field"><label htmlFor={`${titleId}-sex`}>ضریب جنس در معادله</label><select id={`${titleId}-sex`} name="sex" defaultValue="male"><option value="male">مرد</option><option value="female">زن</option></select><span className="tool-hint">فقط برای انتخاب ضریب معادله</span></div></>}
        {kind !== "protein" && <NumberField name="height" label="قد" unit="سانتی‌متر" low={130} high={220} value={175} error={error} errorId={errorId} />}
        <NumberField name="weight" label="وزن" unit="کیلوگرم" low={35} high={250} value={70} error={error} errorId={errorId} />
        {kind === "calorie" && <div className="tool-field tool-field-wide"><label htmlFor={`${titleId}-activity`}>سطح فعالیت تخمینی</label><select id={`${titleId}-activity`} name="activity" defaultValue="1.2">{activityFactors.map((factor, index) => <option value={factor} key={factor}>{["کم‌تحرک", "فعالیت سبک", "فعالیت متوسط", "فعالیت زیاد"][index]} ({factor})</option>)}</select></div>}
      </div>
      {error && <p className="tool-error" role="alert" id={errorId}>{error.message}</p>}
      <button className="tool-submit" type="submit" disabled={!ready}>محاسبه نتیجه <span aria-hidden="true">←</span></button>
      <p className="tool-local-note">بدون ذخیره یا ارسال قد، وزن و اطلاعات شخصی</p>
      <noscript><p className="tool-local-note">برای محاسبه روی دستگاه، جاوااسکریپت را فعال کن. اطلاعات ارسال نمی‌شود.</p></noscript>
    </form>
    <div className={`tool-result-panel${result ? " has-result" : ""}`}><span className="tool-result-eyebrow">FITICIAN / INSIGHT</span><output className="tool-result" aria-live="polite" aria-atomic="true">{result ? <ResultContent result={result} /> : <span className="tool-empty"><span className="tool-empty-mark" aria-hidden="true">—</span><strong>از یک عدد آگاهانه شروع کن</strong><span>اطلاعات را وارد کن و «محاسبه نتیجه» را بزن.<br />نتیجه همین‌جا نمایش داده می‌شود.</span></span>}</output></div>
    </div>
  </section>;
}
