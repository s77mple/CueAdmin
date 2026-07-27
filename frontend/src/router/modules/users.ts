export default {
  path: "/users",
  redirect: "/users/index",
  meta: { icon: "ep/user-filled", title: "用户管理", rank: 2 },
  children: [
    {
      path: "/users/index",
      name: "UserList",
      component: () => import("@/views/system/users/index.vue"),
      meta: { title: "用户列表", roles: ["admin"] }
    }
  ]
};
