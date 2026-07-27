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
import { getToken, formatToken, removeToken } from "@/utils/auth";
import { router } from "@/router";

const defaultConfig: AxiosRequestConfig = {
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

class PureHttp {
  constructor() {
    this.httpInterceptorsRequest();
    this.httpInterceptorsResponse();
  }

  private static initConfig: PureHttpRequestConfig = {};

  private static axiosInstance: AxiosInstance = Axios.create(defaultConfig);

  /** 请求拦截 — 自动带 token */
  private httpInterceptorsRequest(): void {
    PureHttp.axiosInstance.interceptors.request.use(
      (config: PureHttpRequestConfig) => {
        // 白名单：不需要 token 的接口
        const whiteList = ["/login"];
        const isWhite = whiteList.some(url => config.url?.includes(url));

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

  /** 响应拦截 — 统一处理业务 code + 401 跳转 */
  private httpInterceptorsResponse(): void {
    PureHttp.axiosInstance.interceptors.response.use(
      (response: PureHttpResponse) => {
        const res = response.data;

        // 未登录 → 跳登录页
        if (res.code === 11002 || res.code === 11003) {
          message("登录已过期，请重新登录", { type: "warning" });
          removeToken();
          router.push("/login");
          return Promise.reject(new Error(res.message));
        }

        // 权限不足
        if (res.code === 16001) {
          message("权限不足", { type: "error" });
          return Promise.reject(new Error(res.message));
        }

        return response.data;
      },
      (error: PureHttpError) => {
        const httpCode = error?.response?.status;
        if (httpCode === 401) {
          message("未授权，请登录", { type: "warning" });
          removeToken();
          router.push("/login");
        } else if (httpCode === 500) {
          message("服务器繁忙，请稍后重试", { type: "error" });
        } else if (error.message?.includes("timeout")) {
          message("请求超时，请重试", { type: "error" });
        } else if (!error?.response) {
          message("网络异常，请检查网络连接", { type: "error" });
        }
        return Promise.reject(error);
      }
    );
  }

  public request<T>(
    method: RequestMethods,
    url: string,
    param?: AxiosRequestConfig,
    axiosConfig?: PureHttpRequestConfig
  ): Promise<T> {
    const config = { method, url, ...param, ...axiosConfig } as PureHttpRequestConfig;
    return new Promise((resolve, reject) => {
      PureHttp.axiosInstance.request(config).then(resolve).catch(reject);
    });
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

  public delete<T>(url: string, params?: AxiosRequestConfig, config?: PureHttpRequestConfig): Promise<T> {
    return this.request<T>("delete", url, params, config);
  }
}

export const http = new PureHttp();
