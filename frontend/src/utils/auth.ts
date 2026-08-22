import Cookies from "js-cookie";
import { useUserStoreHook } from "@/store/modules/user";
import { storageLocal, isString, isIncludeAllChildren } from "@pureadmin/utils";

export interface DataInfo {
  /** JWT access token */
  accessToken: string;
  /** 刷新令牌 — access 过期后调 /auth/refresh 换新（一次性轮换） */
  refreshToken?: string;
  /** 用户名 */
  username?: string;
  /** 按钮级别权限 */
  permissions?: Array<string>;
  /** 角色 */
  roles?: Array<string>;
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
  refreshToken?: string;
  username?: string;
  permissions?: Array<string>;
  roles?: Array<string>;
}) {
  const { accessToken, refreshToken, username, permissions, roles } = data;

  // token 存 cookie
  Cookies.set(TokenKey, JSON.stringify({ accessToken, refreshToken }));

  // 多标签页登录状态标记
  Cookies.set(multipleTabsKey, "true");

  // 用户信息存 localStorage（roles 给路由侧边栏过滤器用）
  if (username) useUserStoreHook().SET_USERNAME(username);
  if (permissions) useUserStoreHook().SET_PERMS(permissions);
  if (roles) useUserStoreHook().SET_ROLES(roles);
  storageLocal().setItem(userKey, {
    accessToken, refreshToken, username, permissions, roles: roles ?? [],
  });
}

/** 刷新令牌后回写新 token（access + refresh 都换新，用户信息不变） */
export function updateToken(data: { accessToken: string; refreshToken?: string }) {
  const { accessToken, refreshToken } = data;
  Cookies.set(TokenKey, JSON.stringify({ accessToken, refreshToken }));
  const cur = storageLocal().getItem<DataInfo>(userKey);
  if (cur) {
    storageLocal().setItem(userKey, { ...cur, accessToken, refreshToken });
  }
}

/** 登出清理 */
export function removeToken() {
  Cookies.remove(TokenKey);
  Cookies.remove(multipleTabsKey);
  storageLocal().removeItem(userKey);
}

/** 刷新时用 /routes 返回值回写当前用户的权限与角色（保留 accessToken/username） */
export function updateUserAuth(data: {
  permissions?: Array<string>;
  roles?: Array<string>;
}) {
  const cur = storageLocal().getItem<DataInfo>(userKey);
  if (!cur) return;
  const permissions = data.permissions ?? cur.permissions ?? [];
  const roles = data.roles ?? cur.roles ?? [];
  useUserStoreHook().SET_PERMS(permissions);
  useUserStoreHook().SET_ROLES(roles);
  storageLocal().setItem(userKey, { ...cur, permissions, roles });
}

/** 格式化 token（JWT 格式） */
export const formatToken = (token: string): string => {
  return "Bearer " + token;
};

/** 是否有按钮级别的权限 */
export const hasPerms = (value: string | Array<string>): boolean => {
  if (!value) return false;
  const store = useUserStoreHook();
  /* admin 角色拥有所有权限 */
  if (store.roles?.includes("admin")) return true;
  if (!store.permissions) return false;
  const isAuths = isString(value)
    ? store.permissions.includes(value)
    : isIncludeAllChildren(value, store.permissions);
  return isAuths ? true : false;
};
