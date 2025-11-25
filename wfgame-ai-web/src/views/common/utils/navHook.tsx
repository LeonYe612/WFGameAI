import { isString, isEmpty } from "@pureadmin/utils";
import { useMultiTagsStoreHook } from "@/store/modules/multiTags";
import { useSettingStoreHook } from "@/store/modules/settings";
import { emitter } from "@/utils/mitt";
import {
  useRouter,
  useRoute,
  type LocationQueryRaw,
  type RouteParamsRaw
} from "vue-router";
import { nextTick, ref } from "vue";

export interface NavigateProps {
  parameter?: LocationQueryRaw | RouteParamsRaw;
  model?: "query" | "params";
  path?: string;
  componentName?: string;
  tagTitle?: string;
  dynamicLevel?: number; // 最大打开标签数
  blank?: boolean; // 是否在新的标签页中打开
  addTag?: boolean; // 是否添加标签页
}

export function useNavigate() {
  const route = useRoute();
  const router = useRouter();
  const getParameter = isEmpty(route?.params) ? route?.query : route?.params;
  const pureSetting = useSettingStoreHook();

  // 用于跟踪是否已添加样式表，避免重复添加
  const fullscreenStyleSheet = ref<CSSStyleSheet | null>(null);

  const findPathByName = (routeName: string) => {
    const resolvedRoute = router.resolve({
      name: routeName
    });

    if (resolvedRoute) {
      return resolvedRoute.href;
    }
    return "";
  };

  function navigateTo(props: NavigateProps) {
    const {
      parameter = {},
      model = "query",
      componentName,
      tagTitle = "未命名页面",
      dynamicLevel = 1,
      addTag = true
    } = props;
    let path = props.path;
    // 如果path未传递，使用 componentName 去路由信息中查找对应path
    if (!path) {
      path = findPathByName(componentName);
    }
    // ⚠️ 这里要特别注意下
    // vue - router在解析路由参数的时候会自动转化成字符串类型
    // 比如在使用useRoute().route.query或useRoute().route.params时，得到的参数都是字符串类型
    // 所以在传参的时候，如果参数是数字类型，就需要在此处 toString() 一下
    // 保证传参跟路由参数类型一致都是字符串，这是必不可少的环节！！！
    Object.keys(parameter).forEach(param => {
      if (!isString(parameter[param])) {
        parameter[param] = parameter[param]?.toString() || "";
      }
    });

    // 添加标签页
    if (addTag) {
      useMultiTagsStoreHook().handleTags("push", {
        // path: `/tabs/query-detail`,
        path: path,
        name: componentName,
        query: parameter,
        meta: {
          // title: {
          //   zh: `No.${parameter.id} - 详情信息`,
          //   en: `No.${parameter.id} - DetailInfo`
          // },
          // 如果使用的是非国际化精简版title可以像下面这么写
          title: tagTitle,
          // 最大打开标签数
          dynamicLevel: dynamicLevel || 1
        }
      });
    }

    // 根据 model("params" | "query") 类型组织参数
    const routeInfo = { name: componentName, [model]: parameter };
    const href = router.resolve(routeInfo).href;

    // 路由跳转
    if (props.blank) {
      window.open(href, "_blank");
    } else {
      router.push(routeInfo);
    }
  }

  function navigateToScriptDetail(id?: number, blank = false) {
    let title = "";
    if (!id) {
      // 新增
      id = 0;
      title = "新增脚本";
    } else {
      // 编辑用例
      title = `ID.${id} - 编辑脚本`;
    }
    navigateTo({
      parameter: {
        id: id
      },
      componentName: "AI-SCRIPTS-DETAIL",
      tagTitle: title,
      blank
    });
  }

  function navigateToTestcaseList() {
    router.push({ name: "TestCaseList" });
  }

  function navigateToPlanList() {
    router.push({ name: "PlanManagement" });
  }

  function navigateToTasksPage(params = {}, blank = false) {
    if (blank) {
      const href = router.resolve({
        name: "AI-TASKS",
        query: { ...params }
      }).href;
      window.open(href, "_blank");
      return;
    }
    router.push({ name: "AI-TASKS", query: { ...params } });
  }

  function navigateToExecutorDownload() {
    navigateTo({
      parameter: { showTag: "true" },
      componentName: "NeeBeeReadme",
      tagTitle: "NeeBee Cli"
    });
  }

  function navigateToPlanDetail(id?: number) {
    let title = "";
    if (!id) {
      // 新增用例
      id = 0;
      title = "新增计划";
    } else {
      // 编辑用例
      title = `ID.${id} - 编辑计划`;
    }
    navigateTo({
      parameter: {
        id: id
      },
      componentName: "PlanDetail",
      tagTitle: title
    });
  }

  function navigateToCatalog() {
    navigateTo({
      parameter: { showTag: "true" },
      componentName: "TestcaseCatalog",
      tagTitle: "目录管理"
    });
  }

  function navigateToReportDetail(
    id: number,
    blank = false,
    params = {},
    addTag = false
  ) {
    const title = `ID.${id} - 测试报告`;
    navigateTo({
      parameter: {
        id: id,
        ...params
      },
      componentName: "AI-REPORTS-DETAIL",
      tagTitle: title,
      blank,
      addTag
    });
  }

  // 跳转到报告列表（带 id 参数），后续列表根据 id 自动选中行
  function navigateToReportList(reportId?: number, blank = false) {
    let title = "测试报告";
    const rid = reportId && !isNaN(reportId) && reportId > 0 ? reportId : undefined;
    if (rid) {
      title = `报告ID.${rid}`;
    }
    navigateTo({
      parameter: rid ? { id: rid } : {},
      componentName: "AI-REPORTS-INDEX",
      tagTitle: title,
      blank
    });
  }


  function navigateToOcrResult(
    taskId: string,
    blank = false,
    params = {},
    addTag = true
  ) {
    const title = `任务ID.${taskId} - 识别结果`;
    navigateTo({
      parameter: {
        id: taskId,
        ...params
      },
      componentName: "AI-OCR-RESULT",
      tagTitle: title,
      blank,
      addTag
    });
  }

  function navigateToDebugReportList(keywords: string) {
    router.push({
      name: "ReportManagement",
      query: { plan_type: 1, keywords: keywords }
    });
    // router.push({ name: "ReportManagement", params: { type: "debug" } });
  }

  function navigateToPlanReportList(planType: number, keywords: string) {
    router.push({
      name: "ReportManagement",
      query: { plan_type: planType, keywords: keywords }
    });
  }

  /**
   * ----- Replay room navigation helpers -----
   * Centralizes building and opening the replay room URL with resilience to route-name differences.
   */
  const normalizeList = (val?: Array<string | number>) => {
    if (!Array.isArray(val)) return [] as string[];
    return val
      .map(v => (v == null ? "" : String(v)))
      .map(s => s.trim())
      .filter(Boolean);
  };

  const pickReplayRoute = () => {
    const candidates = ["AI-REPLAY-ROOM", "ReplayRoom"] as const;
    for (const name of candidates) {
      try {
        if ((router as any).hasRoute && (router as any).hasRoute(name as any)) {
          return { name } as const;
        }
      } catch (e) {
        // ignore
      }
    }
    // fallback to a stable path
    return { path: "/replay/index" } as const;
  };

  function buildReplayUrl({
    taskId,
    deviceIds,
    scriptIds,
    celeryId
  }: {
    taskId: string | number;
    deviceIds?: Array<string | number>;
    scriptIds?: Array<string | number>;
    celeryId?: string;
  }) {
    const nameOrPath = pickReplayRoute();
    const query: Record<string, string> = {
      task_id: String(taskId)
    };
    const d = normalizeList(deviceIds);
    const s = normalizeList(scriptIds);
    if (d.length) query.device_ids = d.join(",");
    if (s.length) query.script_ids = s.join(",");
    if (celeryId) query.celery_id = String(celeryId);

    const { href } = router.resolve({ ...(nameOrPath as any), query });
    return href;
  }

  function openReplayRoomBak(params: {
    taskId: string | number;
    deviceIds?: Array<string | number>;
    scriptIds?: Array<string | number>;
    celeryId?: string;
    newTab?: boolean; // default true
  }) {
    const href = buildReplayUrl(params);
    if (params.newTab === false) {
      window.location.href = href;
    } else {
      window.open(href, "_blank");
    }
  }

  function openReplayRoom(params: {
    taskId: string | number;
    deviceIds?: Array<string | number>;
    scriptIds?: Array<string | number>;
    celeryId?: string;
    newTab?: boolean; // default true
    blank?: boolean; // default false
  }) {
    const title = `Task.${params.taskId} - 回放室`;

    const parameter: any = {
      task_id: params.taskId
    };

    const d = normalizeList(params.deviceIds);
    const s = normalizeList(params.scriptIds);
    if (d.length) parameter.device_ids = d.join(",");
    if (s.length) parameter.script_ids = s.join(",");
    if (params.celeryId) parameter.celery_id = params.celeryId;

    // 尝试获取回放室路由名称
    const componentName = "AI-REPLAY-ROOM"; // 默认组件名

    navigateTo({
      parameter,
      componentName,
      tagTitle: title,
      blank: params.blank,
      addTag: params.newTab
    });
  }

  function toDetail(
    parameter: LocationQueryRaw | RouteParamsRaw,
    model: "query" | "params"
  ) {
    // ⚠️ 这里要特别注意下，因为vue-router在解析路由参数的时候会自动转化成字符串类型，比如在使用useRoute().route.query或useRoute().route.params时，得到的参数都是字符串类型
    // 所以在传参的时候，如果参数是数字类型，就需要在此处 toString() 一下，保证传参跟路由参数类型一致都是字符串，这是必不可少的环节！！！
    Object.keys(parameter).forEach(param => {
      if (!isString(parameter[param])) {
        parameter[param] = parameter[param].toString();
      }
    });
    if (model === "query") {
      // 保存信息到标签页
      useMultiTagsStoreHook().handleTags("push", {
        path: `/tabs/query-detail`,
        name: "TabQueryDetail",
        query: parameter,
        meta: {
          title: {
            zh: `No.${parameter.id} - 详情信息`,
            en: `No.${parameter.id} - DetailInfo`
          },
          // 如果使用的是非国际化精简版title可以像下面这么写
          // title: `No.${index} - 详情信息`,
          // 最大打开标签数
          dynamicLevel: 3
        }
      });
      // 路由跳转
      router.push({ name: "TabQueryDetail", query: parameter });
    } else if (model === "params") {
      useMultiTagsStoreHook().handleTags("push", {
        path: `/tabs/params-detail/:id`,
        name: "TabParamsDetail",
        params: parameter,
        meta: {
          title: {
            zh: `No.${parameter.id} - 详情信息`,
            en: `No.${parameter.id} - DetailInfo`
          }
          // 如果使用的是非国际化精简版title可以像下面这么写
          // title: `No.${index} - 详情信息`,
        }
      });
      router.push({ name: "TabParamsDetail", params: parameter });
    }
  }

  // 用于页面刷新，重新获取浏览器地址栏参数并保存到标签页
  const initToDetail = (model: "query" | "params") => {
    if (getParameter) toDetail(getParameter, model);
  };

  /**
   * 设置全屏模式
   * @param enableFullscreen 是否启用全屏，如果不传则从路由参数中获取
   * @param hideTagBar 是否隐藏标签栏，默认与全屏状态一致
   */
  function setFullscreen(enableFullscreen?: boolean, hideTagBar?: boolean) {
    const isFullscreen =
      enableFullscreen ?? getParameter?.fullscreen === "true";
    const shouldHideTagBar = hideTagBar ?? isFullscreen;

    nextTick(() => {
      // 设置侧边栏隐藏状态
      pureSetting.changeSetting({
        key: "hiddenSideBar",
        value: isFullscreen
      });

      // 设置标签栏显示状态
      emitter.emit("tagViewsChange", shouldHideTagBar as unknown as string);

      // 处理样式覆盖
      if (isFullscreen) {
        addFullscreenStyles();
      } else {
        removeFullscreenStyles();
      }
    });
  }

  /**
   * 添加全屏样式
   */
  function addFullscreenStyles() {
    // 如果已经添加过样式表，先移除
    if (fullscreenStyleSheet.value) {
      removeFullscreenStyles();
    }

    try {
      // 创建新的样式表
      const sheet = new CSSStyleSheet();

      // 添加样式规则
      const rules = [
        "body[layout=horizontal] .main-hidden .fixed-header + .app-main { padding-top: 0px !important; }",
        "body[layout=vertical] .main-hidden .fixed-header + .app-main { padding-top: 0px !important; }",
        // 可以根据需要添加更多全屏相关样式
        "body[layout=horizontal] .main-hidden .fixed-header + .app-main { padding-left: 0px !important; }",
        "body[layout=horizontal] .main-hidden .fixed-header + .app-main { padding-right: 0px !important; }"
      ];

      rules.forEach(rule => {
        sheet.insertRule(rule);
      });

      // 添加到文档
      document.adoptedStyleSheets = [...document.adoptedStyleSheets, sheet];
      fullscreenStyleSheet.value = sheet;
    } catch (error) {
      console.warn("Failed to add fullscreen styles:", error);
      // 降级方案：直接设置内联样式
      fallbackToInlineStyles(true);
    }
  }

  /**
   * 移除全屏样式
   */
  function removeFullscreenStyles() {
    if (fullscreenStyleSheet.value) {
      try {
        const index = document.adoptedStyleSheets.indexOf(
          fullscreenStyleSheet.value
        );
        if (index > -1) {
          document.adoptedStyleSheets = document.adoptedStyleSheets.filter(
            (_, i) => i !== index
          );
        }
      } catch (error) {
        console.warn("Failed to remove fullscreen styles:", error);
        // 降级方案：恢复内联样式
        fallbackToInlineStyles(false);
      }
      fullscreenStyleSheet.value = null;
    }
  }

  /**
   * 降级方案：直接操作DOM元素的内联样式
   */
  function fallbackToInlineStyles(enable: boolean) {
    const selectors = [
      "body[layout=horizontal] .main-hidden .fixed-header + .app-main",
      "body[layout=vertical] .main-hidden .fixed-header + .app-main"
    ];

    selectors.forEach(selector => {
      const element = document.querySelector(selector) as HTMLElement;
      if (element) {
        if (enable) {
          element.style.setProperty("padding-top", "0px", "important");
          element.style.setProperty("padding-left", "0px", "important");
          element.style.setProperty("padding-right", "0px", "important");
        } else {
          element.style.removeProperty("padding-top");
          element.style.removeProperty("padding-left");
          element.style.removeProperty("padding-right");
        }
      }
    });
  }

  /**
   * 切换全屏状态
   */
  function toggleFullscreen() {
    const currentState = getParameter?.fullscreen === "true";
    setFullscreen(!currentState);
  }

  /**
   * 退出全屏模式
   */
  function exitFullscreen() {
    setFullscreen(false);
  }

  return {
    navigateTo,
    navigateToTestcaseList,
    navigateToScriptDetail,
    navigateToPlanList,
    navigateToPlanDetail,
    navigateToReportDetail,
    navigateToOcrResult,
    navigateToCatalog,
    navigateToDebugReportList,
    navigateToPlanReportList,
    navigateToReportList,
    navigateToExecutorDownload,
    // replay
    buildReplayUrl,
    openReplayRoom,
    openReplayRoomBak,
    navigateToTasksPage,
    // fullscreen
    setFullscreen,
    toggleFullscreen,
    exitFullscreen,
    removeFullscreenStyles,
    toDetail,
    initToDetail,
    getParameter,
    router
  };
}
