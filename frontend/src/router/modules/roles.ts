export default {
  path: "/roles",
  redirect: "/roles/index",
  meta: { icon: "ep/avatar", title: "角色管理", rank: 3 },
  children: [
    {
      path: "/roles/index",
      name: "RoleList",
      component: () => import("@/views/system/roles/index.vue"),
      meta: { title: "角色列表", roles: ["admin"] }
    }
  ]
};
