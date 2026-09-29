import { createCommunicationApi, type CommunicationRequest } from "@fitician/core";
import { request } from "../../shared/apiClient";
const communicationRequest: CommunicationRequest = input => request(input.path, { method: input.method, body: input.body === undefined ? undefined : JSON.stringify(input.body) });
export const communicationApi = createCommunicationApi(communicationRequest);
