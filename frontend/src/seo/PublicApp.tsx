import { SeoHead } from "./SeoHead";
import type { PublicPayload } from "./registry";
import { PublicPage } from "./PublicPage";
export function PublicApp({ payload }: { payload: PublicPayload }) {
  return <><SeoHead seo={payload.seo} /><PublicPage payload={payload} /></>;
}
