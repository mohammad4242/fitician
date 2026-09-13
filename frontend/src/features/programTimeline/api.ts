import { request } from "../../shared/apiClient";
import type { ProgramTimelineToday } from "./types";

const timelinePath = "/api/v1/program-timeline/today";

export function getProgramTimelineToday(timezone?: string): Promise<ProgramTimelineToday> {
  const query = timezone
    ? `?${new URLSearchParams({ timezone }).toString()}`
    : "";
  return request<ProgramTimelineToday>(`${timelinePath}${query}`);
}

