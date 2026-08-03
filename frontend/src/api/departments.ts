import { http } from "@/utils/http";
import type { ApiResult, PageData } from "./types";

export const getDepartmentList = (params?: object) =>
  http.request<ApiResult<PageData<any>>>("get", "/api/v1/departments", { params });
export const createDepartment = (data?: object) =>
  http.request<ApiResult<any>>("post", "/api/v1/departments", { data });
export const updateDepartment = (id: number, data?: object) =>
  http.request<ApiResult<any>>("put", `/api/v1/departments/${id}`, { data });
export const deleteDepartment = (id: number) =>
  http.request<ApiResult>("delete", `/api/v1/departments/${id}`);
