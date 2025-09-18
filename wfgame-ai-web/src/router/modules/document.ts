const Layout = () => import("@/layout/index.vue");
const IFrame = () => import("@/layout/frameView.vue");

// 最简代码，也就是这些字段必须有
export default {
  path: "/document",
  meta: {
    icon: "gg:readme",
    title: "使用说明",
    component: Layout,
    rank: 9999, // 放在最后一个
    showLink: false
  },
  children: [
    // 内嵌 iframe
    {
      path: "/document/readme",
      // name必须写，写法随意
      name: "DocumentReadme",
      component: IFrame,
      meta: {
        icon: "gg:readme",
        title: "使用说明",
        showParent: false,
        // 需要内嵌页面的地址
        frameSrc:
          "https://pek02ezp15.feishu.cn/wiki/B00Ww7nC0if3yUkch8Ccnrs5nV5?from=from_copylink",
        // 内嵌的iframe页面是否开启首次加载动画，默认true，下面可以不写，如果内嵌的iframe页面已经存在首加载动画，可以将frameLoading设为false
        frameLoading: false
      }
    }
    // 外链
    // {
    //   // path必须写，必须以 / 开头，推荐格式 / 后跟随意单词，不同的外链path不要重复哦
    //   path: "/anything",
    //   // 外链地址写在name属性里
    //   name: "https://yiming_chang.gitee.io/pure-admin-doc",
    //   meta: {
    //     title: " 外链"
    //   }
    // }
  ]
} as RouteConfigsTable;
