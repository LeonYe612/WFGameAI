const Layout = () => import("@/layout/index.vue");

export default {
    path: "/reports",
    meta: {
        icon: "icon-park-outline:analysis",
        title: "报告管理",
        rank: 3
    },
    children: [
        {
            path: "/reports/list",
            name: "ReportManagement",
            component: () => import("@/views/reports/list/index.vue"),
            meta: {
                title: "报告列表"
            }
        },
        {
            path: "/reports/detail",
            name: "ReportDetail",
            component: () => import("@/views/reports/detail/index.vue"),
            meta: {
                title: "报告详情",
                showLink: false,
                activePath: "/reports/list"
            }
        }
    ]
} as RouteConfigsTable;
