import { http } from "@/utils/http";
import type { ApiResult, PageData } from "./types";

export const getRoleList = (params?: object) =>
  http.get<ApiResult<PageData<any>>>("/api/v1/system/roles", { params });
export const createRole = (data?: object) =>
  http.post<ApiResult<any>>("/api/v1/system/roles", { data });
export const updateRole = (id: number, data?: object) =>
  http.put<ApiResult<any>>(`/api/v1/system/roles/${id}`, { data });
export const deleteRole = (id: number) =>
  http.delete<ApiResult>(`/api/v1/system/roles/${id}`);
