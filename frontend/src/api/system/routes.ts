import { http } from "@/utils/http";
import type { ApiResult } from "../types";

export type AsyncRoutesResult = ApiResult<{
  routes: any[];
  permissions: string[];
  roles: { id: number; code: string; name: string }[];
}>;

/** 获取当前用户的动态路由 + 权限 + 角色，后端返回 Pure Admin 格式 */
export const getAsyncRoutes = () =>
  http.get<AsyncRoutesResult>("/api/v1/routes");
