import { http } from "@/utils/http";
import type { ApiResult, PageData } from "./types";

export const getPermissionList = (params?: object) =>
  http.request<ApiResult<PageData<any>>>("get", "/api/v1/permissions", { params });
export const createPermission = (data?: object) =>
  http.request<ApiResult<any>>("post", "/api/v1/permissions", { data });
export const updatePermission = (id: number, data?: object) =>
  http.request<ApiResult<any>>("put", `/api/v1/permissions/${id}`, { data });
export const patchPermission = (id: number, data?: object) =>
  http.request<ApiResult<any>>("patch", `/api/v1/permissions/${id}`, { data });
export const deletePermission = (id: number) =>
  http.request<ApiResult>("delete", `/api/v1/permissions/${id}`);
