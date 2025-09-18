const Layout = () => import("@/layout/index.vue");

export default {
  path: "/mine-team",
  name: "Team",
  component: Layout,
  redirect: "/mine-team",
  meta: {
    icon: "ant-design:smile-twotone",
    title: "我的团队",
    rank: 0
  },
  children: [
    {
      path: "/mine-team/manage",
      name: "MineTeamManagement",
      component: () => import("@/views/team/mine/index.vue"),
      meta: {
        title: "我的团队",
        showLink: true
      }
    }
  ]
} as RouteConfigsTable;
