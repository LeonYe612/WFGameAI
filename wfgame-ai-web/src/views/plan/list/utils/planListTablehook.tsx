import {
  listPlan,
  delPlan,
  editPlan,
  implementPlan,
  restartPlan,
  getWorkerServerNames,
  getWebhookPlanMockData
} from "@/api/plan";
import { detailCase } from "@/api/testcase";
import { listReportPlans } from "@/api/report";
import { superRequest } from "@/utils/request";
import { ref, computed, reactive, onUnmounted, onMounted } from "vue";
import { useNavigate } from "@/views/common/utils/navHook";
import { usePlanStoreHook } from "@/store/modules/plan";
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { cloneDeep } from "@pureadmin/utils";
import { message } from "@/utils/message";
import { planRunTypeEnum, planStatusEnum, runStatusEnum } from "@/utils/enums";
import { backendHost } from "@/api/utils";

const store = usePlanStoreHook();
const testcaseStore = useTestcaseStoreHook();

export const usePlanListTable = (props?: any) => {
  const tableRef = props.tableRef;
  const dataList = ref([]);
  const dataTotal = ref(0);
  const loading = ref(false);
  const delLoadings = ref({});
  const copyLoadings = ref({});
  const rewardDialogRef = ref(null); // 返奖率报告弹窗
  const showPlanConfirmer = ref(false);
  const workerNames = reactive({});

  // 模拟 webhook 请求相关变量
  const showApiMan = ref(false);
  const apiMethod = ref("get");
  const apiUrl = ref("");
  const apiJson = ref("");

  const {
    navigateToPlanDetail,
    navigateToPlanReportList,
    navigateToReportDetail
  } = useNavigate();

  /** 查询 Worker Names */
  const fetchWorkerNames = () => {
    superRequest({
      apiFunc: getWorkerServerNames,
      onSucceed: data => {
        if (data) {
          Object.assign(workerNames, data);
        }
      }
    });
  };

  const workerLabel = computed(() => {
    return (workerName: string) => {
      return workerNames[workerName] || "UNKONWN";
    };
  });

  /** 新增计划 */
  const handleCreate = () => {
    store.RESET_INFO(); // 重置store中的计划信息
    navigateToPlanDetail();
  };

  /** 根据row获取tag类型 */
  const getRunTypeTag = (
    row
  ): "" | "success" | "warning" | "info" | "danger" => {
    const TAG_TYPE_MAP = {
      [planRunTypeEnum.SINGLE.value]: "info",
      [planRunTypeEnum.SCHEDULE.value]: "success",
      [planRunTypeEnum.CIRCLE.value]: "warning",
      [planRunTypeEnum.WEBHOOK.value]: "" // 默认样式
    };

    return (TAG_TYPE_MAP[row.run_type] || "") as
      | ""
      | "success"
      | "warning"
      | "info"
      | "danger"; // 默认类型为 info
  };

  /** 编辑计划 */
  const handleEdit = row => {
    store.RESET_INFO(); // 重置store中的计划信息
    store.SET_INFO(row); // 设置store中的计划信息
    store.UPDATE_ASSIGN_PARAMS(cloneDeep(row)); // 动态更新某些指定参数
    navigateToPlanDetail(row.id);
  };

  /** 启用禁用计划 */
  const handleEnable = async (value, row) => {
    await superRequest({
      apiFunc: editPlan,
      apiParams: { id: row.id, disabled: value },
      enableSucceedMsg: true,
      onSucceed: () => {
        // 如果是 webhook 类型的计划, 修改禁用状态后无需重新实施
        if (row.run_type === planRunTypeEnum.WEBHOOK.value) {
          return;
        }
        setTimeout(() => {
          superRequest({
            apiFunc: implementPlan,
            apiParams: { id: row.id }
          });
        }, 500);
      }
    });
  };

  /** 复用计划参数 */
  const handleReplay = row => {
    // 获取计划信息中的用例ID
    if (!row.case_queue?.[0]?.length) {
      message("计划中未包含任何用例！", { type: "warning" });
      return;
    }
    const caseItem = row.case_queue[0][0];
    // 查询计划中包含的用例信息，将用例信息存入 testcaseStore
    superRequest({
      apiFunc: detailCase,
      apiParams: {
        id: caseItem.case_base_id,
        version: caseItem.version
      },
      onSucceed: (data: any) => {
        testcaseStore.SET_BASE_INFO({
          ...data,
          id: caseItem.case_base_id,
          version: caseItem.version
        });
        // 将计划信息存入store
        store.RESET_INFO(); // 重置store中的计划信息
        store.SET_INFO(row); // 设置store中的计划信息
        store.UPDATE_ASSIGN_PARAMS(cloneDeep(row)); // 动态更新某些指定参数
        showPlanConfirmer.value = true;
      }
    });
  };

  /** 查看计划报告 */
  const handleReport = row => {
    const keyword = `PLAN-ID:${row.id}`;
    // 确认此计划对应的报告数量
    // a. resultCount = 1: 直接跳转到报告详情页
    // b. resultCount > 1: 跳转到报告列表页
    // /v1/reports/plans?page=1&size=20&keyword=&plan_type=3&run_type=&filter_self=2
    superRequest({
      apiFunc: listReportPlans,
      apiParams: {
        page: 1,
        size: 5,
        keyword,
        plan_type: row.plan_type,
        filter_self: 2 // 查看全部
      },
      onSucceed: data => {
        const totalResult = data?.total || 0;
        if (totalResult === 0) {
          message("未找到此计划对应的报告！", { type: "warning" });
        } else if (totalResult === 1) {
          const resultId = data!.list[0].id;
          navigateToReportDetail(resultId, true);
        } else {
          navigateToPlanReportList(row.plan_type, keyword);
        }
      }
    });
  };

  /** 查看返奖率报告弹窗 */
  const handleRewardReport = row => {
    const keyword = `PLAN-ID:${row.id}`;
    // 确认此计划对应的报告数量
    // a. resultCount = 1: 直接跳转到报告详情页
    // b. resultCount > 1: 跳转到报告列表页
    // /v1/reports/plans?page=1&size=20&keyword=&plan_type=3&run_type=&filter_self=2
    superRequest({
      apiFunc: listReportPlans,
      apiParams: {
        page: 1,
        size: 5,
        keyword,
        plan_type: row.plan_type,
        filter_self: 2 // 查看全部
      },
      onSucceed: data => {
        const totalResult = data?.total || 0;
        if (totalResult === 0) {
          message("未找到此计划对应的报告！", { type: "warning" });
        } else if (totalResult === 1) {
          const reportId = data!.list[0].id;
          // 先查询确认是否有返奖率报告
          rewardDialogRef.value?.fetchItems(reportId, res => {
            if (!res?.data?.special_fish?.length && !res?.data?.room?.length) {
              message(`未找到此报告[id:${reportId}]对应的返奖率数据！`, {
                type: "warning"
              });
              return;
            }
            rewardDialogRef.value?.show(reportId, () => {});
          });
        } else {
          navigateToPlanReportList(row.plan_type, keyword);
        }
      }
    });
  };

  /** 拷贝计划 */
  // const handleCopy = async (row: any) => {
  //   await superRequest({
  //     apiFunc: copyCase,
  //     apiParams: { id: row.id },
  //     enableSucceedMsg: true,
  //     onBeforeRequest: () => {
  //       copyLoadings.value[row.id] = true;
  //     },
  //     onSucceed: data => {
  //       // 刷新列表显示
  //       fetchData();
  //       // 跳转编辑页面
  //       const newCaseId = data.id;
  //       navigateTo({
  //         parameter: {
  //           id: newCaseId,
  //           version: 1
  //         },
  //         componentName: "TestcaseDetail",
  //         tagTitle: `ID.${newCaseId} - 编辑计划`
  //       });
  //     },
  //     onCompleted: () => {
  //       delete copyLoadings.value[row.id];
  //     }
  //   });
  // };

  /** 删除计划 */
  async function handleDelete(row: any) {
    await superRequest({
      apiFunc: delPlan,
      apiParams: { id: row.id },
      enableSucceedMsg: true,
      succeedMsgContent: "删除成功！",
      onBeforeRequest: () => {
        delLoadings.value[row.id] = true;
      },
      onSucceed: () => {
        fetchData();
      },
      onCompleted: () => {
        delete delLoadings.value[row.id];
      }
    });
  }

  const autoRefresh = ref(false);
  let refreshTimer: ReturnType<typeof setTimeout> | null = null;

  // 清理定时器
  function clearRefreshTimer() {
    if (refreshTimer) {
      clearTimeout(refreshTimer);
      refreshTimer = null;
    }
  }

  const fetchData = async () => {
    // 仪表盘页面需要展示未开始的测试计划
    const queryForm = { ...props.queryForm };
    if (props.run_filter) {
      queryForm.run_filter = true;
    }
    await superRequest({
      apiFunc: listPlan,
      apiParams: queryForm,
      onBeforeRequest: () => {
        loading.value = true;
      },
      onSucceed: data => {
        dataList.value = data?.list;
        dataTotal.value = data?.total;
        if (autoRefresh.value) {
          tryAutoRefresh(data?.list || []);
        }
      },
      onCompleted: () => {
        loading.value = false;
      }
    });
  };

  const tryAutoRefresh = data => {
    if (!autoRefresh.value) return;
    const interval = 5000; // 5秒
    // 判断是否有未完成的计划
    // const hasUnfinished = data.some(
    //   item => item.run_status !== planStatusEnum.ENDING.value
    // );
    // if (hasUnfinished && autoRefresh.value) {
    if (autoRefresh.value && data?.length) {
      clearRefreshTimer();
      refreshTimer = setTimeout(() => {
        fetchData();
      }, interval);
    } else {
      autoRefresh.value = false;
      clearRefreshTimer();
    }
  };

  // 监听页面可见性变化
  function handleVisibilityChange() {
    if (document.visibilityState === "hidden") {
      clearRefreshTimer();
    } else if (document.visibilityState === "visible" && autoRefresh.value) {
      fetchData();
    }
  }

  onMounted(() => {
    document.addEventListener("visibilitychange", handleVisibilityChange);
  });

  onUnmounted(() => {
    autoRefresh.value = false;
    clearRefreshTimer();
    document.removeEventListener("visibilitychange", handleVisibilityChange);
  });

  // 获取选中的行
  const selectionRows = computed(() => {
    return tableRef.value?.getSelectionRows();
  });

  const clearSelection = () => {
    tableRef.value?.clearSelection();
  };

  // 获取选中行的总行数
  const selectionRowsCount = computed(() => {
    return tableRef.value?.getSelectionRows().length || 0;
  });

  /** 终止计划 */
  async function handleStop(row: any) {
    await superRequest({
      apiFunc: editPlan,
      apiParams: { ...row, run_status: 3, redis_key: true },
      enableSucceedMsg: true,
      succeedMsgContent: "终止成功！",
      onBeforeRequest: () => {
        delLoadings.value[row.id] = true;
      },
      onSucceed: () => {
        fetchData();
      },
      onCompleted: () => {
        delete delLoadings.value[row.id];
      }
    });
  }

  async function handleRestart(row: any) {
    await superRequest({
      apiFunc: restartPlan,
      apiParams: { id: row.id },
      enableSucceedMsg: true,
      succeedMsgContent: "重新执行计划！",
      onBeforeRequest: () => {
        delLoadings.value[row.id] = true;
      },
      onSucceed: () => {
        fetchData();
      },
      onCompleted: () => {
        delete delLoadings.value[row.id];
      }
    });
  }

  async function handleMock(row: any) {
    await superRequest({
      apiFunc: getWebhookPlanMockData,
      apiParams: { id: row.id },
      enableSucceedMsg: false,
      onSucceed: data => {
        showApiMan.value = true;
        apiMethod.value = data?.method;
        apiUrl.value = backendHost() + data.url;
        apiJson.value = JSON.stringify(data.data, null, 2);
        console.log(apiJson.value);
      }
    });
  }

  return {
    dataList,
    dataTotal,
    loading,
    delLoadings,
    copyLoadings,
    selectionRows,
    selectionRowsCount,
    rewardDialogRef,
    showPlanConfirmer,
    workerLabel,
    showApiMan,
    apiMethod,
    apiUrl,
    apiJson,
    autoRefresh,
    getRunTypeTag,
    clearSelection,
    fetchData,
    fetchWorkerNames,
    handleCreate,
    handleReplay,
    handleReport,
    handleRewardReport,
    handleEdit,
    handleEnable,
    handleDelete,
    handleStop,
    handleRestart,
    handleMock
  };
};
