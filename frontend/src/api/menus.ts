import { http } from "@/utils/http";
import type { ApiResult } from "./types";

export const getMenuList = () =>
  http.get<ApiResult<any>>("/api/v1/system/menus");
export const createMenu = (data?: object) =>
  http.post<ApiResult<any>>("/api/v1/system/menus", { data });
export const updateMenu = (id: number, data?: object) =>
  http.put<ApiResult<any>>(`/api/v1/system/menus/${id}`, { data });
export const deleteMenu = (id: number) =>
  http.delete<ApiResult>(`/api/v1/system/menus/${id}`);
