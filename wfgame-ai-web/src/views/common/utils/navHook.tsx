import { isString, isEmpty } from "@pureadmin/utils";
import { useMultiTagsStoreHook } from "@/store/modules/multiTags";
import {
  useRouter,
  useRoute,
  type LocationQueryRaw,
  type RouteParamsRaw
} from "vue-router";

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

  function navigateToTestcaseDetail(id?: number, version?: number) {
    let title = "";
    if (!id) {
      // 新增用例
      id = 0;
      version = 0;
      title = "新增用例";
    } else {
      // 编辑用例
      title = `ID.${id} - 编辑用例`;
    }
    navigateTo({
      parameter: {
        id: id,
        version: version
      },
      componentName: "TestcaseDetail",
      tagTitle: title
    });
  }

  function navigateToTestcaseList() {
    router.push({ name: "TestCaseList" });
  }

  function navigateToPlanList() {
    router.push({ name: "PlanManagement" });
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
    addTag = true
  ) {
    const title = `ID.${id} - 测试报告`;
    navigateTo({
      parameter: {
        id: id,
        ...params
      },
      componentName: "ReportDetail",
      tagTitle: title,
      blank,
      addTag
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

  return {
    navigateTo,
    navigateToTestcaseList,
    navigateToTestcaseDetail,
    navigateToPlanList,
    navigateToPlanDetail,
    navigateToReportDetail,
    navigateToOcrResult,
    navigateToCatalog,
    navigateToDebugReportList,
    navigateToPlanReportList,
    navigateToExecutorDownload,
    toDetail,
    initToDetail,
    getParameter,
    router
  };
}
