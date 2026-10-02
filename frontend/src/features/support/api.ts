import { createSupportApi, type SupportRequest } from '@fitician/core';
import { request } from '../../shared/apiClient';
const send:SupportRequest = input => request(input.path,{method:input.method,body:input.body===undefined?undefined:JSON.stringify(input.body)});
export const supportApi=createSupportApi(send);
export const adminSupportApi=createSupportApi(send,true);
