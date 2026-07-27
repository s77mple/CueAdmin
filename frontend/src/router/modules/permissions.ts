import { $t } from "@/plugins/i18n";

export default {
  path: "/permissions",
  name: "Permissions",
  redirect: "/permissions/index",
  component: () => import("@/layout/index.vue"),
  meta: { icon: "fa-solid:lock", title: $t("menus.purePermission"), rank: 5 },
  children: [
    {
      path: "/permissions/index",
      name: "PermissionList",
      component: () => import("@/views/system/permissions/index.vue"),
      meta: { title: $t("menus.purePermission"), roles: ["admin"] }
    }
  ]
};
