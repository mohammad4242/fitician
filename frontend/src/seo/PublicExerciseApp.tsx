import { SeoHead } from "./SeoHead";
import type { PublicPayload } from "./registry";
import { PublicExercisePage } from "./PublicExercises";
export function PublicExerciseApp({ payload }: { payload: PublicPayload }) {
  return <><SeoHead seo={payload.seo} /><PublicExercisePage payload={payload} /></>;
}
