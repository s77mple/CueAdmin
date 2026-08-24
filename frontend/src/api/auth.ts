import { http } from "@/utils/http";
import type { ApiResult } from "./types";
import type { PureHttpRequestConfig } from "@/utils/http/types";

// 后端 /auth/login 返回的 data（含 token）
export type LoginResult = ApiResult<{
  access_token: string;
  refresh_token: string;
  user: { id: number; username: string; display_name: string; phone: string | null; is_active: boolean };
  permissions: string[];
  roles: { id: number; code: string; name: string }[];
}>;

export const getLogin = (data?: object) =>
  http.post<LoginResult>("/api/v1/auth/login", { data });
export const logout = (token?: string) =>
  http.post(
    "/api/v1/auth/logout",
    undefined,
    token ? ({ headers: { Authorization: `Bearer ${token}` } } as PureHttpRequestConfig) : undefined
  );
