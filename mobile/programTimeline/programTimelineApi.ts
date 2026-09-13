import type { TransportRequest } from "@fitician/core";
import type { ProgramTimelineToday } from "@fitician/core/program-timeline";

const TODAY_PATH = "/api/v1/program-timeline/today";

export type ProgramTimelineRequest = <TResponse>(
  request: TransportRequest,
) => Promise<TResponse>;

export interface ProgramTimelineApi {
  getToday(timezone: string): Promise<ProgramTimelineToday>;
}

export function createProgramTimelineApi(request: ProgramTimelineRequest): ProgramTimelineApi {
  return {
    getToday: (timezone) => request<ProgramTimelineToday>({
      method: "GET",
      path: `${TODAY_PATH}?timezone=${encodeURIComponent(timezone)}`,
    }),
  };
}
