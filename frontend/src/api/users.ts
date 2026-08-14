import { http } from "@/utils/http";
import type { ApiResult, PageData } from "./types";

export const getUserList = (params?: object) =>
  http.get<ApiResult<PageData<any>>>("/api/v1/users", { params });
export const createUser = (data?: object) =>
  http.post<ApiResult<any>>("/api/v1/users", { data });
export const updateUser = (id: number, data?: object) =>
  http.put<ApiResult<any>>(`/api/v1/users/${id}`, { data });
export const patchUser = (id: number, data?: object) =>
  http.patch<ApiResult<any>>(`/api/v1/users/${id}`, { data });
export const deleteUser = (id: number) =>
  http.delete<ApiResult>(`/api/v1/users/${id}`);
/** 彻底删除（仅限已禁用的用户） */
export const hardDeleteUser = (id: number) =>
  http.delete<ApiResult>(`/api/v1/users/${id}`, { params: { hard: true } });
