import Cookies from "js-cookie";
import { useUserStoreHook } from "@/store/modules/user";
import { storageLocal, isString, isIncludeAllChildren } from "@pureadmin/utils";

export interface DataInfo {
  /** JWT token */
  accessToken: string;
  /** 用户名 */
  username?: string;
  /** 按钮级别权限 */
  permissions?: Array<string>;
  /** 角色 */
  roles?: Array<string>;
  /** 动态菜单 */
  menus?: Array<{
    code: string; name: string; icon: string; path: string;
    parent_id: number | null; sort_order: number;
  }>;
}

export const userKey = "user-info";
export const TokenKey = "authorized-token";
export const multipleTabsKey = "multiple-tabs";

/** 获取`token` */
export function getToken(): DataInfo | null {
  try {
    const cookie = Cookies.get(TokenKey);
    if (cookie) return JSON.parse(cookie);
  } catch {
    Cookies.remove(TokenKey);
  }
  return storageLocal().getItem(userKey);
}

/** 保存 token 和用户信息（登录成功后调用） */
export function setToken(data: {
  accessToken: string;
  username?: string;
  permissions?: Array<string>;
  roles?: Array<string>;
  menus?: Array<any>;
}) {
  const { accessToken, username, permissions, roles, menus } = data;

  // token 存 cookie
  Cookies.set(TokenKey, JSON.stringify({ accessToken }));

  // 多标签页登录状态标记
  Cookies.set(multipleTabsKey, "true");

  // 用户信息存 localStorage（roles 给路由侧边栏过滤器用）
  if (username) useUserStoreHook().SET_USERNAME(username);
  if (permissions) useUserStoreHook().SET_PERMS(permissions);
  if (menus) useUserStoreHook().SET_MENUS(menus);
  storageLocal().setItem(userKey, {
    accessToken, username, permissions, roles: roles ?? [], menus: menus ?? [],
  });
}

/** 登出清理 */
export function removeToken() {
  Cookies.remove(TokenKey);
  Cookies.remove(multipleTabsKey);
  storageLocal().removeItem(userKey);
}

/** 格式化 token（JWT 格式） */
export const formatToken = (token: string): string => {
  return "Bearer " + token;
};

/** 是否有按钮级别的权限 */
export const hasPerms = (value: string | Array<string>): boolean => {
  if (!value) return false;
  const { permissions } = useUserStoreHook();
  if (!permissions) return false;
  const isAuths = isString(value)
    ? permissions.includes(value)
    : isIncludeAllChildren(value, permissions);
  return isAuths ? true : false;
};
