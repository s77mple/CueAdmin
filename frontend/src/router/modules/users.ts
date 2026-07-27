import { $t } from "@/plugins/i18n";

export default {
  path: "/users",
  name: "Users",
  redirect: "/users/index",
  component: () => import("@/layout/index.vue"),
  meta: { icon: "fa-solid:users", title: $t("menus.pureUser"), rank: 2 },
  children: [
    {
      path: "/users/index",
      name: "UserList",
      component: () => import("@/views/system/users/index.vue"),
      meta: { title: $t("menus.pureUser"), roles: ["admin"] }
    }
  ]
};
