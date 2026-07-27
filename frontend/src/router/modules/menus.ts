export default {
  path: "/menus",
  redirect: "/menus/index",
  meta: { icon: "ep/menu", title: "菜单管理", rank: 4 },
  children: [
    {
      path: "/menus/index",
      name: "MenuList",
      component: () => import("@/views/system/menus/index.vue"),
      meta: { title: "菜单列表", roles: ["admin"] }
    }
  ]
};
