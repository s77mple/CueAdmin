import { http } from "@/utils/http";
import type { ApiResult } from "./types";

/** 获取当前用户有权限的动态路由，后端返回 Pure Admin 格式 */
export const getAsyncRoutes = () =>
  http.request<ApiResult<[]>>("get", "/api/v1/routes");
