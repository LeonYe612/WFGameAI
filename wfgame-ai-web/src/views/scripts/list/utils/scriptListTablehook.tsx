import { scriptApi } from "@/api/scripts";
import { superRequest } from "@/utils/request";
import { ref, computed } from "vue";
import { useNavigate } from "@/views/common/utils/navHook";
import { useScriptStore } from "@/store/modules/script";
import { message } from "@/utils/message";
import { ElMessageBox } from "element-plus";

export const useScriptListTable = (props?: any) => {
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
    navigateToScriptDetail,
    // navigateToReportDetail,
    navigateToDebugReportList,
    navigateToTasksPage
  } = useNavigate();

  const _scriptStore = useScriptStore();

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
    navigateToScriptDetail();
  };

  /** 调试用例 */
  const handleDebug = _row => {};

  /** 执行脚本 */
  const handleExecute = async (_row, run_type: number) => {
    const queryParams = {
      script_ids: [_row.id],
      task_type: 1, // 回放类型 - todo: 定义枚举
      run_type: run_type // 调试类型 - todo: 定义枚举
    };
    navigateToTasksPage(queryParams);
    return;
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
    navigateToScriptDetail(row.id);
  };

  /** 拷贝用例 */
  const handleCopy = async (row: any) => {
    await superRequest({
      apiFunc: scriptApi.copy,
      apiParams: { copy_id: row.id },
      enableSucceedMsg: true,
      succeedMsgContent: "拷贝成功！",
      onBeforeRequest: () => {
        copyLoadings.value[row.id] = true;
      },
      onSucceed: data => {
        // 刷新列表显示
        fetchData();
        // 跳转编辑页面
        navigateToScriptDetail(data.id);
      },
      onCompleted: () => {
        delete copyLoadings.value[row.id];
      }
    });
  };

  /** 删除用例 */
  async function handleDelete(row: any) {
    await superRequest({
      apiFunc: scriptApi.delete,
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

  /** 二次确认后-删除用例 */
  async function handleConfirmDelete(row: any) {
    ElMessageBox.confirm(
      `确定删除脚本【ID:${row.id}】吗？<span style="color: red;">🚨删除后不可恢复</span>`,
      "删除脚本",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
        dangerouslyUseHTMLString: true
      }
    )
      .then(() => {
        handleDelete(row);
      })
      .catch(() => {});
  }

  const fetchData = async () => {
    await superRequest({
      apiFunc: scriptApi.list,
      apiParams: props.queryForm,
      enableSucceedMsg: false,
      onBeforeRequest: () => {
        loading.value = true;
      },
      onSucceed: data => {
        dataList.value = data?.items;
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

  // 行点击事件，切换选中状态
  const handleToggleRowSelection = row => {
    tableRef.value?.toggleRowSelection(row);
  };

  const clearSelection = () => {
    tableRef.value?.clearSelection();
  };

  // 获取选中行的总行数
  const selectionRowsCount = computed(() => {
    return tableRef.value?.getSelectionRows().length || 0;
  });

  const handleBatchDelete = async () => {
    // 构造参数
    const ids = selectionRows.value.map(item => item.id);
    ElMessageBox.confirm(
      `确定删除选中的 <strong style="color: red;">${ids.length}</strong> 个脚本吗？<span style="color: red;">🚨删除后不可恢复</span>`,
      "批量删除脚本",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
        dangerouslyUseHTMLString: true
      }
    )
      .then(async () => {
        await superRequest({
          apiFunc: scriptApi.batchDelete,
          apiParams: { ids },
          enableSucceedMsg: true,
          succeedMsgContent: "批量删除成功！",
          onBeforeRequest: () => {
            delLoading.value = true;
          },
          onSucceed: () => {
            fetchData();
            clearSelection();
          },
          onCompleted: () => {
            delLoading.value = false;
          }
        });
      })
      .catch(() => {});
  };

  const handleBatchCopy = async (data: {
    targetTeamId: number;
    targetCategoryId: number;
  }) => {
    // 构造参数
    const ids = selectionRows.value.map(item => item.id);
    await superRequest({
      apiFunc: scriptApi.copy,
      apiParams: {
        script_ids: ids,
        target_team_id: data.targetTeamId,
        target_category_id: data.targetCategoryId
      },
      enableSucceedMsg: true
    });
    fetchData();
    clearSelection();
  };

  const handleSwitchLog = async row => {
    await superRequest({
      apiFunc: () =>
        scriptApi.update({
          id: row.id,
          include_in_log: row.include_in_log
        } as any)
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
    handleConfirmDelete,
    handleBatchDelete,
    handleBatchCopy,
    handleSwitchLog,
    handleToggleRowSelection
  };
};
