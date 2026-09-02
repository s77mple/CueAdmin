import { http } from "@/utils/http";
import type { ApiResult, ListData } from "../types";
import type { Department, DepartmentBrief } from "./types";

export const getDepartmentList = (params?: object) =>
  http.get<ApiResult<ListData<Department>>>("/api/v1/system/departments", {
    params
  });
export const getDepartment = (id: number) =>
  http.get<ApiResult<Department>>(`/api/v1/system/departments/${id}`);
export const createDepartment = (data?: object) =>
  http.post<ApiResult<DepartmentBrief>>("/api/v1/system/departments", { data });
export const updateDepartment = (id: number, data?: object) =>
  http.put<ApiResult<DepartmentBrief>>(`/api/v1/system/departments/${id}`, {
    data
  });
export const deleteDepartment = (id: number) =>
  http.delete<ApiResult>(`/api/v1/system/departments/${id}`);
