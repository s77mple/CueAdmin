import { defineStore } from "pinia";
import { store, router, resetRouter, routerArrays, storageLocal } from "../utils";
import { type UserResult, getLogin } from "@/api/user";
import { useMultiTagsStoreHook } from "./multiTags";
import { type DataInfo, setToken, removeToken, userKey } from "@/utils/auth";

export const useUserStore = defineStore("pure-user", {
  state: () => ({
    // 用户名
    username: storageLocal().getItem<DataInfo>(userKey)?.username ?? "",
    // 按钮级别权限
    permissions: storageLocal().getItem<DataInfo>(userKey)?.permissions ?? [],
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
    /** 存储登录页面显示哪个组件 */
    SET_CURRENTPAGE(value: number) {
      this.currentPage = value;
    },
    /** 登录 */
    async loginByUsername(data) {
      return new Promise<UserResult>((resolve, reject) => {
        getLogin(data)
          .then(res => {
            if (res.code === 0) {
              setToken({
                accessToken: res.data.access_token,
                username: res.data.user?.display_name ?? res.data.user?.username,
                permissions: res.data.permissions ?? [],
              });
              resolve(res);
            } else {
              reject(res.message);
            }
          })
          .catch(error => {
            reject(error);
          });
      });
    },
    /** 前端登出（不调用接口） */
    logOut() {
      this.username = "";
      this.permissions = [];
      removeToken();
      useMultiTagsStoreHook().handleTags("equal", [...routerArrays]);
      resetRouter();
      router.push("/login");
    },
  }
});

export function useUserStoreHook() {
  return useUserStore(store);
}
