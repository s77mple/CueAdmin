export default {
  path: "/permissions",
  name: "Permissions",
  redirect: "/permissions/index",
  component: () => import("@/layout/index.vue"),
  meta: { icon: "fa-solid:lock", title: "权限管理", rank: 5 },
  children: [
    {
      path: "/permissions/index",
      name: "PermissionList",
      component: () => import("@/views/system/permissions/index.vue"),
      meta: { title: "权限列表", roles: ["admin"] }
    }
  ]
};
