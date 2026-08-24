import { http } from "@/utils/http";
import type { ApiResult, PageData } from "../types";
import type { Role, RoleBrief } from "./types";

export const getRoleList = (params?: object) =>
  http.get<ApiResult<PageData<Role>>>("/api/v1/system/roles", { params });
export const createRole = (data?: object) =>
  http.post<ApiResult<RoleBrief>>("/api/v1/system/roles", { data });
export const updateRole = (id: number, data?: object) =>
  http.put<ApiResult<RoleBrief>>(`/api/v1/system/roles/${id}`, { data });
export const deleteRole = (id: number) =>
  http.delete<ApiResult>(`/api/v1/system/roles/${id}`);
