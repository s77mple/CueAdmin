import { http } from "@/utils/http";
import type { ApiResult, PageData } from "./types";

export const getUserList = (params?: object) =>
  http.request<ApiResult<PageData<any>>>("get", "/api/v1/users", { params });
export const getUserDetail = (id: number) =>
  http.request<ApiResult<any>>("get", `/api/v1/users/${id}`);
export const createUser = (data?: object) =>
  http.request<ApiResult<any>>("post", "/api/v1/users", { data });
export const updateUser = (id: number, data?: object) =>
  http.request<ApiResult<any>>("put", `/api/v1/users/${id}`, { data });
export const deleteUser = (id: number) =>
  http.request<ApiResult>("delete", `/api/v1/users/${id}`);
