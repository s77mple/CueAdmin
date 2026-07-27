import type { ApiResult } from "@/api/types";

export const getAsyncRoutes = () => {
  // CueAdmin 后端不提供动态路由，返回空数组，使用前端静态路由
  return new Promise<ApiResult<[]>>((resolve) => {
    resolve({ code: 0, message: "ok", data: [] });
  });
};
