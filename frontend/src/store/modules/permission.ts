import { defineStore } from "pinia";
import {
  type cacheType,
  store,
  ascending,
  getKeyList,
  filterTree,
  constantMenus,
  filterNoPermissionTree,
  formatFlatteningRoutes
} from "../utils";
import { useMultiTagsStoreHook } from "./multiTags";
import { handleTree } from "@/utils/tree";

export const usePermissionStore = defineStore("pure-permission", {
  state: () => ({
    // 静态路由生成的菜单
    constantMenus,
    // 整体路由生成的菜单（静态、动态）
    wholeMenus: [],
    // 整体路由（一维数组格式）
    flatteningRoutes: [],
    // 缓存页面keepAlive
    cachePageList: []
  }),
  actions: {
    /** 组装整体路由生成的菜单 */
    handleWholeMenus(routes: any[]) {
      this.wholeMenus = filterNoPermissionTree(
        filterTree(ascending(this.constantMenus.concat(routes)))
      );
      this.flatteningRoutes = formatFlatteningRoutes(
        this.constantMenus.concat(routes) as any
      );
    },
    /** 从后端 menus 数据构建动态侧边栏 */
    handleMenus(menus: any[]) {
      if (!menus || !menus.length) {
        this.handleWholeMenus([]);
        return;
      }
      try {
        const menuTree = handleTree(menus, "id", "parent_id", "children");
        const toRoute = (node: any): any => ({
          path: node.path,
          name: node.code,
          redirect: node.children?.length ? node.children[0].path : undefined,
          meta: {
            icon: node.icon,
            title: node.name,
            rank: node.sort_order,
            roles: []
          },
          children: node.children?.map(toRoute)
        });
        const routes = menuTree.map(toRoute);
        this.wholeMenus = filterTree(ascending(routes));
        this.flatteningRoutes = formatFlatteningRoutes(routes);
      } catch (e) {
        console.warn("动态菜单构建失败，回退到静态菜单", e);
        this.handleWholeMenus([]);
      }
    },
    /** 监听缓存页面是否存在于标签页，不存在则删除 */
    clearCache() {
      let cacheLength = this.cachePageList.length;
      const nameList = getKeyList(useMultiTagsStoreHook().multiTags, "name");
      while (cacheLength > 0) {
        nameList.findIndex(v => v === this.cachePageList[cacheLength - 1]) ===
          -1 &&
          this.cachePageList.splice(
            this.cachePageList.indexOf(this.cachePageList[cacheLength - 1]),
            1
          );
        cacheLength--;
      }
    },
    cacheOperate({ mode, name }: cacheType) {
      const delIndex = this.cachePageList.findIndex(v => v === name);
      switch (mode) {
        case "refresh":
          this.cachePageList = this.cachePageList.filter(v => v !== name);
          this.clearCache();
          break;
        case "add":
          this.cachePageList.push(name);
          break;
        case "delete":
          delIndex !== -1 && this.cachePageList.splice(delIndex, 1);
          this.clearCache();
          break;
      }
    },
    /** 清空缓存页面 */
    clearAllCachePage() {
      this.wholeMenus = [];
      this.cachePageList = [];
    }
  }
});

export function usePermissionStoreHook() {
  return usePermissionStore(store);
}
