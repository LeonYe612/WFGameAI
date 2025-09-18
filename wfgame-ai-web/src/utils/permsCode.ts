/** 各个页面对应的按钮权限CODE */
// 按钮权限CODE命名规则：页面名+权限类型
export const perms = {
  /** 仪表盘页面 */
  dashboard: {
    // 概览
    overview: {
      readable: "DashboardOverviewReadable",
      writable: "DashboardOverviewWritable"
    }
  },
  /** 测试用例相关页面 */
  testcase: {
    // 测试用例列表
    list: {
      readable: "TestCaseListReadable",
      writable: "TestCaseListWritable"
    },
    // 测试用例详情
    detail: {
      readable: "TestCaseDetailReadable",
      writable: "TestCaseDetailWritable"
    },
    // 测试用例目录管理
    catalog: {
      readable: "TestCaseCatalogReadable",
      writable: "TestCaseCatalogWritable"
    }
  },
  /** 测试计划相关页面 */
  plan: {
    // 计划列表
    list: {
      readable: "PlanManagementReadable",
      writable: "PlanManagementWritable"
    },
    // 计划详情
    detail: {
      readable: "PlanDetailReadable",
      writable: "PlanDetailWritable"
    }
  },
  /** 测试报告相关页面 */
  report: {
    // 报告列表
    list: {
      readable: "ReportManagementReadable"
    },
    // 报告详情
    detail: {
      readable: "ReportDetailReadable"
    }
  },
  /** JMX 相关页面 */
  jmx: {
    // JMX 列表
    list: {
      readable: "JmxManagementReadable",
      writable: "JmxManagementWritable"
    },
    // JMX 详情
    detail: {
      readable: "JmxDetailReadable",
      writable: "JmxDetailWritable"
    }
  },
  /** 我的团队相关页面 */
  myteam: {
    // 团队列表
    manage: {
      writable: "TeamManagementWritable"
    }
  },
  /** 系统管理页面 */
  // 系统页面下述code暂做保留，实际分配给用户系统管理菜单时候
  // 默认拥有菜单页面内的按钮权限
  system: {
    // 权限管理
    permission: {
      writable: "PermissionManagementWritable"
    },
    // 角色管理
    role: {
      writable: "RoleManagementWritable"
    },
    // 用户管理
    user: {
      writable: "UserManagementWritable"
    },
    // 团队管理
    team: {
      writable: "TeamManagementWritable"
    }
  }
};
