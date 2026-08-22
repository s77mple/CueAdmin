import { http } from "@/utils/http";
import type { ApiResult } from "./types";

/** 错误码数据字典 — 后端 app/core/exceptions.py 自动生成 */
export const getErrorCodes = () =>
  http.get<ApiResult<any[]>>("/api/v1/system/meta/error-codes");
