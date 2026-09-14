import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { useMobileAuth } from "../../../auth/MobileAuthProvider";
import { nutritionKeys } from "../../../data/queryKeys";
import { Notice, PageHeading, Skeleton } from "../../../ui/components";
import { getMobileViewState } from "../../../ui/requestState";
import { Screen } from "../../../ui/layout";
import { RouteGuard } from "../../../ui/navigation/RouteGuards";
import { NutritionPlanSection } from "../../../nutrition/NutritionPlanSection";
import { createNutritionApi } from "../../../nutrition/nutritionApi";

export default function MemberNutritionPlanRoute() {
  const auth = useMobileAuth();
  const api = useMemo(() => createNutritionApi(auth.request), [auth.request]);
  const safetyQuery = useQuery({
    queryFn: api.getSafety,
    queryKey: nutritionKeys.safety(),
  });
  const safetyState = getMobileViewState(safetyQuery, {
    audience: "member",
    context: "nutrition",
  });

  return (
    <RouteGuard kind="member" requiredCapability="nutrition">
      <Screen contentWidth="reading">
        <PageHeading
          compact
          eyebrow="تغذیه"
          supportingText="نسخه فعال، تاریخچه و تغییرهای مجاز برنامه غذایی را اینجا مدیریت کن."
          title="برنامه غذایی"
        />
        {safetyState.status === "loading" ? <Skeleton height={180} /> : null}
        {safetyState.status === "error" ? <Notice message={safetyState.error.message} variant="danger" /> : null}
        {safetyState.status !== "loading" && safetyState.status !== "error" ? (
          <NutritionPlanSection safety={safetyQuery.data ?? null} />
        ) : null}
      </Screen>
    </RouteGuard>
  );
}
