import { http } from "@/utils/http";
import type { ApiResult, PageData } from "./types";

export const getDepartmentList = (params?: object) =>
  http.get<ApiResult<PageData<any>>>("/api/v1/departments", { params });
export const createDepartment = (data?: object) =>
  http.post<ApiResult<any>>("/api/v1/departments", { data });
export const updateDepartment = (id: number, data?: object) =>
  http.put<ApiResult<any>>(`/api/v1/departments/${id}`, { data });
export const deleteDepartment = (id: number) =>
  http.delete<ApiResult>(`/api/v1/departments/${id}`);
