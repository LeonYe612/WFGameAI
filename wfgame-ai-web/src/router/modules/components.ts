export default {
  path: "/components",
  meta: {
    icon: "carbon:ibm-watson-studio",
    title: "组件演示",
    rank: 5,
    showLink: false
  },
  children: [
    {
      path: "/components/log-viewer",
      name: "LogViewerDemo",
      component: () => import("@/components/LogViewer/demo.vue"),
      meta: {
        icon: "carbon:document-view",
        title: "日志查看器",
        showParent: true
      }
    }
  ]
} as RouteConfigsTable;
