export default {
  path: "/roles",
  name: "Roles",
  redirect: "/roles/index",
  component: () => import("@/layout/index.vue"),
  meta: { icon: "fa-solid:user-tag", title: "角色管理", rank: 3 },
  children: [
    {
      path: "/roles/index",
      name: "RoleList",
      component: () => import("@/views/system/roles/index.vue"),
      meta: { title: "角色列表", roles: ["admin"] }
    }
  ]
};
