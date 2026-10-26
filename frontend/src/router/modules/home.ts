import { $t } from "@/plugins/i18n";
import { home } from "@/router/enums";
const Layout = () => import("@/layout/index.vue");

/**
 * 根路由只当 Layout 容器用，不自带页面。
 *
 * 后端下发的动态路由运行时会被 push 进 `router.options.routes[0].children`
 * （见 router/utils.ts 的 handleAsyncRoutes），所以这条路由**不能删**；
 * `name: "Home"` 和 `path: "/"` 也**不能改** —— ascending 里的 handRank 靠这两个值
 * 把它锁在 rank 0，改了动态路由的挂载点就漂了。
 *
 * 原先这里挂着一个 /welcome 示例首页，已删除。侧边栏和登录后的落地页统一看
 * getTopMenu()（= 后端返回的第一个菜单）。`children` 留空数组而不是删掉这个 key，
 * 是为了让 handleAsyncRoutes 里的 `routes[0].children.findIndex(...)` 有东西可点。
 */
export default {
  path: "/",
  name: "Home",
  component: Layout,
  meta: {
    icon: "ep/home-filled",
    title: $t("menus.pureHome"),
    rank: home
  },
  children: []
} satisfies RouteConfigsTable;
