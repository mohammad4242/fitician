import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { deleteAdminExercise, getAdminExercises } from "../admin/api";
import { getExerciseCategories, getExercises } from "./api";
import { ExerciseCatalog, type CatalogSource } from "./ExerciseCatalog";

export function ExerciseCatalogPage() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const source = useMemo<CatalogSource>(() => ({
    categories: getExerciseCategories,
    list: (filters, status) => status === undefined ? getExercises(filters)
      : getAdminExercises({ ...filters,
          is_active: status === "inactive" ? false : undefined,
          needs_review: status === "needs_review" ? true : undefined,
        }),
    delete: deleteAdminExercise,
  }), []);
  return <ExerciseCatalog source={source} searchParams={searchParams}
    setSearchParams={setSearchParams} isAdmin={user?.is_admin === true} />;
}
