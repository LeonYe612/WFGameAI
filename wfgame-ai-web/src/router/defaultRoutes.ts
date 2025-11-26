export default [
  {
    id: 75,
    parent_id: 74,
    genre: 1,
    path: "/dashboard",
    name: "AI-DASHBOARD",
    queue: 0,
    meta: {
      title: "控制台",
      icon: "ant-design:dashboard-twotone",
      showLink: true,
      showParent: true,
      keepAlive: true,
      frameLoading: false,
      hiddenTag: false,
      transition: {
        enterTransition: "animate__fadeIn animate__faster",
        leaveTransition: "animate__fadeOut animate__faster"
      }
    },
    children: [
      {
        id: 76,
        parent_id: 75,
        genre: 1,
        path: "/dashboard/index",
        component: "/dashboard/index",
        name: "AI-DASHBOARD-INDEX",
        queue: 0,
        meta: {
          title: "控制台",
          showLink: true,
          showParent: false,
          keepAlive: true,
          frameLoading: false,
          hiddenTag: false,
          transition: {
            enterTransition: "animate__fadeIn animate__faster",
            leaveTransition: "animate__fadeOut animate__faster"
          }
        }
      }
    ]
  },
  {
    id: 77,
    parent_id: 74,
    genre: 1,
    path: "/devices",
    name: "AI-DEVICES",
    queue: 5,
    meta: {
      title: "设备管理",
      icon: "ant-design:mobile-twotone",
      showLink: true,
      showParent: true,
      keepAlive: true,
      frameLoading: false,
      hiddenTag: false,
      transition: {
        enterTransition: "animate__fadeIn animate__faster",
        leaveTransition: "animate__fadeOut animate__faster"
      }
    },
    children: [
      {
        id: 78,
        parent_id: 77,
        genre: 1,
        path: "/devices/list/index",
        component: "/devices/list/index",
        name: "AI-DEVICES-LIST",
        queue: 0,
        meta: {
          title: "设备管理",
          showLink: true,
          showParent: false,
          keepAlive: true,
          frameLoading: false,
          hiddenTag: false,
          transition: {
            enterTransition: "animate__fadeIn animate__faster",
            leaveTransition: "animate__fadeOut animate__faster"
          }
        }
      }
    ]
  },
  {
    id: 79,
    parent_id: 74,
    genre: 1,
    path: "/scripts",
    name: "AI-SCRIPTS",
    queue: 10,
    meta: {
      title: "脚本管理",
      icon: "ant-design:code-twotone",
      showLink: true,
      showParent: true,
      keepAlive: true,
      frameLoading: false,
      hiddenTag: false,
      transition: {
        enterTransition: "animate__fadeIn animate__faster",
        leaveTransition: "animate__fadeOut animate__faster"
      }
    },
    children: [
      {
        id: 80,
        parent_id: 79,
        genre: 1,
        path: "/scripts/list",
        component: "/scripts/list/index",
        name: "AI-SCRIPTS-LIST",
        queue: 0,
        meta: {
          title: "脚本管理",
          showLink: true,
          showParent: false,
          keepAlive: true,
          frameLoading: false,
          hiddenTag: false,
          transition: {
            enterTransition: "animate__fadeIn animate__faster",
            leaveTransition: "animate__fadeOut animate__faster"
          }
        }
      },
      {
        id: 81,
        parent_id: 79,
        genre: 1,
        path: "/scripts/detail",
        component: "/scripts/detail/index",
        name: "AI-SCRIPTS-DETAIL",
        queue: 0,
        meta: {
          title: "脚本详情",
          showLink: false,
          showParent: false,
          keepAlive: true,
          frameLoading: false,
          hiddenTag: false,
          transition: {
            enterTransition: "animate__fadeIn animate__faster",
            leaveTransition: "animate__fadeOut animate__faster"
          }
        }
      }
    ]
  },
  {
    id: 82,
    parent_id: 74,
    genre: 1,
    path: "/tasks",
    name: "AI-TASKS",
    queue: 15,
    meta: {
      title: "任务管理",
      icon: "ant-design:rocket-twotone",
      showLink: true,
      showParent: true,
      keepAlive: true,
      frameLoading: false,
      hiddenTag: false,
      transition: {
        enterTransition: "animate__fadeIn animate__faster",
        leaveTransition: "animate__fadeOut animate__faster"
      }
    },
    children: [
      {
        id: 83,
        parent_id: 82,
        genre: 1,
        path: "/tasks/index",
        component: "/tasks/index",
        name: "AI-TASKS-INDEX",
        queue: 0,
        meta: {
          title: "任务管理",
          showLink: true,
          showParent: false,
          keepAlive: true,
          frameLoading: false,
          hiddenTag: false,
          transition: {
            enterTransition: "animate__fadeIn animate__faster",
            leaveTransition: "animate__fadeOut animate__faster"
          }
        }
      }
    ]
  },
  {
    id: 84,
    parent_id: 74,
    genre: 1,
    path: "/reports",
    name: "AI-REPORTS",
    queue: 20,
    meta: {
      title: "测试报告",
      icon: "ant-design:pie-chart-twotone",
      showLink: true,
      showParent: true,
      keepAlive: true,
      frameLoading: false,
      hiddenTag: false,
      transition: {
        enterTransition: "animate__fadeIn animate__faster",
        leaveTransition: "animate__fadeOut animate__faster"
      }
    },
    children: [
      {
        id: 85,
        parent_id: 84,
        genre: 1,
        path: "/reports/list/index",
        component: "/reports/list/index",
        name: "AI-REPORTS-INDEX",
        queue: 0,
        meta: {
          title: "测试报告",
          showLink: true,
          showParent: false,
          keepAlive: true,
          frameLoading: false,
          hiddenTag: false,
          transition: {
            enterTransition: "animate__fadeIn animate__faster",
            leaveTransition: "animate__fadeOut animate__faster"
          }
        }
      },
      {
        id: 85,
        parent_id: 84,
        genre: 1,
        path: "/reports/detail/index",
        component: "/reports/detail/index",
        name: "AI-REPORTS-DETAIL",
        queue: 5,
        meta: {
          title: "测试报告",
          showLink: false,
          showParent: false,
          keepAlive: true,
          frameLoading: false,
          hiddenTag: false,
          transition: {
            enterTransition: "animate__fadeIn animate__faster",
            leaveTransition: "animate__fadeOut animate__faster"
          }
        }
      }
    ]
  },
  {
    id: 86,
    parent_id: 74,
    genre: 1,
    path: "/data",
    name: "AI-DATA",
    queue: 25,
    meta: {
      title: "数据管理",
      icon: "ant-design:database-twotone",
      showLink: true,
      showParent: true,
      keepAlive: true,
      frameLoading: false,
      hiddenTag: false,
      transition: {
        enterTransition: "animate__fadeIn animate__faster",
        leaveTransition: "animate__fadeOut animate__faster"
      }
    },
    children: [
      {
        id: 87,
        parent_id: 86,
        genre: 1,
        path: "/data/index",
        component: "/data/index",
        name: "AI-DATA-INDEX",
        queue: 0,
        meta: {
          title: "数据管理",
          showLink: true,
          showParent: false,
          keepAlive: true,
          frameLoading: false,
          hiddenTag: false,
          transition: {
            enterTransition: "animate__fadeIn animate__faster",
            leaveTransition: "animate__fadeOut animate__faster"
          }
        }
      }
    ]
  },
  {
    id: 88,
    parent_id: 74,
    genre: 1,
    path: "/ocr",
    name: "AI-OCR",
    queue: 30,
    meta: {
      title: "OCR识别",
      icon: "ant-design:camera-twotone",
      showLink: true,
      showParent: true,
      keepAlive: true,
      frameLoading: false,
      hiddenTag: false,
      transition: {
        enterTransition: "animate__fadeIn animate__faster",
        leaveTransition: "animate__fadeOut animate__faster"
      }
    },
    children: [
      {
        id: 89,
        parent_id: 88,
        genre: 1,
        path: "/ocr/list",
        component: "/ocr/list/index",
        name: "AI-OCR-LIST",
        queue: 0,
        meta: {
          title: "OCR识别",
          showLink: true,
          showParent: false,
          keepAlive: true,
          frameLoading: false,
          hiddenTag: false,
          transition: {
            enterTransition: "animate__fadeIn animate__faster",
            leaveTransition: "animate__fadeOut animate__faster"
          }
        }
      },
      {
        id: 899,
        parent_id: 88,
        genre: 1,
        path: "/ocr/result",
        component: "/ocr/result/index",
        name: "AI-OCR-RESULT",
        queue: 0,
        meta: {
          title: "OCR结果",
          showLink: false,
          showParent: false,
          keepAlive: true,
          frameLoading: false,
          hiddenTag: false,
          transition: {
            enterTransition: "animate__fadeIn animate__faster",
            leaveTransition: "animate__fadeOut animate__faster"
          }
        }
      }
    ]
  },
  {
    id: 90,
    parent_id: 74,
    genre: 1,
    path: "/settings",
    name: "AI-SETTINGS",
    queue: 35,
    meta: {
      title: "系统设置",
      icon: "ant-design:setting-twotone",
      showLink: true,
      showParent: true,
      keepAlive: true,
      frameLoading: false,
      hiddenTag: false,
      transition: {
        enterTransition: "animate__fadeIn animate__faster",
        leaveTransition: "animate__fadeOut animate__faster"
      }
    },
    children: [
      {
        id: 91,
        parent_id: 90,
        genre: 1,
        path: "/settings/index",
        component: "/settings/index",
        name: "AI-SETTINGS-INDEX",
        queue: 0,
        meta: {
          title: "系统设置",
          showLink: true,
          showParent: false,
          keepAlive: true,
          frameLoading: false,
          hiddenTag: false,
          transition: {
            enterTransition: "animate__fadeIn animate__faster",
            leaveTransition: "animate__fadeOut animate__faster"
          }
        }
      }
    ]
  },
  {
    id: 92,
    parent_id: 74,
    genre: 1,
    path: "/replay",
    name: "AI-REPLAY",
    queue: 9998,
    meta: {
      title: "回放",
      icon: "videoPlay",
      showLink: false,
      showParent: false,
      keepAlive: false,
      frameLoading: false,
      hiddenTag: false,
      transition: {
        enterTransition: "animate__fadeIn animate__faster",
        leaveTransition: "animate__fadeOut animate__faster"
      }
    },
    children: [
      {
        id: 93,
        parent_id: 92,
        genre: 1,
        path: "/replay/index",
        component: "/replay/index.vue",
        name: "AI-REPLAY-ROOM",
        queue: 0,
        meta: {
          title: "回放房间",
          showLink: false,
          showParent: false,
          keepAlive: false,
          frameLoading: false,
          hiddenTag: false,
          transition: {
            enterTransition: "animate__fadeIn animate__faster",
            leaveTransition: "animate__fadeOut animate__faster"
          }
        }
      }
    ]
  }
];
