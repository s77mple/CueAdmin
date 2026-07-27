import { http } from "@/utils/http";
import type { ApiResult } from "@/api/user";

export const getAsyncRoutes = () => {
  // CueAdmin 后端不提供动态路由，返回空数组，使用前端静态路由
  return new Promise<ApiResult<[]>>((resolve) => {
    resolve({ code: 0, message: "ok", data: [] });
  });
};
