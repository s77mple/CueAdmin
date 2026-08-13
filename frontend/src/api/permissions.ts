import { http } from "@/utils/http";
import type { ApiResult } from "./types";

export const getPermissionList = () =>
  http.request<ApiResult<any>>("get", "/api/v1/permissions");
export const createPermission = (data?: object) =>
  http.request<ApiResult<any>>("post", "/api/v1/permissions", { data });
export const updatePermission = (id: number, data?: object) =>
  http.request<ApiResult<any>>("put", `/api/v1/permissions/${id}`, { data });
export const patchPermission = (id: number, data?: object) =>
  http.request<ApiResult<any>>("patch", `/api/v1/permissions/${id}`, { data });
export const deletePermission = (id: number) =>
  http.request<ApiResult>("delete", `/api/v1/permissions/${id}`);
