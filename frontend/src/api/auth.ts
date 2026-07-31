import { http } from "@/utils/http";
import type { ApiResult } from "./types";

// 后端 /auth/login 返回的 data（含 token）
export type LoginResult = ApiResult<{
  access_token: string;
  user: { id: number; username: string; display_name: string; phone: string | null; is_active: boolean };
  permissions: string[];
  roles: { id: number; code: string; name: string }[];
  menus: { code: string; name: string; icon: string; path: string; parent_id: number | null; sort_order: number }[];
}>;

// 后端 /auth/me 返回的 data（不含 token）
export type MeResult = ApiResult<{
  user: { id: number; username: string; display_name: string; phone: string | null; is_active: boolean };
  permissions: string[];
  roles: { id: number; code: string; name: string }[];
  menus: { code: string; name: string; icon: string; path: string; parent_id: number | null; sort_order: number }[];
}>;

export const getLogin = (data?: object) =>
  http.request<LoginResult>("post", "/api/v1/auth/login", { data });
export const getMe = () =>
  http.request<MeResult>("get", "/api/v1/auth/me");
export const logout = () =>
  http.request("post", "/api/v1/auth/logout");
export const updateProfile = (data?: object) =>
  http.request("put", "/api/v1/auth/profile", { data });
