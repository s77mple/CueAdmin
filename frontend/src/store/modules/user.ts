import { defineStore } from "pinia";
import { store, router, resetRouter, routerArrays, storageLocal } from "../utils";
import { type LoginResult, getLogin, logout } from "@/api/auth";
import { useMultiTagsStoreHook } from "./multiTags";
import { type DataInfo, setToken, removeToken, userKey } from "@/utils/auth";

export const useUserStore = defineStore("pure-user", {
  state: () => ({
    // 用户名
    username: storageLocal().getItem<DataInfo>(userKey)?.username ?? "",
    // 按钮级别权限
    permissions: storageLocal().getItem<DataInfo>(userKey)?.permissions ?? [],
    // 角色
    roles: storageLocal().getItem<DataInfo>(userKey)?.roles ?? [],
    // 登录页显示哪个组件（0：登录）
    currentPage: 0,
  }),
  actions: {
    /** 存储用户名 */
    SET_USERNAME(username: string) {
      this.username = username;
    },
    /** 存储按钮级别权限 */
    SET_PERMS(permissions: Array<string>) {
      this.permissions = permissions;
    },
    /** 存储角色 */
    SET_ROLES(roles: Array<string>) {
      this.roles = roles;
    },
    /** 存储登录页面显示哪个组件 */
    SET_CURRENTPAGE(value: number) {
      this.currentPage = value;
    },
    /** 登录 */
    async loginByUsername(data) {
      return new Promise<LoginResult>((resolve, reject) => {
        getLogin(data)
          .then(res => {
            if (res.code === 0) {
              setToken({
                accessToken: res.data.access_token,
                username: res.data.user?.display_name ?? res.data.user?.username,
                permissions: res.data.permissions ?? [],
                roles: res.data.roles?.map((r: any) => r.code) ?? [],
              });
              resolve(res);
            } else {
              reject(res.message || `登录失败 (code: ${res.code})`);
            }
          })
          .catch(error => {
            reject(error);
          });
      });
    },
    /** 前端登出（调用接口使 token 失效） */
    logOut() {
      this.username = "";
      this.permissions = [];
      removeToken();
      useMultiTagsStoreHook().handleTags("equal", [...routerArrays]);
      resetRouter();
      logout().catch(() => {});  // fire-and-forget: 即使网络异常也不阻塞跳转
      router.push("/login");
    },
  }
});

export function useUserStoreHook() {
  return useUserStore(store);
}
