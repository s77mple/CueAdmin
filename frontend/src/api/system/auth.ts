import { http } from "@/utils/http";
import type { ApiResult } from "../types";
import type { PureHttpRequestConfig } from "@/utils/http/types";
import type { User, RoleBrief } from "./types";

// 后端 /auth/login 返回的 data（含 token）
export type LoginResult = ApiResult<{
  access_token: string;
  refresh_token: string;
  user: User;
  permissions: string[];
  roles: RoleBrief[];
}>;

export const getLogin = (data?: object) =>
  http.post<LoginResult>("/api/v1/auth/login", { data });
export const logout = (token?: string) =>
  http.post(
    "/api/v1/auth/logout",
    undefined,
    token
      ? ({
          headers: { Authorization: `Bearer ${token}` }
        } as PureHttpRequestConfig)
      : undefined
  );
