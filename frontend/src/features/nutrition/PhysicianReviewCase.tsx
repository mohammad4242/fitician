import { useState, type ReactNode } from "react";

import { formatIsoDate, formatPersianDate } from "@fitician/core";

import { ProfilePhotoAvatar } from "../profile/ProfilePhoto";
import { ReviewDisclosure } from "../../shared/ReviewDisclosure";
import { ReviewProfileSummaryCard } from "../../shared/ReviewProfileSummaryCard";
import {
  SpecialistCaseHeader,
  SpecialistStatusBadge,
} from "../../shared/specialistWorkbench";
import type { SupplementCatalogueItem, SupplementOrder } from "./api";
import type { LabDocument, PhysicianReviewQueueItem } from "./api";
import type { WeeklyPlan, WeeklyPlanFood } from "./types";
import { irrToToman } from "./money";

type PhysicianCaseTab = "summary" | "plan" | "labs" | "supplements" | "notes";
type PhysicianAction = "approve" | "request_changes" | "reject";
type LabReviewStatus = "reviewed" | "requires_follow_up";
type SupplementTransition = "active" | "completed" | "discontinued" | "cancelled";

export type PhysicianOrderForm = {
  supplementId: string;
  doseAmount: string;
  doseUnit: string;
  dailyUnits: string;
  frequency: string;
  durationDays: string;
  instructions: string;
  rationale: string;
};

type PhysicianReviewCaseProps = {
  readonly busy: boolean;
  readonly fa: boolean;
  readonly foodCatalogue: readonly { id: string; name_fa: string; name_en: string }[];
  readonly labs: readonly LabDocument[];
  readonly notes: string;
  readonly internalNotes: string;
  readonly onAct: (action: PhysicianAction) => void;
  readonly onAdjustFoodQuantity: (mealId: string, foodId: string, grams: number) => void;
  readonly onBack: () => void;
  readonly onEditOrder: (order: SupplementOrder) => void;
  readonly onNotesChange: (value: string) => void;
  readonly onInternalNotesChange: (value: string) => void;
  readonly onOrderFormChange: (patch: Partial<PhysicianOrderForm>) => void;
  readonly onRequestLabs: (requestedTests: string[]) => void;
  readonly onReplaceFood: (mealId: string, foodId: string, replacementFoodId: string) => void;
  readonly onReviewLab: (documentId: string, status: LabReviewStatus) => void;
  readonly onSaveOrder: () => void;
  readonly onTestsChange: (value: string) => void;
  readonly onTransitionOrder: (orderId: string, status: SupplementTransition) => void;
  readonly orderForm: PhysicianOrderForm;
  readonly orders: readonly SupplementOrder[];
  readonly plan: WeeklyPlan;
  readonly readOnly: boolean;
  readonly review: PhysicianReviewQueueItem;
  readonly supplementCatalogue: readonly SupplementCatalogueItem[];
  readonly tests: string;
};

const tabs: Array<{ id: PhysicianCaseTab; fa: string; en: string }> = [
  { id: "summary", fa: "خلاصه", en: "Summary" },
  { id: "plan", fa: "برنامه تغذیه", en: "Plan review" },
  { id: "labs", fa: "آزمایش‌ها", en: "Laboratory review" },
  { id: "supplements", fa: "مکمل‌ها", en: "Supplements" },
  { id: "notes", fa: "یادداشت‌ها", en: "Notes" },
];

export function PhysicianReviewCase({
  busy,
  fa,
  foodCatalogue,
  labs,
  notes,
  internalNotes,
  onAct,
  onAdjustFoodQuantity,
  onBack,
  onEditOrder,
  onNotesChange,
  onInternalNotesChange,
  onOrderFormChange,
  onRequestLabs,
  onReplaceFood,
  onReviewLab,
  onSaveOrder,
  onTestsChange,
  onTransitionOrder,
  orderForm,
  orders,
  plan,
  readOnly,
  review,
  supplementCatalogue,
  tests,
}: PhysicianReviewCaseProps) {
  const [activeTab, setActiveTab] = useState<PhysicianCaseTab>("summary");
  const memberName = review.member_display_name ?? (fa ? "کاربر فیتیشن" : "Fitician member");
  const caseStatus = plan.physician_review_status ?? review.status;
  const tabTitle = (tab: PhysicianCaseTab) => tabs.find((item) => item.id === tab)?.[fa ? "fa" : "en"] ?? "";

  return (
    <article className="physician-review-case" data-testid="physician-review-case">
      <div className="physician-review-case-header" data-testid="physician-review-case-header">
        <SpecialistCaseHeader
          avatar={<ProfilePhotoAvatar label={memberName} size="md" url={review.member_profile_photo_url} />}
          backLabel={fa ? "بازگشت به صف" : "Back to queue"}
          context="physician"
          eyebrow={fa ? "پرونده تغذیه" : "Nutrition case"}
          fa={fa}
          meta={[
            { label: fa ? "اولویت" : "Priority", value: formatNumber(review.priority, fa) },
            { label: fa ? "هزینه هفتگی" : "Weekly cost", value: `${irrToToman(plan.weekly_cost_irr)} ${fa ? "تومان" : "Toman"}` },
            { label: fa ? "مدت نسخه" : "Plan duration", value: `${formatNumber(plan.days.length, fa)} ${fa ? "روز" : "days"}` },
            ...(review.overdue ? [{ label: fa ? "توجه" : "Attention", value: fa ? "گذشته از موعد" : "Overdue" }] : []),
          ]}
          name={memberName}
          onBack={onBack}
          status={caseStatus}
        />
      </div>

      <nav aria-label={fa ? "بخش‌های پرونده تغذیه" : "Nutrition case sections"} className="physician-case-tabs" role="tablist">
        {tabs.map((tab) => (
          <button
            aria-controls={`physician-case-panel-${tab.id}`}
            aria-selected={activeTab === tab.id}
            id={`physician-case-tab-${tab.id}`}
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            role="tab"
            tabIndex={activeTab === tab.id ? 0 : -1}
            type="button"
          >
            {tabTitle(tab.id)}
          </button>
        ))}
      </nav>

      <section
        aria-labelledby={`physician-case-tab-${activeTab}`}
        className="physician-review-case-panel"
        id={`physician-case-panel-${activeTab}`}
        role="tabpanel"
        tabIndex={0}
      >
        {activeTab === "summary" && <PhysicianCaseSummary fa={fa} labs={labs} orders={orders} plan={plan} />}
        {activeTab === "plan" && (
          <PhysicianPlanReview
            fa={fa}
            foodCatalogue={foodCatalogue}
            onAdjustFoodQuantity={onAdjustFoodQuantity}
            onReplaceFood={onReplaceFood}
            plan={plan}
            readOnly={readOnly}
          />
        )}
        {activeTab === "labs" && (
          <PhysicianLabs
            fa={fa}
            labs={labs}
            notes={notes}
            onRequestLabs={onRequestLabs}
            onReviewLab={onReviewLab}
            onTestsChange={onTestsChange}
            readOnly={readOnly}
            tests={tests}
          />
        )}
        {activeTab === "supplements" && (
          <PhysicianSupplements
            fa={fa}
            onEditOrder={onEditOrder}
            onOrderFormChange={onOrderFormChange}
            onSaveOrder={onSaveOrder}
            onTransitionOrder={onTransitionOrder}
            orderForm={orderForm}
            orders={orders}
            readOnly={readOnly}
            supplementCatalogue={supplementCatalogue}
          />
        )}
        {activeTab === "notes" && (
          <section className="physician-review-section physician-review-notes">
            <label>
              {fa ? "یادداشت قابل مشاهده برای کاربر" : "User-visible note"}
              <textarea disabled={readOnly} value={notes} onChange={(event) => onNotesChange(event.target.value)} />
            </label>
            <label>
              {fa ? "یادداشت محرمانه پزشک" : "Private physician note"}
              <textarea disabled={readOnly} value={internalNotes} onChange={(event) => onInternalNotesChange(event.target.value)} />
            </label>
          </section>
        )}
      </section>

      {!readOnly ? (
        <footer aria-label={fa ? "تصمیم نهایی" : "Final decision"} className="physician-review-actions">
          <div>
            <p>{fa ? "تصمیم نهایی" : "Final decision"}</p>
            <span>{fa ? "پس از تکمیل بررسی، اقدام مناسب را ثبت کن." : "Record the appropriate decision after completing the review."}</span>
          </div>
          <div className="physician-review-actions__buttons">
            <button disabled={busy} onClick={() => onAct("approve")} type="button">{fa ? "تأیید نسخه" : "Approve this revision"}</button>
            <button disabled={busy || !notes.trim()} onClick={() => onAct("request_changes")} type="button">{fa ? "درخواست تغییر" : "Request changes"}</button>
            <button className="is-danger" disabled={busy || !notes.trim()} onClick={() => onAct("reject")} type="button">{fa ? "رد نسخه" : "Reject"}</button>
          </div>
        </footer>
      ) : null}
    </article>
  );
}

function PhysicianCaseSummary({
  fa,
  labs,
  orders,
  plan,
}: {
  readonly fa: boolean;
  readonly labs: readonly LabDocument[];
  readonly orders: readonly SupplementOrder[];
  readonly plan: WeeklyPlan;
}) {
  const medical = plan.profile_summary?.medical;
  const safetyReasons = readStringArray(plan.input_snapshot.safety_reason_codes);

  return (
    <div className="physician-case-summary">
      <ReviewProfileSummaryCard fa={fa} summary={plan.profile_summary} />
      <section className="physician-summary-section">
        <header><h3>{fa ? "نمای کلی نسخه" : "Plan overview"}</h3></header>
        <dl className="physician-summary-grid">
          <SummaryValue label={fa ? "هزینه هفتگی" : "Weekly cost"} value={`${irrToToman(plan.weekly_cost_irr)} ${fa ? "تومان" : "Toman"}`} />
          <SummaryValue label={fa ? "بودجه" : "Budget"} value={formatDataStatus(plan.budget_status, fa)} />
          <SummaryValue label={fa ? "روزهای نسخه" : "Plan days"} value={formatNumber(plan.days.length, fa)} />
          <SummaryValue label={fa ? "شماره نسخه" : "Revision"} value={formatNumber(plan.revision, fa)} />
          <SummaryValue label={fa ? "آزمایش‌ها" : "Laboratory"} value={labs.length ? fa ? `${formatNumber(labs.length, fa)} مورد` : `${labs.length} documents` : fa ? "ثبت نشده" : "None recorded"} />
          <SummaryValue label={fa ? "مکمل‌ها" : "Supplements"} value={orders.length ? fa ? `${formatNumber(orders.length, fa)} دستور` : `${orders.length} orders` : fa ? "ثبت نشده" : "None recorded"} />
        </dl>
      </section>
      <section className="physician-summary-section">
        <header><h3>{fa ? "ایمنی و نکات مهم" : "Safety and key flags"}</h3></header>
        {safetyReasons.length > 0 || medical?.safety_reason_codes?.length ? (
          <ul className="physician-readable-list">
            {[...safetyReasons, ...(medical?.safety_reason_codes ?? [])].map((code) => <li key={code}>{humanizeCode(code, fa)}</li>)}
          </ul>
        ) : (
          <p className="physician-summary-muted">{fa ? "پرچم ایمنی فعالی در دادهٔ نسخه ثبت نشده است." : "No active safety flags were recorded in the plan data."}</p>
        )}
      </section>
      <PhysicianEvidence plan={plan} fa={fa} />
    </div>
  );
}

function PhysicianPlanReview({
  fa,
  foodCatalogue,
  onAdjustFoodQuantity,
  onReplaceFood,
  plan,
  readOnly,
}: {
  readonly fa: boolean;
  readonly foodCatalogue: readonly { id: string; name_fa: string; name_en: string }[];
  readonly onAdjustFoodQuantity: (mealId: string, foodId: string, grams: number) => void;
  readonly onReplaceFood: (mealId: string, foodId: string, replacementFoodId: string) => void;
  readonly plan: WeeklyPlan;
  readonly readOnly: boolean;
}) {
  return (
    <section className="physician-review-section">
      <PhysicianEvidence plan={plan} fa={fa} />
      <ReviewDisclosure
        section="physician-nutrients"
        summary={fa ? `${formatNumber(Object.keys(plan.nutrients).length, fa)} شاخص ثبت‌شده` : `${Object.keys(plan.nutrients).length} recorded metrics`}
        title={fa ? "وضعیت مواد مغذی" : "Nutrient validation"}
      >
        <div className="physician-nutrient-list">
          {Object.values(plan.nutrients).map((nutrient) => (
            <div className="physician-nutrient-row" key={nutrient.nutrient_code}>
              <span>{humanizeCode(nutrient.nutrient_code, fa)}</span>
              <strong>{formatNumber(nutrient.planned, fa)} {nutrient.unit}</strong>
              <span className="physician-readable-status">{formatDataStatus(nutrient.status, fa)}</span>
            </div>
          ))}
        </div>
      </ReviewDisclosure>
      <div className="physician-plan-days">
        {plan.days.map((day) => (
          <ReviewDisclosure
            className="physician-plan-day"
            key={day.plan_date}
            section="physician-plan-day"
            summary={fa ? `${formatNumber(day.meals.length, fa)} وعده` : `${day.meals.length} meals`}
            title={fa ? `روز ${formatNumber(day.day_index + 1, fa)} · ${formatPersianDate(day.plan_date)}` : `Day ${day.day_index + 1} · ${formatIsoDate(day.plan_date, "en-US")}`}
          >
            <div className="physician-plan-meals">
              {day.meals.map((meal, mealIndex) => (
                <ReviewDisclosure
                  className="physician-plan-meal"
                  key={meal.id}
                  section="physician-plan-meal"
                  summary={fa ? `${formatNumber(meal.foods.length, fa)} ماده غذایی` : `${meal.foods.length} food items`}
                  title={fa ? (meal.name_fa ?? `وعده ${formatNumber(mealIndex + 1, fa)}`) : (meal.name_en ?? `Meal ${mealIndex + 1}`)}
                >
                  <div className="physician-plan-foods">
                    {meal.foods.map((food) => (
                      <PhysicianFoodRow
                        fa={fa}
                        food={food}
                        foodCatalogue={foodCatalogue}
                        key={food.food_id ?? food.slug}
                        mealId={meal.id}
                        onAdjustFoodQuantity={onAdjustFoodQuantity}
                        onReplaceFood={onReplaceFood}
                        readOnly={readOnly}
                      />
                    ))}
                  </div>
                </ReviewDisclosure>
              ))}
            </div>
          </ReviewDisclosure>
        ))}
      </div>
    </section>
  );
}

function PhysicianFoodRow({
  fa,
  food,
  foodCatalogue,
  mealId,
  onAdjustFoodQuantity,
  onReplaceFood,
  readOnly,
}: {
  readonly fa: boolean;
  readonly food: WeeklyPlanFood;
  readonly foodCatalogue: readonly { id: string; name_fa: string; name_en: string }[];
  readonly mealId: string;
  readonly onAdjustFoodQuantity: (mealId: string, foodId: string, grams: number) => void;
  readonly onReplaceFood: (mealId: string, foodId: string, replacementFoodId: string) => void;
  readonly readOnly: boolean;
}) {
  const name = fa ? food.name_fa : food.name_en;
  if (food.food_id === null) {
    return <p><span>{name}</span><strong>{formatNumber(food.grams, fa)} g</strong></p>;
  }

  return (
    <p>
      <span>{name}</span>
      <input
        aria-label={fa ? `مقدار ${food.name_fa}` : `${food.name_en} quantity`}
        defaultValue={food.grams}
        disabled={readOnly}
        max="5000"
        min="1"
        onBlur={(event) => {
          const grams = Number(event.target.value);
          if (!readOnly && grams !== food.grams) onAdjustFoodQuantity(mealId, food.food_id!, grams);
        }}
        type="number"
      />
      <select
        aria-label={fa ? `جایگزین ${food.name_fa}` : `Replace ${food.name_en}`}
        disabled={readOnly}
        onChange={(event) => {
          if (!readOnly && event.target.value !== food.food_id) onReplaceFood(mealId, food.food_id!, event.target.value);
        }}
        value={food.food_id}
      >
        <option value={food.food_id}>{name}</option>
        {foodCatalogue.filter((candidate) => candidate.id !== food.food_id).map((candidate) => (
          <option key={candidate.id} value={candidate.id}>{fa ? candidate.name_fa : candidate.name_en}</option>
        ))}
      </select>
    </p>
  );
}

function PhysicianLabs({
  fa,
  labs,
  notes,
  onRequestLabs,
  onReviewLab,
  onTestsChange,
  readOnly,
  tests,
}: {
  readonly fa: boolean;
  readonly labs: readonly LabDocument[];
  readonly notes: string;
  readonly onRequestLabs: (requestedTests: string[]) => void;
  readonly onReviewLab: (documentId: string, status: LabReviewStatus) => void;
  readonly onTestsChange: (value: string) => void;
  readonly readOnly: boolean;
  readonly tests: string;
}) {
  return (
    <section className="physician-review-section physician-labs-panel">
      <header><h3>{fa ? "آزمایش‌های کاربر" : "Member lab documents"}</h3><span>{formatNumber(labs.length, fa)} {fa ? "مورد" : "documents"}</span></header>
      {labs.length === 0 ? <p className="physician-summary-muted">{fa ? "آزمایشی ثبت نشده است." : "No lab documents are available."}</p> : (
        <div className="physician-lab-list">
          {labs.map((lab) => (
            <article key={lab.id}>
              <div>
                <strong>{lab.original_filename}</strong>
                <small>{[lab.category, lab.laboratory_name, lab.test_date].filter(Boolean).join(" · ") || (fa ? "جزئیات تکمیلی ثبت نشده" : "No extra details recorded")}</small>
              </div>
              <SpecialistStatusBadge context="physician" fa={fa} status={lab.review_status} />
              {!readOnly ? <button onClick={() => onReviewLab(lab.id, "reviewed")} type="button">{fa ? "ثبت بررسی" : "Mark reviewed"}</button> : null}
            </article>
          ))}
        </div>
      )}
      <label>
        {fa ? "آزمایش‌های درخواستی" : "Requested tests"}
        <input disabled={readOnly} value={tests} onChange={(event) => onTestsChange(event.target.value)} />
      </label>
      {!readOnly ? <button onClick={() => onRequestLabs(tests.split(",").map((item) => item.trim()).filter(Boolean))} type="button">{fa ? "درخواست آزمایش" : "Request labs"}</button> : null}
      {notes ? <p className="physician-labs-note">{fa ? "یادداشت همراه درخواست:" : "Note included with request:"} {notes}</p> : null}
    </section>
  );
}

function PhysicianSupplements({
  fa,
  onEditOrder,
  onOrderFormChange,
  onSaveOrder,
  onTransitionOrder,
  orderForm,
  orders,
  readOnly,
  supplementCatalogue,
}: {
  readonly fa: boolean;
  readonly onEditOrder: (order: SupplementOrder) => void;
  readonly onOrderFormChange: (patch: Partial<PhysicianOrderForm>) => void;
  readonly onSaveOrder: () => void;
  readonly onTransitionOrder: (orderId: string, status: SupplementTransition) => void;
  readonly orderForm: PhysicianOrderForm;
  readonly orders: readonly SupplementOrder[];
  readonly readOnly: boolean;
  readonly supplementCatalogue: readonly SupplementCatalogueItem[];
}) {
  const orderReady = Boolean(orderForm.supplementId && orderForm.instructions.trim() && orderForm.rationale.trim());

  return (
    <section className="physician-review-section physician-supplements-panel">
      <header><h3>{fa ? "دستورهای مکمل" : "Supplement orders"}</h3><span>{formatNumber(orders.length, fa)} {fa ? "دستور" : "orders"}</span></header>
      {orders.length === 0 ? <p className="physician-summary-muted">{fa ? "دستوری ثبت نشده است." : "No order has been recorded."}</p> : (
        <div className="physician-supplement-list">
          {orders.map((order) => (
            <article key={order.id}>
              <div>
                <strong>{order.name}</strong>
                <small>{order.dose_amount} {order.dose_unit} · {order.frequency} · {formatNumber(order.duration_days, fa)} {fa ? "روز" : "days"}</small>
              </div>
              <SpecialistStatusBadge context="physician" fa={fa} status={order.status} />
              {!readOnly && ["prescribed", "active"].includes(order.status) ? <button onClick={() => onEditOrder(order)} type="button">{fa ? "ویرایش" : "Edit"}</button> : null}
              {!readOnly && order.status === "prescribed" ? <div className="physician-inline-actions"><button onClick={() => onTransitionOrder(order.id, "active")} type="button">{fa ? "فعال‌سازی" : "Activate"}</button><button onClick={() => onTransitionOrder(order.id, "cancelled")} type="button">{fa ? "لغو" : "Cancel"}</button></div> : null}
              {!readOnly && order.status === "active" ? <div className="physician-inline-actions"><button onClick={() => onTransitionOrder(order.id, "completed")} type="button">{fa ? "تکمیل" : "Complete"}</button><button onClick={() => onTransitionOrder(order.id, "discontinued")} type="button">{fa ? "قطع" : "Discontinue"}</button></div> : null}
            </article>
          ))}
        </div>
      )}
      <fieldset className="physician-supplement-form" disabled={readOnly}>
        <legend>{fa ? "ثبت دستور جدید" : "Create a supplement order"}</legend>
        <label>{fa ? "مکمل" : "Supplement"}<select value={orderForm.supplementId} onChange={(event) => onOrderFormChange({ supplementId: event.target.value })}><option value="">{fa ? "انتخاب مکمل" : "Select supplement"}</option>{supplementCatalogue.map((item) => <option key={item.id} value={item.id}>{fa ? item.name_fa : item.name_en}</option>)}</select></label>
        <label>{fa ? "مقدار دوز" : "Dose amount"}<input min="0.01" type="number" value={orderForm.doseAmount} onChange={(event) => onOrderFormChange({ doseAmount: event.target.value })} /></label>
        <label>{fa ? "واحد دوز" : "Dose unit"}<input value={orderForm.doseUnit} onChange={(event) => onOrderFormChange({ doseUnit: event.target.value })} /></label>
        <label>{fa ? "تعداد واحد روزانه" : "Daily units"}<input min="0.01" type="number" value={orderForm.dailyUnits} onChange={(event) => onOrderFormChange({ dailyUnits: event.target.value })} /></label>
        <label>{fa ? "دفعات مصرف" : "Frequency"}<input value={orderForm.frequency} onChange={(event) => onOrderFormChange({ frequency: event.target.value })} /></label>
        <label>{fa ? "مدت به روز" : "Duration in days"}<input min="1" type="number" value={orderForm.durationDays} onChange={(event) => onOrderFormChange({ durationDays: event.target.value })} /></label>
        <label>{fa ? "دستور مصرف" : "Instructions"}<textarea value={orderForm.instructions} onChange={(event) => onOrderFormChange({ instructions: event.target.value })} /></label>
        <label>{fa ? "دلیل بالینی" : "Clinical rationale"}<textarea value={orderForm.rationale} onChange={(event) => onOrderFormChange({ rationale: event.target.value })} /></label>
        {!readOnly ? <button disabled={!orderReady} onClick={onSaveOrder} type="button">{fa ? "ثبت دستور مکمل" : "Prescribe supplement"}</button> : null}
      </fieldset>
    </section>
  );
}

function PhysicianEvidence({ fa, plan }: { readonly fa: boolean; readonly plan: WeeklyPlan }) {
  return (
    <ReviewDisclosure
      section="physician-evidence"
      summary={fa ? "اطلاعات مبنا و کنترل‌های نسخه به‌صورت خوانا" : "Readable plan inputs and provenance controls"}
      title={fa ? "پروفایل، ایمنی، بودجه و منشأ داده" : "Profile, safety, budget, and provenance"}
    >
      <div className="physician-readable-evidence">
        <EvidenceBlock fa={fa} label={fa ? "داده‌های ورودی" : "Input snapshot"} value={plan.input_snapshot} valueKey="input_snapshot" />
        <EvidenceBlock fa={fa} label={fa ? "وضعیت بودجه" : "Budget"} value={plan.budget_status} valueKey="budget_status" />
        <EvidenceBlock fa={fa} label={fa ? "تصویر قیمت" : "Price snapshot"} value={plan.price_snapshot} valueKey="price_snapshot" />
        <EvidenceBlock fa={fa} label={fa ? "منشأ داده غذا" : "Food data provenance"} value={plan.food_data_manifest} valueKey="food_data_manifest" />
        {(plan.repair_actions ?? []).length > 0 ? <EvidenceBlock fa={fa} label={fa ? "اقدام‌های ترمیم نسخه" : "Plan repair actions"} value={plan.repair_actions} valueKey="repair_actions" /> : null}
      </div>
    </ReviewDisclosure>
  );
}

function EvidenceBlock({ fa, label, value, valueKey }: { readonly fa: boolean; readonly label: string; readonly value: unknown; readonly valueKey: string }) {
  return (
    <section className="physician-evidence-block">
      <h4>{label}</h4>
      <ReadableValue fa={fa} keyName={valueKey} value={value} />
    </section>
  );
}

function ReadableValue({ fa, keyName, value }: { readonly fa: boolean; readonly keyName?: string; readonly value: unknown }): ReactNode {
  if (value === null || value === undefined || value === "") return <span className="physician-readable-muted">{fa ? "ثبت نشده" : "Not recorded"}</span>;
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="physician-readable-muted">{fa ? "موردی ثبت نشده" : "None recorded"}</span>;
    return <ul className="physician-readable-list">{value.map((item, index) => <li key={`${keyName ?? "value"}-${index}`}><ReadableValue fa={fa} keyName={keyName} value={item} /></li>)}</ul>;
  }
  if (typeof value === "object") {
    return <dl className="physician-readable-data">{Object.entries(value as Record<string, unknown>).map(([key, nestedValue]) => <div key={key}><dt>{labelForKey(key, fa)}</dt><dd><ReadableValue fa={fa} keyName={key} value={nestedValue} /></dd></div>)}</dl>;
  }
  if (typeof value === "boolean") return <span>{value ? fa ? "بله" : "Yes" : fa ? "خیر" : "No"}</span>;
  if (typeof value === "number") return <span>{value.toLocaleString(fa ? "fa-IR" : "en-US")}</span>;
  const textValue = String(value);
  return <span>{isStatusKey(keyName) ? formatDataStatus(textValue, fa) : humanizeCode(textValue, fa)}</span>;
}

function SummaryValue({ label, value }: { readonly label: string; readonly value: string }) {
  return <div><dt>{label}</dt><dd>{value}</dd></div>;
}

function formatNumber(value: number, fa: boolean) {
  return value.toLocaleString(fa ? "fa-IR" : "en-US");
}

function formatDataStatus(value: string, fa: boolean) {
  const labels: Record<string, [string, string]> = {
    active: ["فعال", "Active"],
    adequate: ["کافی", "Adequate"],
    above_applicable_limit: ["بالاتر از حد مجاز", "Above applicable limit"],
    above_preferred: ["بالاتر از مقدار مطلوب", "Above preferred"],
    below_preferred: ["پایین‌تر از مقدار مطلوب", "Below preferred"],
    cancelled: ["لغوشده", "Cancelled"],
    completed: ["تکمیل‌شده", "Completed"],
    data_incomplete: ["داده ناقص", "Data incomplete"],
    discontinued: ["قطع‌شده", "Discontinued"],
    fresh: ["به‌روز", "Fresh"],
    in_review: ["در حال بررسی", "In review"],
    claimed: ["در حال بررسی", "In review"],
    pending: ["در انتظار بررسی", "Waiting for review"],
    prescribed: ["تجویزشده", "Prescribed"],
    rejected: ["ردشده", "Rejected"],
    requires_follow_up: ["نیازمند پیگیری", "Needs follow-up"],
    reviewed: ["بررسی‌شده", "Reviewed"],
    uploaded: ["بارگذاری‌شده", "Uploaded"],
    within_budget: ["در محدوده بودجه", "Within budget"],
    over_budget: ["بیشتر از بودجه", "Over budget"],
  };
  return labels[value]?.[fa ? 0 : 1] ?? (fa ? "ثبت‌شده" : "Recorded");
}

function isStatusKey(key: string | undefined) {
  return Boolean(key && (key === "status" || key.endsWith("_status") || key.includes("review_status")));
}

function labelForKey(key: string, fa: boolean) {
  const labels: Record<string, [string, string]> = {
    catalogue_version: ["نسخه کاتالوگ", "Catalogue version"],
    created_at: ["زمان ایجاد", "Created at"],
    food_data_manifest: ["منشأ داده غذا", "Food data provenance"],
    input_snapshot: ["داده‌های ورودی", "Input snapshot"],
    price_snapshot: ["تصویر قیمت", "Price snapshot"],
    safety_reason_codes: ["دلایل ایمنی", "Safety reasons"],
    status: ["وضعیت", "Status"],
  };
  return labels[key]?.[fa ? 0 : 1] ?? humanizeCode(key, fa);
}

function humanizeCode(value: string, fa: boolean) {
  const labels: Record<string, [string, string]> = {
    controlled_hypertension: ["فشار خون کنترل‌شده", "Controlled hypertension"],
    lose_weight: ["کاهش وزن", "Lose weight"],
    within_budget: ["در محدوده بودجه", "Within budget"],
  };
  return labels[value]?.[fa ? 0 : 1] ?? value.replaceAll("_", " ");
}

function readStringArray(value: unknown) {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}
