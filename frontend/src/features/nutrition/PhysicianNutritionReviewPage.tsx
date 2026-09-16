import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";

import { AppErrorNotice } from "../../shared/AppErrorNotice";
import { SpecialistWorkbenchShell } from "../../shared/specialistWorkbench";
import type { SpecialistSection } from "../../shared/specialistWorkbench";
import { PhysicianDashboard } from "./PhysicianDashboard";
import { PhysicianReviewCase, type PhysicianOrderForm } from "./PhysicianReviewCase";
import { PhysicianReviewQueue } from "./PhysicianReviewQueue";
import * as api from "./api";
import type { PhysicianSupplementOrderInput, SupplementOrder } from "./api";
import type { WeeklyPlan } from "./types";
import "./nutritionEstimate.css";
import "./physicianWorkspace.css";

type QueueView = api.PhysicianQueueView;
type Review = api.PhysicianReviewQueueItem;
type PhysicianAction = "approve" | "request_changes" | "reject";
type LabReviewStatus = "reviewed" | "requires_follow_up";
type SupplementTransition = "active" | "completed" | "discontinued" | "cancelled";

const queueViews: QueueView[] = ["pending", "claimed", "approved"];
const emptyQueues: Record<QueueView, Review[]> = { pending: [], claimed: [], approved: [] };
const initialLoading: Record<QueueView, boolean> = { pending: true, claimed: true, approved: true };
const emptyOrder: PhysicianOrderForm = {
  supplementId: "",
  doseAmount: "1",
  doseUnit: "tablet",
  dailyUnits: "1",
  frequency: "once_daily",
  durationDays: "30",
  instructions: "",
  rationale: "",
};

export function PhysicianNutritionReviewPage() {
  const { i18n } = useTranslation();
  const fa = i18n.resolvedLanguage !== "en";
  const l = useCallback((faText: string, enText: string) => (fa ? faText : enText), [fa]);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeSection = readSection(searchParams.get("section"));
  const activeQueueView = queueViewForSection(activeSection);
  const [queues, setQueues] = useState<Record<QueueView, Review[]>>(emptyQueues);
  const [loadingQueues, setLoadingQueues] = useState<Record<QueueView, boolean>>(initialLoading);
  const [queueErrors, setQueueErrors] = useState<Partial<Record<QueueView, unknown>>>({});
  const [apiError, setApiError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<WeeklyPlan | null>(null);
  const [selectedReview, setSelectedReview] = useState<Review | null>(null);
  const [selectedSourceView, setSelectedSourceView] = useState<QueueView | null>(null);
  const [readOnly, setReadOnly] = useState(false);
  const [labs, setLabs] = useState<api.LabDocument[]>([]);
  const [orders, setOrders] = useState<SupplementOrder[]>([]);
  const [notes, setNotes] = useState("");
  const [internalNotes, setInternalNotes] = useState("");
  const [tests, setTests] = useState("CBC");
  const [supplementCatalogue, setSupplementCatalogue] = useState<Awaited<ReturnType<typeof api.listSupplementCatalogue>>>([]);
  const [foodCatalogue, setFoodCatalogue] = useState<api.CatalogueFood[]>([]);
  const [orderForm, setOrderForm] = useState<PhysicianOrderForm>(emptyOrder);
  const [editingOrderId, setEditingOrderId] = useState<string | null>(null);
  const allQueuesLoading = queueViews.some((view) => loadingQueues[view]);
  const currentQueueLoading = loadingQueues[activeQueueView];
  const firstQueueError = queueViews.map((view) => queueErrors[view]).find((cause) => cause !== undefined);
  const visibleError = apiError ?? firstQueueError;

  const loadQueue = useCallback(async (view: QueueView) => {
    setLoadingQueues((current) => ({ ...current, [view]: true }));
    try {
      const items = await api.listPhysicianReviews(view);
      setQueues((current) => ({ ...current, [view]: items }));
      setQueueErrors((current) => ({ ...current, [view]: undefined }));
      setApiError(null);
    } catch (cause) {
      setQueueErrors((current) => ({ ...current, [view]: cause }));
      setApiError(cause);
    } finally {
      setLoadingQueues((current) => ({ ...current, [view]: false }));
    }
  }, []);

  const loadAllQueues = useCallback(async () => {
    const results = await Promise.all(queueViews.map(async (view) => {
      try {
        return { items: await api.listPhysicianReviews(view), view } as const;
      } catch (cause) {
        return { cause, view } as const;
      }
    }));
    const nextQueues = { ...emptyQueues };
    const nextErrors: Partial<Record<QueueView, unknown>> = {};
    let firstError: unknown;
    for (const result of results) {
      if ("items" in result) nextQueues[result.view] = result.items ?? [];
      else {
        nextErrors[result.view] = result.cause;
        firstError ??= result.cause;
      }
    }
    setQueues(nextQueues);
    setQueueErrors(nextErrors);
    setApiError(firstError ?? null);
    setLoadingQueues({ pending: false, claimed: false, approved: false });
  }, []);

  useEffect(() => {
    void loadAllQueues();
  }, [loadAllQueues]);

  useEffect(() => {
    void Promise.all([api.listSupplementCatalogue(), api.listCatalogueFoods()])
      .then(([supplements, foods]) => {
        setSupplementCatalogue(supplements);
        setFoodCatalogue(foods);
      })
      .catch((cause) => setApiError(cause));
  }, []);

  function changeSection(section: SpecialistSection, clearSelected = true) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.set("section", section);
      return next;
    }, { replace: true });
    if (clearSelected) clearSelectedReview();
  }

  function clearSelectedReview() {
    setSelectedPlan(null);
    setSelectedReview(null);
    setSelectedSourceView(null);
    setReadOnly(false);
    setLabs([]);
    setOrders([]);
    setNotes("");
    setInternalNotes("");
    setTests("CBC");
    setOrderForm(emptyOrder);
    setEditingOrderId(null);
  }

  async function openReview(review: Review, sourceView: QueueView = activeQueueView) {
    setBusy(true);
    setApiError(null);
    clearSelectedReview();
    setSelectedReview(review);
    setSelectedSourceView(sourceView);
    setReadOnly(sourceView === "approved");
    try {
      if (review.status === "pending") await api.claimPhysicianReview(review.review_id);
      const [plan, documents, planOrders] = await Promise.all([
        api.getPhysicianPlan(review.plan_id),
        api.listPhysicianLabs(review.plan_id),
        api.listPhysicianSupplementOrders(review.plan_id),
      ]);
      setSelectedReview({ ...review, status: review.status === "pending" ? "in_review" : review.status });
      setSelectedPlan(plan);
      setLabs(documents);
      setOrders(planOrders);
      await loadQueue(sourceView);
    } catch (cause) {
      setApiError(cause);
    } finally {
      setBusy(false);
    }
  }

  async function act(action: PhysicianAction) {
    if (!selectedPlan || ((action === "request_changes" || action === "reject") && !notes.trim())) return;
    setBusy(true);
    setApiError(null);
    try {
      const updated = await api.actOnPhysicianPlan(
        selectedPlan.id,
        action,
        notes.trim() || null,
        internalNotes.trim() || null,
      );
      setSelectedPlan(updated);
      if (selectedReview && updated.physician_review_status) setSelectedReview({ ...selectedReview, status: updated.physician_review_status });
      await loadQueue(selectedSourceView ?? activeQueueView);
    } catch (cause) {
      setApiError(cause);
    } finally {
      setBusy(false);
    }
  }

  function orderPayload(): PhysicianSupplementOrderInput | null {
    if (!orderForm.supplementId || !orderForm.instructions.trim() || !orderForm.rationale.trim()) return null;
    return {
      supplement_id: orderForm.supplementId,
      dose_amount: Number(orderForm.doseAmount),
      dose_unit: orderForm.doseUnit,
      daily_units: Number(orderForm.dailyUnits),
      frequency: orderForm.frequency,
      duration_days: Number(orderForm.durationDays),
      instructions: orderForm.instructions,
      rationale: orderForm.rationale,
      rationale_user_visible: true,
      linked_gap_codes: [],
      linked_lab_document_ids: [],
    };
  }

  async function saveOrder() {
    if (!selectedPlan) return;
    const payload = orderPayload();
    if (!payload) return;
    try {
      if (editingOrderId) await api.updatePhysicianSupplementOrder(editingOrderId, payload);
      else await api.createPhysicianSupplementOrder(selectedPlan.id, payload);
      setOrders(await api.listPhysicianSupplementOrders(selectedPlan.id));
      setEditingOrderId(null);
      setOrderForm(emptyOrder);
    } catch (cause) {
      setApiError(cause);
    }
  }

  function editOrder(order: SupplementOrder) {
    setEditingOrderId(order.id);
    setOrderForm({
      supplementId: order.supplement_id,
      doseAmount: String(order.dose_amount),
      doseUnit: order.dose_unit,
      dailyUnits: String(order.daily_units),
      frequency: order.frequency,
      durationDays: String(order.duration_days),
      instructions: order.instructions,
      rationale: order.rationale ?? "",
    });
  }

  async function transitionOrder(orderId: string, status: SupplementTransition) {
    if (!selectedPlan) return;
    try {
      await api.transitionPhysicianSupplementOrder(orderId, status);
      setOrders(await api.listPhysicianSupplementOrders(selectedPlan.id));
    } catch (cause) {
      setApiError(cause);
    }
  }

  function adjustFoodQuantity(mealId: string, foodId: string, grams: number) {
    if (!selectedPlan) return;
    void api.adjustPhysicianFoodQuantity(selectedPlan.id, mealId, foodId, grams)
      .then(setSelectedPlan)
      .catch((cause) => setApiError(cause));
  }

  function replaceFood(mealId: string, foodId: string, replacementFoodId: string) {
    if (!selectedPlan) return;
    void api.replacePhysicianFood(selectedPlan.id, mealId, foodId, replacementFoodId)
      .then(setSelectedPlan)
      .catch((cause) => setApiError(cause));
  }

  function requestLabs(requestedTests: string[]) {
    if (!selectedPlan) return;
    void api.requestPhysicianLabs(
      selectedPlan.id,
      requestedTests,
      notes || l("برای بررسی ایمن‌تر برنامه", "For a safer plan review"),
    ).catch((cause) => setApiError(cause));
  }

  function reviewLab(documentId: string, status: LabReviewStatus) {
    void api.reviewPhysicianLab(documentId, status, notes || null)
      .then((updated) => setLabs((items) => items.map((item) => item.id === updated.id ? updated : item)))
      .catch((cause) => setApiError(cause));
  }

  const counts = {
    history: queues.approved.length,
    mine: queues.claimed.length,
    queue: queues.pending.length,
  };

  return (
    <SpecialistWorkbenchShell
      counts={counts}
      description={l("پرونده‌ها، آزمایش‌ها و نسخه‌های تغذیه را در یک جریان روشن بررسی کن.", "Review nutrition cases, lab documents, and plans in one clear workflow.")}
      error={<AppErrorNotice audience="physician" context="specialist_review" error={visibleError} locale={fa ? "fa" : "en"} />}
      fa={fa}
      headerAction={<button className="physician-review-back" onClick={() => navigate(-1)} type="button">{l("بازگشت", "Back")}</button>}
      onSectionChange={(section) => changeSection(section)}
      role="physician"
      title={l("میز کار پزشک", "Physician workbench")}
      activeSection={activeSection}
    >
      {selectedPlan && selectedReview ? (
        <PhysicianReviewCase
          busy={busy}
          fa={fa}
          foodCatalogue={foodCatalogue}
          internalNotes={internalNotes}
          labs={labs}
          notes={notes}
          onAct={(action) => void act(action)}
          onAdjustFoodQuantity={adjustFoodQuantity}
          onBack={clearSelectedReview}
          onEditOrder={editOrder}
          onInternalNotesChange={setInternalNotes}
          onNotesChange={setNotes}
          onOrderFormChange={(patch) => setOrderForm((current) => ({ ...current, ...patch }))}
          onReplaceFood={replaceFood}
          onRequestLabs={requestLabs}
          onReviewLab={reviewLab}
          onSaveOrder={() => void saveOrder()}
          onTestsChange={setTests}
          onTransitionOrder={transitionOrder}
          orderForm={orderForm}
          orders={orders}
          plan={selectedPlan}
          readOnly={readOnly}
          review={selectedReview}
          supplementCatalogue={supplementCatalogue}
          tests={tests}
        />
      ) : activeSection === "dashboard" ? (
        allQueuesLoading ? <p className="specialist-workbench-loading" role="status">{l("در حال آماده‌سازی داشبورد…", "Preparing dashboard…")}</p> : (
          <PhysicianDashboard
            approved={queues.approved}
            claimed={queues.claimed}
            fa={fa}
            onOpenCase={(item, sourceView) => void openReview(item, sourceView)}
            onSectionChange={changeSection}
            pending={queues.pending}
          />
        )
      ) : (
        <PhysicianReviewQueue
          busy={busy}
          fa={fa}
          items={queues[activeQueueView]}
          loading={currentQueueLoading}
          onOpenReview={(item) => void openReview(item, activeQueueView)}
          selectedReviewId={selectedReview?.review_id}
          view={activeQueueView}
        />
      )}
    </SpecialistWorkbenchShell>
  );
}

function readSection(value: string | null): SpecialistSection {
  return value === "queue" || value === "mine" || value === "history" ? value : "dashboard";
}

function queueViewForSection(section: SpecialistSection): QueueView {
  if (section === "mine") return "claimed";
  if (section === "history") return "approved";
  return "pending";
}
