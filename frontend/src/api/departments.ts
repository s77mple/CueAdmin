import { http } from "@/utils/http";
import type { ApiResult } from "./types";

export const getDepartmentList = (params?: object) =>
  http.get<ApiResult<{ items: any[]; total: number }>>("/api/v1/system/departments", { params });
export const createDepartment = (data?: object) =>
  http.post<ApiResult<any>>("/api/v1/system/departments", { data });
export const updateDepartment = (id: number, data?: object) =>
  http.put<ApiResult<any>>(`/api/v1/system/departments/${id}`, { data });
export const deleteDepartment = (id: number) =>
  http.delete<ApiResult>(`/api/v1/system/departments/${id}`);
