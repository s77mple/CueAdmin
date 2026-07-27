export default {
  path: "/menus",
  name: "Menus",
  redirect: "/menus/index",
  component: () => import("@/layout/index.vue"),
  meta: { icon: "fa-solid:bars", title: "菜单管理", rank: 4 },
  children: [
    {
      path: "/menus/index",
      name: "MenuList",
      component: () => import("@/views/system/menus/index.vue"),
      meta: { title: "菜单列表", roles: ["admin"] }
    }
  ]
};
