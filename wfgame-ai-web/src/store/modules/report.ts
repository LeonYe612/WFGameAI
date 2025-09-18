import { defineStore } from "pinia";
import { store } from "@/store";
import {
  detailReport,
  listReportCases,
  detailReportStep,
  robotReportData,
  pressureReportData,
  betReportData,
  arrangeReportData
} from "@/api/report";
import { superRequest } from "@/utils/request";
import {
  resultEnum,
  protoGenreEnum,
  planTypeEnum,
  runStatusEnum
} from "@/utils/enums";
import { showRewardReturn } from "@/api/outter";
import { assetItem, CaseQueueItem } from "../types";

interface ProtoDataItem {
  remark: string;
  modifier: any;
  type: string;
  field: string;
  field_id: number;
  operator: string;
  value: any;
  children: ProtoDataItem[] | null; // 这里是递归类型定义，表示每个元素的 children 属性也是 ProtoDataItem 类型的数组
  deleted: boolean;
}

interface Proto {
  proto_id: number;
  proto_name: string;
  proto_message: string;
  proto_contents: string[];
  proto_data: ProtoDataItem[]; // 正确定义了 proto_data 属性为 ProtoDataItem 类型的数组
  code: number;
  result: number;
}

/** 初始值 */
const defaultReport = () => {
  return {
    id: null,
    plan_id: null,
    task_id: null,
    name: "",
    env: null, // 报告执行环境
    server_no: null,
    account: "",
    prefix: "",
    parent_id: 0, // 父报告ID, 0表示主报告
    plan_type: 0,
    run_type: null, // 1: 调试-DEBUG 2: 单次-SINGLE 3: 定时-SCHEDULE 4: 周期-CIRCLE
    run_info: {
      schedule: null, // 定时执行类型：只需要采集一个日期时间即可。示例："2021-01-01 12:00:00"
      circle: {
        // 周期执行类型：需要采集一个日期范围，指定一周的哪些天，一个运行时间
        date_range: ["", ""], // 周期运行的日期范围，示例：["2021-01-01 00:00:00", "2021-01-31 23:59:59"]
        which_days: [], // 在一周的哪些天执行, 示例: [1, 2, 4, 7]
        run_time: "" // 运行时间, 示例："12:00:00"
      }
    },
    inform: null,
    run_status: null, // 运行状态: 1. 未开始 | 2.运行中 | 3.结束 | 4. 投递任务成功中 | 5. 投递任务成功 | 6. 投递任务失败
    result: null, // 1. 成功 | 2.失败 | 3.未开始
    spend_time: {
      start: null,
      end: null
    },
    // ============  用例列表相关字段 ================
    list: [],
    total: 0, // 总用例数量
    statistics: {
      success: 0, // 成功用例数量
      failure: 0, // 失败用例数量
      pending: 0, // 待测用例数量
      total_time_taken: 0, // 总耗时
      average_time_taken: 0 // 平均耗时
    },
    remark: "",
    tasks: [], // taskId: string | testcase 接口返回
    logs: [], // testcase 接口返回
    robot_data: [],
    // 压测相关数据
    pressure_data: {
      url: ""
    }
  };
};
const defaultPieData = () => {
  return [
    { value: 0, name: "成功" },
    { value: 0, name: "失败" },
    { value: 0, name: "待测" }
  ];
};
const defaultDescData = () => {
  return [
    {
      name: "总用例数",
      value: 0
    },
    {
      name: "请求总耗时",
      value: 0
    },
    {
      // 总耗时 / 总用例步骤数(一个步骤只有一个请求)
      name: "请求平均耗时",
      value: 0
    }
  ];
};
const formatJmxUrl = (taskId: number, filePath: string) => {
  const baseUrl = "https://autoapi.wanfeng-inc.com/jmeter-task";
  return `${baseUrl}/task${taskId}/${filePath}`;
};
const defaultJmxData = () => {
  return {
    runParams: {
      server: "", // 执行Jmeter的服务器IP
      ref: "", // 分支
      command: "", // 执行命令
      jmx: {
        name: "",
        url: ""
      } as assetItem, // JMX 文件路径
      assets: [] as assetItem[] // 已选依赖文件
    },
    htmlUrl: "", // JMX 执行结果的HTML页面地址
    files: [] as assetItem[] // JMX 依赖的文件列表
  };
};
export const useReportStore = defineStore({
  id: "pure-report",
  state: () => ({
    report: defaultReport(),
    pieData: defaultPieData(),
    descData: defaultDescData(),
    // 用例列表: 动态变化的, 支持过滤状态
    resultFilter: "ALL",
    caseList: [],
    robotData: [],
    jmxData: defaultJmxData(), // jmx 报告专用数据
    arrangeList: [] as CaseQueueItem[][],
    activeCaseIndex: -1,
    activeStepIndex: -1,
    currentStep: {
      step_id: 0,
      name: "",
      version: 0,
      result: 0,
      send: [],
      recv: [],
      real_recv: []
    },
    // 相关组件间的共享状态值
    shareState: {
      // loading
      loading: false, // 详情加载loading
      stepLoading: false,
      enableAutoRefresh: false,
      refreshTimer: null,
      logConsoleVisible: false,
      showRewardReturnFlag: false
    }
  }),
  actions: {
    assignValue(to: any, from: any) {
      Object.keys(from).forEach(key => {
        if (key in to) {
          const value = to[key];
          if (Array.isArray(value)) {
            // 数组类型：不能改变原数组的引用， 先清空原数组，再push新数据
            to[key].splice(0, to[key].length);
            if (from[key] && from[key].length > 0) {
              to[key].push(...from[key]);
            }
          } else if (typeof value === "object" && value !== null) {
            // 如果属性值是对象，则递归处理
            this.assignValue(to[key], from[key]);
          } else {
            // 其他类型的属性直接赋值
            to[key] = from[key];
          }
        }
      });
    },
    /** 设置 Report 中的信息 */
    SET_REPORT(obj: any) {
      this.assignValue(this.report, obj);
    },
    /** 重置info的信息 */
    RESET_REPORT() {
      this.assignValue(this.report, defaultReport());
    },
    /** 重置所有信息 */
    RESET_ALL() {
      this.RESET_CASE_LIST();
      this.assignValue(this.report, defaultReport());
      this.assignValue(this.pieData, defaultPieData());
      this.assignValue(this.descData, defaultDescData());
    },
    /** 设置饼图数据 */
    SET_PIE_DATA(data: any) {
      this.pieData.splice(0, this.pieData.length);
      this.pieData.push({ value: data.statistics?.success || 0, name: "成功" });
      this.pieData.push({ value: data.statistics?.failure || 0, name: "失败" });
      this.pieData.push({ value: data.statistics?.pending || 0, name: "待测" });
    },
    /** 设置描述数据 */
    SET_DESC_DATA(data: any) {
      this.descData[0].value = (data.total || "❔") + " 个";
      this.descData[1].value =
        (data.statistics?.total_time_taken?.toFixed(3) || "❔") + " 秒";
      this.descData[2].value =
        (data.statistics?.average_time_taken?.toFixed(3) || "❔") + " 秒";
    },
    /** 设置用例列表 */
    SET_CASE_LIST(
      filter: "ALL" | "SUCCESS" | "FAILURE" | "PENDING" = "ALL",
      resetActiveIndex = true
    ) {
      // 清空原有数据
      this.caseList.splice(0, this.caseList.length);
      // 过滤数据
      if (filter === "ALL") {
        this.caseList.push(...this.report.list);
      } else {
        const filterResult = this.report.list.filter(
          (item: any) => item.result === resultEnum[filter].value
        );
        this.caseList.push(...filterResult);
      }
      this.resultFilter = filter;
      if (resetActiveIndex) {
        this.activeCaseIndex = -1;
        this.activeStepIndex = -1;
      }
    },
    RESET_CASE_LIST() {
      this.caseList.splice(0, this.caseList.length);
      this.resultFilter = "ALL";
      this.activeCaseIndex = -1;
      this.activeStepIndex = -1;
    },
    /** 设置机器人执行结果列表 */
    SET_ROBOT_DATA(filter: "ALL" | "SUCCESS" | "FAILURE" | "PENDING" = "ALL") {
      // 清空原有数据
      this.robotData.splice(0, this.robotData.length);
      // 过滤数据
      if (filter === "ALL") {
        this.robotData.push(...this.report.robot_data);
      } else {
        const filterResult = this.report.robot_data.filter(
          (item: any) => item.result == resultEnum[filter].value
        );
        this.robotData.push(...filterResult);
      }
      this.resultFilter = filter;
    },
    /** 设置编排报告列表 */
    SET_ARRANGE_LIST(
      filter: "ALL" | "SUCCESS" | "FAILURE" | "PENDING" = "ALL"
    ) {
      // 清空原有数据
      this.arrangeList.splice(0, this.arrangeList.length);
      // 过滤数据
      if (filter === "ALL") {
        this.arrangeList.push(...this.report.list);
      } else {
        for (const caseList of this.report.list) {
          const filterResult = caseList.filter(
            (item: any) => item.result == resultEnum[filter].value
          );
          // 将过滤后的结果添加到编排列表中
          this.arrangeList.push(filterResult);
        }
      }
      this.resultFilter = filter;
    },
    // 将Proto对应的数据数据结构转换成json字符串
    convertProtoToJson(item: Proto) {
      const protoDataLen = item?.proto_data?.length || 0;
      if (protoDataLen == 0) {
        return JSON.stringify(
          {
            code: item.code,
            body: ""
          },
          null,
          4
        );
      }
      const jsonResult = this.convertDataItemsToJson(item.proto_data);
      const jsonStr = JSON.stringify(
        {
          code: item.code,
          body: jsonResult
        },
        null,
        4
      );
      return jsonStr;
    },
    // todo: old version 稳定后删除此函数
    convertToJson(protoData: ProtoDataItem[]) {
      const result = {};
      for (let i = 0; i < protoData.length; i++) {
        const field = protoData[i];
        const fieldName = field.field;
        const fieldValue = field.value;
        if (field.deleted) {
          continue;
        }

        // 判断是否为数组
        if (field.modifier === "repeated") {
          const repeatedArr = [];
          if (Array.isArray(field.children)) {
            if (field.children.length == 0) {
              if (field.operator === "=") {
                result[fieldName] = field.value;
              } else if (field.operator === "!=") {
                result[fieldName] = `!${field.value}`;
              }
            } else {
              for (let j = 0; j < field.children.length; j++) {
                // item 级别
                const childField = field.children[j];
                let childResult;
                if (
                  Array.isArray(childField.children) &&
                  childField.children.length > 0
                ) {
                  // a. 非基础类型 item
                  childResult = this.convertToJson(childField.children);
                } else {
                  // b. 基础类型 item
                  // if (childField.operator === "=") {
                  //   result[fieldName] = childField.value;
                  // } else if (childField.operator === "!=") {
                  //   result[fieldName] = `!${childField.value}`;
                  // }
                  if (childField.operator === "=") {
                    childResult = childField.value;
                  } else if (childField.operator === "!=") {
                    childResult = `!${childField.value}`;
                  }
                }
                repeatedArr.push(childResult);
              }
              result[fieldName] = repeatedArr;
            }
          }
        } else {
          if (Array.isArray(field.children) && field.children.length > 0) {
            result[fieldName] = this.convertToJson(field.children);
          } else {
            if (fieldValue != null && fieldValue != undefined) {
              if (field.operator === "=") {
                result[fieldName] = field.value;
              } else if (field.operator === "!=") {
                result[fieldName] = `!${field.value}`;
              }
            }
          }
        }
      }
      return result;
    },
    // new版本：支持map的转化，如果需要回退请修改为：convertToJson 调用
    convertDataItemsToJson(protoData) {
      const result = {};
      for (const field of protoData) {
        if (field.deleted) {
          continue;
        }

        const fieldName = field.field;
        let fieldValue = field.value;
        let valueToAssign = fieldValue;

        // A. 参数有子节点
        if (field?.children?.length) {
          // A.1 repeated 类型
          if (field.modifier === "repeated") {
            valueToAssign = field.children.map(childField => {
              if (childField?.children?.length) {
                return this.convertDataItemsToJson(childField.children);
              }
              return childField.operator === "="
                ? childField.value
                : `!${childField.value}`;
            });
          }
          // A.2 map 类型
          if (field.modifier === "map") {
            valueToAssign = {};
            for (const mapItem of field.children) {
              const keyField = mapItem.children[0];
              const valueField = mapItem.children[1];
              if (valueField?.children?.length) {
                valueToAssign[keyField.value] = this.convertDataItemsToJson(
                  valueField.children
                );
              } else {
                valueToAssign[keyField.value] = valueField.value;
              }
            }
          }
          // A.3 optional 类型
          if (field.modifier !== "repeated" && field.modifier !== "map") {
            valueToAssign = this.convertDataItemsToJson(field.children);
          }
          result[fieldName] = valueToAssign;
          continue;
        }

        // B. 参数无子节点
        if (field.modifier === "repeated") {
          // 无子节点的 repeated 类型显示为空数组
          fieldValue = [];
        }
        valueToAssign = field.operator === "=" ? fieldValue : `!${fieldValue}`;
        result[fieldName] = valueToAssign;
      }

      return result;
    },
    /** 设置当前激活的用例步骤数据 */
    SET_CURRENT_STEP(data: any) {
      // 将send、recv、real_recv中的数据转换成字符串
      const fields = [
        protoGenreEnum.SEND.value,
        protoGenreEnum.RECV.value,
        protoGenreEnum.REALRECV.value
      ];
      fields.forEach(key => {
        if (!data[key]) return;
        data[key]?.forEach(item => {
          item.proto_text = this.convertProtoToJson(item);
        });
      });
      // 赋值
      this.assignValue(this.currentStep, data);
    },
    /** 根据 enableAutoRefresh 的值开启或关闭自动刷新 */
    async toggleAutoRefresh(enable: boolean) {
      // 机器人报告的刷新频率，可以不用那么高
      const interval = 2000;

      this.shareState.enableAutoRefresh = enable;

      const refreshAllData = async () => {
        this.fetchReportDetail(data => {
          if (data?.plan_type === planTypeEnum.ROBOT.value) {
            this.fetchRobotReportData();
          } else if (data?.plan_type === planTypeEnum.BET.value) {
            this.fetchBetReportData(false);
          } else if (data?.plan_type === planTypeEnum.JMX.value) {
            this.fetchJmxReportDetail();
          } else if (
            data?.plan_type === planTypeEnum.ARRANGE.value &&
            data?.parent_id === 0
          ) {
            // 特殊说明：编排类型为了复用基础报告类型
            // a. 只有主报告入口时显示 -> 编排报告组件页面
            // b. 点击用例将切换到子用例的普通报告组件
            this.fetchArrangeReportData();
          } else if (
            data?.plan_type === planTypeEnum.PRESS.value ||
            data?.plan_type === planTypeEnum.LOAD_TEST.value ||
            data?.plan_type === planTypeEnum.FIRE.value
          ) {
            data.tasks = [`PLAN-${data.plan_id}|TASK-${data.task_id}`];
            this.SET_REPORT(data);
            this.fetchPressureReportData();
          } else {
            this.fetchReportCases(false);
            this.fetchStepDetail();
          }
        });
      };
      // 利用 timer 每间隔 interval 秒刷新一次
      if (this.shareState.enableAutoRefresh) {
        refreshAllData();
        this.shareState.refreshTimer = setInterval(refreshAllData, interval);
      } else {
        if (this.shareState.refreshTimer) {
          clearInterval(this.shareState.refreshTimer);
        }
      }
    },
    /** 根据 id 查询报告详情 */
    async fetchReportDetail(onSucceed?: Function) {
      superRequest({
        apiFunc: detailReport,
        apiParams: { id: this.report.id },
        onBeforeRequest: () => {
          this.shareState.loading = true;
        },
        onSucceed: data => {
          // 报告状态不从detail中获取, 从测试用例接口的 complex_result 获取
          delete data.result;
          this.SET_REPORT(data);
          typeof onSucceed === "function" && onSucceed(data);
        },
        onCompleted: () => {
          this.shareState.loading = false;
        }
      });
    },
    /** 根据 id 查询 JMX 报告详情 */
    async fetchJmxReportDetail(onSucceed?: Function) {
      superRequest({
        apiFunc: detailReport,
        apiParams: { id: this.report.id },
        onBeforeRequest: () => {
          this.shareState.loading = true;
        },
        onSucceed: data => {
          data.tasks = [`PLAN-${data.plan_id}|TASK-${data.task_id}`];
          // 报告状态与 detail 中的 result 一致
          this.SET_REPORT(data);
          // 如果发现 Result 结果变更，则自动关闭自动刷新
          if (this.report.run_status === runStatusEnum.COMPLETED.value) {
            this.toggleAutoRefresh(false);
          }
          // 如果是 JMX 类型的报告，则需要设置 JMX 相关数据
          if (this.report.result === resultEnum.SUCCESS.value) {
            const runParams = data.case_queue;
            const jmxData = {
              runParams: runParams,
              htmlUrl: formatJmxUrl(data.task_id, "html/index.html"),
              files: [
                {
                  name: runParams?.jmx.name || "jmeter.jmx",
                  url: formatJmxUrl(data.task_id, runParams?.jmx.name)
                },
                ...(runParams.assets || []).map((item: assetItem) => ({
                  name: item.name,
                  url: formatJmxUrl(data.task_id, item.name)
                })),
                {
                  name: "jmeter.log",
                  url: formatJmxUrl(data.task_id, "jmeter.log")
                },
                {
                  name: "jmeter.jtl",
                  url: formatJmxUrl(data.task_id, "jmeter.jtl")
                }
              ]
            };
            this.jmxData = jmxData;
          }
          // 设置 JMX 相关数据
          typeof onSucceed === "function" && onSucceed(data);
        },
        onCompleted: () => {
          this.shareState.loading = false;
        }
      });
    },
    /** 根据 id 查询编排类型的报告数据 */
    async fetchArrangeReportData() {
      superRequest({
        apiFunc: arrangeReportData,
        apiParams: { id: this.report.id },
        onBeforeRequest: () => {
          this.shareState.loading = true;
        },
        onSucceed: data => {
          data = data || {};
          data.result = data.complex_result;
          this.SET_REPORT(data);
          // 如果发现 Result 结果变更，则自动关闭自动刷新
          if (this.report.result !== resultEnum.PENDING.value) {
            this.toggleAutoRefresh(false);
          }
          this.SET_ARRANGE_LIST(this.resultFilter);
          this.SET_PIE_DATA(data);
          this.SET_DESC_DATA(data);
        },
        onCompleted: () => {
          this.shareState.loading = false;
        }
      });
    },
    /** 根据 id 查询报告中的用例列表 */
    // resetActiveIndex: 是否重置当前激活的用例和步骤索引
    async fetchRobotReportData() {
      superRequest({
        apiFunc: robotReportData,
        apiParams: { id: this.report.id },
        onBeforeRequest: () => {
          this.shareState.loading = true;
        },
        onSucceed: data => {
          data = data || {};
          data.result = data.complex_result;
          this.SET_REPORT(data);
          // 如果发现 Result 结果变更，则自动关闭自动刷新
          if (this.report.result !== resultEnum.PENDING.value) {
            this.toggleAutoRefresh(false);
          }
          this.SET_ROBOT_DATA(this.resultFilter);
          this.SET_PIE_DATA(data);
          this.SET_DESC_DATA(data);
        },
        onCompleted: () => {
          this.shareState.loading = false;
        }
      });
    },
    /** 根据 id 查询自定义压测报告数据 */
    async fetchPressureReportData() {
      superRequest({
        apiFunc: pressureReportData,
        apiParams: { id: this.report.id },
        onBeforeRequest: () => {
          this.shareState.loading = true;
        },
        onSucceed: data => {
          if (data?.url) {
            this.SET_REPORT({
              pressure_data: data
            });
          }
          // 如果发现 Result 结果变更，则自动关闭自动刷新
          if (this.report.run_status === runStatusEnum.COMPLETED.value) {
            this.toggleAutoRefresh(false);
          }
        },
        onCompleted: () => {
          this.shareState.loading = false;
        }
      });
    },
    // 根据 id 查询投注类型报告中的用例列
    // resetActiveIndex: 是否重置当前激活的用例和步骤索引
    async fetchBetReportData(onSucceed?: Function) {
      superRequest({
        apiFunc: betReportData,
        apiParams: { id: this.report.id },
        onBeforeRequest: () => {
          this.shareState.loading = true;
        },
        onSucceed: data => {
          // 报告状态不从detail中获取, 从测试用例接口的 complex_result 获取
          if (
            data.result === resultEnum.SUCCESS.value ||
            data.result === resultEnum.FAILURE.value
          ) {
            this.toggleAutoRefresh(false);
            // 投注类型计划额外获取返奖率接口数据
            this.showRewardFlag();
          }
          delete data.result;
          this.SET_REPORT(data);
          typeof onSucceed === "function" && onSucceed(data);
        },
        onCompleted: () => {
          this.shareState.loading = false;
        }
      });
    },
    /** 根据 id 查询报告中的用例列表 */
    // resetActiveIndex: 是否重置当前激活的用例和步骤索引
    async fetchReportCases(resetActiveIndex = true) {
      superRequest({
        apiFunc: listReportCases,
        apiParams: { id: this.report.id },
        onBeforeRequest: () => {
          this.shareState.loading = true;
        },
        onSucceed: data => {
          data = data || {};
          data.result = data.complex_result;
          this.SET_REPORT(data);
          // 如果发现 Result 结果变更，则自动关闭自动刷新
          if (this.report.result !== resultEnum.PENDING.value) {
            this.toggleAutoRefresh(false);
            // 判断是否是投注类型游戏，是否要显示对应的返奖率查询按钮
            this.showRewardFlag();
          }

          this.SET_PIE_DATA(data);
          this.SET_DESC_DATA(data);
          this.SET_CASE_LIST(this.resultFilter, resetActiveIndex);
        },
        onCompleted: () => {
          this.shareState.loading = false;
        }
      });
    },
    /** 根据当前的 StepId 和 report.id 去查询步骤中的数据详情 */
    async fetchStepDetail() {
      // todo: 这里可以增加前端缓存处理，已经查看过的stepId在缓存中查找
      if (this.activeCaseIndex == -1 || this.activeStepIndex == -1) return;
      const result_id = this.caseList[this.activeCaseIndex].result_id;
      const step_id =
        this.caseList[this.activeCaseIndex].steps[this.activeStepIndex].step_id;
      const step_name =
        this.caseList[this.activeCaseIndex].steps[this.activeStepIndex].name;
      superRequest({
        apiFunc: detailReportStep,
        apiParams: {
          result_id,
          step_id,
          step_name
        },
        onBeforeRequest: () => {
          this.shareState.stepLoading = true;
        },
        onSucceed: data => {
          // 将 data 赋值给 currentStep
          this.SET_CURRENT_STEP(data);
        },
        onCompleted: () => {
          this.shareState.stepLoading = false;
        }
      });
    },
    async showRewardFlag() {
      superRequest({
        apiFunc: showRewardReturn,
        apiParams: { id: this.report.id },
        enableFailedMsg: false,
        onBeforeRequest: () => {
          this.shareState.showRewardReturnFlag = false;
        },
        onSucceed: data => {
          this.shareState.showRewardReturnFlag = data.show_reward || false;
        }
      });
    }
  }
});

export function useReportStoreHook() {
  return useReportStore(store);
}
