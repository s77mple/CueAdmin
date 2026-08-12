import { http } from "@/utils/http";
import type { ApiResult, PageData } from "./types";

export const getRoleList = (params?: object) =>
  http.request<ApiResult<PageData<any>>>("get", "/api/v1/roles", { params });
export const createRole = (data?: object) =>
  http.request<ApiResult<any>>("post", "/api/v1/roles", { data });
export const updateRole = (id: number, data?: object) =>
  http.request<ApiResult<any>>("put", `/api/v1/roles/${id}`, { data });
export const patchRole = (id: number, data?: object) =>
  http.request<ApiResult<any>>("patch", `/api/v1/roles/${id}`, { data });
export const deleteRole = (id: number) =>
  http.request<ApiResult>("delete", `/api/v1/roles/${id}`);
