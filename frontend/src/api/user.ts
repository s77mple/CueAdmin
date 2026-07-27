import { http } from "@/utils/http";

// —————— 后端 login 返回的 data 结构 ——————
export type UserResult = {
  code: number;
  message: string;
  data: {
    access_token: string;
    user: {
      id: number;
      username: string;
      display_name: string;
      phone: string | null;
      is_active: boolean;
    };
    permissions: Array<string>;
    /** 侧边栏菜单 */
    menus: Array<{
      code: string;
      name: string;
      icon: string;
      path: string;
      parent_id: number | null;
      sort_order: number;
    }>;
  };
};

// —————— 公共分页结构（后端返回） ——————
export type PageData<T> = {
  items: Array<T>;
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
};

// —————— 通用响应结构 ——————
export type ApiResult<T = null> = {
  code: number;
  message: string;
  data: T;
};

/** 登录 */
export const getLogin = (data?: object) => {
  return http.request<UserResult>("post", "/api/v1/auth/login", { data });
};

/** 获取当前用户信息 */
export const getMe = () => {
  return http.request<UserResult>("get", "/api/v1/auth/me");
};

/** 登出 */
export const logout = () => {
  return http.request("post", "/api/v1/auth/logout");
};

/** 更新个人资料 */
export const updateProfile = (data?: object) => {
  return http.request("put", "/api/v1/auth/profile", { data });
};
