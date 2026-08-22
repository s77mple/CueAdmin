import { http } from "@/utils/http";
import type { ApiResult } from "./types";

export const getPermissionList = () =>
  http.get<ApiResult<any>>("/api/v1/system/permissions");
export const createPermission = (data?: object) =>
  http.post<ApiResult<any>>("/api/v1/system/permissions", { data });
export const updatePermission = (id: number, data?: object) =>
  http.put<ApiResult<any>>(`/api/v1/system/permissions/${id}`, { data });
export const deletePermission = (id: number) =>
  http.delete<ApiResult>(`/api/v1/system/permissions/${id}`);
