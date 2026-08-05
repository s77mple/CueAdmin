import { http } from "@/utils/http";
import type { ApiResult } from "./types";

export const getMenuList = () =>
  http.request<ApiResult<any>>("get", "/api/v1/menus");
export const createMenu = (data?: object) =>
  http.request<ApiResult<any>>("post", "/api/v1/menus", { data });
export const updateMenu = (id: number, data?: object) =>
  http.request<ApiResult<any>>("put", `/api/v1/menus/${id}`, { data });
export const patchMenu = (id: number, data?: object) =>
  http.request<ApiResult<any>>("patch", `/api/v1/menus/${id}`, { data });
export const deleteMenu = (id: number) =>
  http.request<ApiResult>("delete", `/api/v1/menus/${id}`);
