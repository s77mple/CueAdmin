export default {
  path: "/users",
  name: "Users",
  redirect: "/users/index",
  component: () => import("@/layout/index.vue"),
  meta: { icon: "fa-solid:users", title: "用户管理", rank: 2 },
  children: [
    {
      path: "/users/index",
      name: "UserList",
      component: () => import("@/views/system/users/index.vue"),
      meta: { title: "用户列表", roles: ["admin"] }
    }
  ]
};
