/**
 * 全局字典 Store — 角色/部门列表跨页面共享。
 *
 * 为什么抽成全局：
 *   - 用户页（表格部门列、角色/部门下拉）、部门页、角色页都用到角色/部门列表，
 *     之前每个页面各自 onMounted 拉一份，彼此不共享 → 别处改了本页看不到
 *   - 这里只拉一次，所有页面复用；任何页面变更字典后调 loadAll(true) 强制重拉，全员生效
 *
 * 用法：
 *   import { useDictStoreHook } from "@/store/modules/dictionary";
 *   const dictStore = useDictStoreHook();
 *   onMounted(() => dictStore.loadAll());        // 懒加载，拉一次
 *   dictStore.loadAll(true);                     // 字典变更后强制重拉
 */
import { defineStore } from "pinia";
import { store } from "../utils";
import { getRoleList } from "@/api/system/roles";
import { getDepartmentList } from "@/api/system/departments";

export const useDictStore = defineStore("dict", {
  state: () => ({
    roles: [] as any[],
    departments: [] as any[],
    loaded: false
  }),
  actions: {
    /** 懒加载：只拉一次；force=true 强制重拉（字典变更后调用） */
    async loadAll(force = false) {
      if (this.loaded && !force) return;
      const [rRes, dRes] = await Promise.all([
        getRoleList(),
        getDepartmentList()
      ]);
      if (rRes.code === 0) this.roles = rRes.data?.items ?? [];
      if (dRes.code === 0) this.departments = dRes.data?.items ?? [];
      this.loaded = true;
    }
  }
});

export function useDictStoreHook() {
  return useDictStore(store);
}
