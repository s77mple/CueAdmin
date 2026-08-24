import { http } from "@/utils/http";
import type { ApiResult, ListData } from "../types";
import type { Permission, PermissionBrief } from "./types";

export const getPermissionList = () =>
  http.get<ApiResult<ListData<Permission>>>("/api/v1/system/permissions");
export const createPermission = (data?: object) =>
  http.post<ApiResult<PermissionBrief>>("/api/v1/system/permissions", { data });
export const updatePermission = (id: number, data?: object) =>
  http.put<ApiResult<PermissionBrief>>(`/api/v1/system/permissions/${id}`, {
    data
  });
export const deletePermission = (id: number) =>
  http.delete<ApiResult>(`/api/v1/system/permissions/${id}`);
