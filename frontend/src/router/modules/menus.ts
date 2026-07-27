import { $t } from "@/plugins/i18n";

export default {
  path: "/menus",
  name: "Menus",
  redirect: "/menus/index",
  component: () => import("@/layout/index.vue"),
  meta: { icon: "fa-solid:bars", title: $t("menus.pureSystemMenu"), rank: 4 },
  children: [
    {
      path: "/menus/index",
      name: "MenuList",
      component: () => import("@/views/system/menus/index.vue"),
      meta: { title: $t("menus.pureSystemMenu"), roles: ["admin"] }
    }
  ]
};
