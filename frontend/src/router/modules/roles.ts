import { $t } from "@/plugins/i18n";

export default {
  path: "/roles",
  name: "Roles",
  redirect: "/roles/index",
  component: () => import("@/layout/index.vue"),
  meta: { icon: "fa-solid:user-tag", title: $t("menus.pureRole"), rank: 3 },
  children: [
    {
      path: "/roles/index",
      name: "RoleList",
      component: () => import("@/views/system/roles/index.vue"),
      meta: { title: $t("menus.pureRole"), roles: ["admin"] }
    }
  ]
};
