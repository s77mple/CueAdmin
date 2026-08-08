import { http } from "@/utils/http";
import type { ApiResult } from "./types";

export const getRoleList = () =>
  http.request<ApiResult<any>>("get", "/api/v1/roles");
export const createRole = (data?: object) =>
  http.request<ApiResult<any>>("post", "/api/v1/roles", { data });
export const updateRole = (id: number, data?: object) =>
  http.request<ApiResult<any>>("put", `/api/v1/roles/${id}`, { data });
export const patchRole = (id: number, data?: object) =>
  http.request<ApiResult<any>>("patch", `/api/v1/roles/${id}`, { data });
export const deleteRole = (id: number) =>
  http.request<ApiResult>("delete", `/api/v1/roles/${id}`);
