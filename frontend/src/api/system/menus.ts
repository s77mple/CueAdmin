import { http } from "@/utils/http";
import type { ApiResult, ListData } from "../types";
import type { Menu, MenuBrief } from "./types";

export const getMenuList = () =>
  http.get<ApiResult<ListData<Menu>>>("/api/v1/system/menus");
export const createMenu = (data?: object) =>
  http.post<ApiResult<MenuBrief>>("/api/v1/system/menus", { data });
export const updateMenu = (id: number, data?: object) =>
  http.put<ApiResult<MenuBrief>>(`/api/v1/system/menus/${id}`, { data });
export const deleteMenu = (id: number) =>
  http.delete<ApiResult>(`/api/v1/system/menus/${id}`);
