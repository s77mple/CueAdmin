export default {
  path: "/permissions",
  redirect: "/permissions/index",
  meta: { icon: "ep/lock", title: "权限管理", rank: 5 },
  children: [
    {
      path: "/permissions/index",
      name: "PermissionList",
      component: () => import("@/views/system/permissions/index.vue"),
      meta: { title: "权限列表", roles: ["admin"] }
    }
  ]
};
