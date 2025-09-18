import { delCase, listCase, copyCase, exportCases } from "@/api/testcase";
import { formatBackendUrl } from "@/api/utils";
import { superRequest } from "@/utils/request";
import { ref, computed } from "vue";
import { useNavigate } from "@/views/common/utils/navHook";
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { message } from "@/utils/message";
import { envEnum } from "@/utils/enums";

export const useCaseListTable = (props?: any) => {
  const tableRef = props.tableRef;
  const dataList = ref([]);
  const dataTotal = ref(0);
  const loading = ref(false);
  const delLoadings = ref({});
  const delLoading = ref(false);
  const copyLoadings = ref({});
  const executeLoadings = ref({});
  const exportLoading = ref(false);

  const {
    navigateToTestcaseDetail,
    // navigateToReportDetail,
    navigateToDebugReportList
  } = useNavigate();
  const testcaseStore = useTestcaseStoreHook();

  // 用例目录 Path 显示
  const catalogPath = ref([]);
  const setCatalogPath = (path: any[]) => {
    catalogPath.value = path;
  };
  const getCatalogPath = computed(() => {
    if (!catalogPath.value || catalogPath.value.length === 0) {
      return "全部";
    } else {
      return "全部 / " + catalogPath.value.map(item => item.name).join(" / ");
    }
  });

  /** 新增用例 */
  const handleCreate = () => {
    navigateToTestcaseDetail();
  };

  /** 调试用例 */
  const handleDebug = row => {
    testcaseStore.baseInfo.id = row.id;
    testcaseStore.baseInfo.version = row.version;
    testcaseStore.fetchBaseInfo();
    testcaseStore.components.showDebugConfirmer = true;
  };

  /** 执行用例 */
  const handleExecute = async row => {
    console.log(row);
    testcaseStore.SET_BASE_INFO(row);
    testcaseStore.components.showPlanConfirmer = true;
  };
  /** 查看用例报告 */
  const handleReport = row => {
    const keywords = `${row.name} (第${row.version}版)`;
    try {
      navigateToDebugReportList(keywords);
    } catch {
      message("请联系管理员分配【报告列表】查看权限！", {
        type: "warning"
      });
    }
  };

  /** 编辑用例 */
  const handleEdit = row => {
    try {
      navigateToTestcaseDetail(row.id, row.version);
    } catch {
      message("请联系管理员分配【用例详情】相关权限！", {
        type: "warning"
      });
    }
  };

  /** 拷贝用例 */
  const handleCopy = async (row: any) => {
    await superRequest({
      apiFunc: copyCase,
      apiParams: { id: row.id },
      enableSucceedMsg: true,
      succeedMsgContent: "拷贝成功！",
      onBeforeRequest: () => {
        copyLoadings.value[row.id] = true;
      },
      onSucceed: data => {
        // 刷新列表显示
        fetchData();
        // 跳转编辑页面
        const newCaseId = data.id;
        navigateToTestcaseDetail(newCaseId, 1);
      },
      onCompleted: () => {
        delete copyLoadings.value[row.id];
      }
    });
  };

  /** 拷贝用例 */
  const handleExport = async () => {
    // 构造参数
    const cases = selectionRows.value.map(item => {
      return {
        case_base_id: item.id,
        version: item.version,
        name: item.name
      };
    });
    await superRequest({
      apiFunc: exportCases,
      apiParams: {
        env: envEnum.TEST,
        cases: cases
      },
      enableSucceedMsg: false,
      onBeforeRequest: () => {
        exportLoading.value = true;
      },
      onSucceed: data => {
        // 打开返回的下载链接，直接下载 url
        window.open(formatBackendUrl(data), "_blank");
      },
      onCompleted: () => {
        exportLoading.value = false;
      }
    });
  };

  /** 删除用例 */
  async function handleDelete(row: any) {
    await superRequest({
      apiFunc: delCase,
      apiParams: { ids_array: [row.id] },
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

  const fetchData = async () => {
    await superRequest({
      apiFunc: listCase,
      apiParams: props.queryForm,
      enableSucceedMsg: false,
      onBeforeRequest: () => {
        loading.value = true;
      },
      onSucceed: data => {
        dataList.value = data?.list;
        dataTotal.value = data?.total;
      },
      onCompleted: () => {
        loading.value = false;
      }
    });
  };

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

  const handleDeleteAll = async () => {
    // 构造参数
    const casesIds = selectionRows.value.map(item => item.id);
    await superRequest({
      apiFunc: delCase,
      apiParams: {
        ids_array: casesIds
      },
      enableSucceedMsg: true,
      succeedMsgContent: "删除成功！",
      onBeforeRequest: () => {
        delLoading.value = true;
      },
      onSucceed: () => {
        delLoading.value = false;
        clearSelection();
        fetchData();
      },
      onCompleted: () => {
        delLoading.value = false;
        clearSelection();
      }
    });
  };

  return {
    dataList,
    dataTotal,
    loading,
    delLoadings,
    delLoading,
    copyLoadings,
    executeLoadings,
    exportLoading,
    catalogPath,
    selectionRows,
    selectionRowsCount,
    setCatalogPath,
    getCatalogPath,
    clearSelection,
    fetchData,
    handleCreate,
    handleDebug,
    handleExecute,
    handleReport,
    handleEdit,
    handleCopy,
    handleDelete,
    handleExport,
    handleDeleteAll
  };
};
