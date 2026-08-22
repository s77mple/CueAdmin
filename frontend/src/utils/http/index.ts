import Axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type CustomParamsSerializer
} from "axios";
import type {
  PureHttpError,
  RequestMethods,
  PureHttpResponse,
  PureHttpRequestConfig
} from "./types.d";
import { stringify } from "qs";
import { message } from "@/utils/message";
import { getToken, formatToken, removeToken, updateToken } from "@/utils/auth";
import { router } from "@/router";
import { ErrorCode } from "@/constants/error-code";

const defaultConfig: AxiosRequestConfig = {
  // 后端地址：读环境变量 VITE_API_BASE_URL；未配置则为空字符串 → 请求保持相对路径，走 Vite dev proxy（开发）/ nginx 反代（生产）
  baseURL: import.meta.env.VITE_API_BASE_URL || "",
  timeout: 10000,
  headers: {
    Accept: "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest"
  },
  paramsSerializer: {
    serialize: stringify as unknown as CustomParamsSerializer
  }
};

// 刷新令牌专用的裸 axios 实例：不挂任何拦截器，避免刷新请求自身又触发「过期→刷新」死循环
const refreshHttp: AxiosInstance = Axios.create(defaultConfig);

// 并发刷新控制：多个请求同时 11002 时只发一次刷新，其余排队等新 token
let isRefreshing = false;
let pendingQueue: Array<{
  resolve: (value: any) => void;
  reject: (reason?: any) => void;
}> = [];

/** 清空登录态并跳登录页（刷新失败 / 令牌作废时调用） */
function forceLogout() {
  removeToken();
  router.push("/login");
}

class PureHttp {
  constructor() {
    this.httpInterceptorsRequest();
    this.httpInterceptorsResponse();
  }

  private static initConfig = {} as PureHttpRequestConfig;

  private static axiosInstance: AxiosInstance = Axios.create(defaultConfig);

  /** 请求拦截 — 自动带 token */
  private httpInterceptorsRequest(): void {
    PureHttp.axiosInstance.interceptors.request.use(
      config => {
        // 白名单：不需要 token 的接口（精确匹配路径末尾）
        const whiteList = ["/auth/login"];
        const isWhite = whiteList.some(url => config.url?.endsWith(url));

        if (!isWhite) {
          const token = getToken();
          if (token?.accessToken) {
            config.headers["Authorization"] = formatToken(token.accessToken);
          }
        }
        return config;
      },
      error => Promise.reject(error)
    );
  }

  /** 响应拦截 — 统一处理业务 code + 401 跳转 + access 过期自动刷新 */
  private httpInterceptorsResponse(): void {
    PureHttp.axiosInstance.interceptors.response.use(
      (response: PureHttpResponse) => {
        const res = response.data;

        // access 过期 → 用 refresh 换新后重试原请求（对调用方透明）
        if (res.code === ErrorCode.AUTH_TOKEN_EXPIRED) {
          return this.handleTokenExpired(response);
        }
        if (
          res.code === ErrorCode.AUTH_TOKEN_REVOKED ||
          res.code === ErrorCode.AUTH_TOKEN_INVALID
        ) {
          message("登录已过期，请重新登录", { type: "warning" });
          forceLogout();
          return Promise.reject(new Error(res.message));
        }
        if (res.code === ErrorCode.ACCESS_DENIED) {
          message("权限不足", { type: "error" });
          return Promise.reject(new Error(res.message));
        }
        return response.data;
      },
      (error: PureHttpError) => {
        // 请求被取消（如路由跳转），不弹 toast
        if (Axios.isCancel(error)) {
          return Promise.reject(error);
        }
        const httpCode = error?.response?.status;
        if (httpCode === 401) {
          message("未授权，请登录", { type: "warning" });
          forceLogout();
        } else if (httpCode === 500) {
          message("服务器繁忙，请稍后重试", { type: "error" });
        } else if (error.code === 'ECONNABORTED') {
          message("请求超时，请重试", { type: "error" });
        } else if (!error?.response) {
          message("网络异常，请检查网络连接", { type: "error" });
        }
        return Promise.reject(error);
      }
    );
  }

  /** access 过期处理：刷新令牌 → 重试原请求；并发 401 只刷一次 */
  private async handleTokenExpired(response: PureHttpResponse): Promise<any> {
    const originalConfig = response.config;

    // 已重试过一次仍过期 → 放弃，直接登出（避免死循环）
    if (originalConfig._retry) {
      message("登录已过期，请重新登录", { type: "warning" });
      forceLogout();
      return Promise.reject(new Error("登录已过期，请重新登录"));
    }

    const refreshToken = getToken()?.refreshToken;
    if (!refreshToken) {
      message("登录已过期，请重新登录", { type: "warning" });
      forceLogout();
      return Promise.reject(new Error("登录已过期，请重新登录"));
    }

    // 已有刷新在进行 → 排队，等新 token 下发后各自重试
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pendingQueue.push({
          resolve: (newToken: string) => {
            originalConfig.headers["Authorization"] = formatToken(newToken);
            originalConfig._retry = true;
            resolve(PureHttp.axiosInstance.request(originalConfig));
          },
          reject
        });
      });
    }

    isRefreshing = true;
    try {
      const res = await refreshHttp.post("/api/v1/auth/refresh", {
        refresh_token: refreshToken
      });
      const data = res.data;
      if (data.code === 0) {
        const { access_token, refresh_token } = data.data;
        updateToken({ accessToken: access_token, refreshToken: refresh_token });
        // 唤醒排队的请求，用新 token 各自重试
        pendingQueue.forEach(({ resolve }) => resolve(access_token));
        pendingQueue = [];
        // 重试原请求
        originalConfig.headers["Authorization"] = formatToken(access_token);
        originalConfig._retry = true;
        return PureHttp.axiosInstance.request(originalConfig);
      }
      throw new Error(data.message || "刷新令牌失败");
    } catch (e) {
      // 刷新失败（refresh 也过期/被撤销/被盗）→ 清空登录态，排队的请求全部拒绝
      message("登录已过期，请重新登录", { type: "warning" });
      pendingQueue.forEach(({ reject }) => reject(e));
      pendingQueue = [];
      forceLogout();
      return Promise.reject(e);
    } finally {
      isRefreshing = false;
    }
  }

  public request<T>(
    method: RequestMethods,
    url: string,
    param?: AxiosRequestConfig,
    axiosConfig?: PureHttpRequestConfig
  ): Promise<T> {
    const config = { method, url, ...param, ...axiosConfig } as PureHttpRequestConfig;
    return PureHttp.axiosInstance.request(config) as Promise<T>;
  }

  public post<T>(url: string, params?: AxiosRequestConfig, config?: PureHttpRequestConfig): Promise<T> {
    return this.request<T>("post", url, params, config);
  }

  public get<T>(url: string, params?: AxiosRequestConfig, config?: PureHttpRequestConfig): Promise<T> {
    return this.request<T>("get", url, params, config);
  }

  public put<T>(url: string, params?: AxiosRequestConfig, config?: PureHttpRequestConfig): Promise<T> {
    return this.request<T>("put", url, params, config);
  }

  public patch<T>(url: string, params?: AxiosRequestConfig, config?: PureHttpRequestConfig): Promise<T> {
    return this.request<T>("patch", url, params, config);
  }

  public delete<T>(url: string, params?: AxiosRequestConfig, config?: PureHttpRequestConfig): Promise<T> {
    return this.request<T>("delete", url, params, config);
  }
}

export const http = new PureHttp();
