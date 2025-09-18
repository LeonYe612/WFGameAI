import { ref, computed } from "vue";
import {
  listDataSources,
  createDataSource,
  updateDataSource,
  deleteDataSource,
  testDataSourceConnection,
  refreshDataSource,
  getTestData,
  importData,
  exportData,
  performDataAnalysis,
  getAnalysisResults
} from "@/api/data";
import type { DataSource, TestData, DataAnalysis, DataStats } from "@/api/data";
import type { ImportConfig, ExportConfig } from "./types";
import { superRequest } from "@/utils/request";
import { message } from "@/utils/message";

export function useDataManagement() {
  // 响应式数据
  const dataSources = ref<DataSource[]>([]);
  const testData = ref<TestData[]>([]);
  const analysisResults = ref<DataAnalysis[]>([]);
  const loading = ref(false);
  const error = ref("");
  const stats = ref<DataStats>({
    totalSources: 0,
    connectedSources: 0,
    totalRecords: 0,
    recentlyUpdated: 0
  });

  // 当前选中的数据源
  const currentDataSource = ref<DataSource | null>(null);

  // 搜索和筛选
  const searchQuery = ref("");
  const statusFilter = ref("");
  const typeFilter = ref("");

  // 计算统计数据
  const computedStats = computed(() => {
    const total = dataSources.value.length;
    const connected = dataSources.value.filter(
      d => d.status === "connected"
    ).length;
    const totalRecords = dataSources.value.reduce(
      (sum, d) => sum + (d.recordCount || 0),
      0
    );
    const recentlyUpdated = dataSources.value.filter(d => {
      const lastUpdate = new Date(d.lastUpdated);
      const threeDaysAgo = new Date();
      threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);
      return lastUpdate > threeDaysAgo;
    }).length;

    return {
      totalSources: total,
      connectedSources: connected,
      totalRecords,
      recentlyUpdated
    };
  });

  // 过滤后的数据源列表
  const filteredDataSources = computed(() => {
    let filtered = [...dataSources.value];

    // 搜索过滤
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase();
      filtered = filtered.filter(
        source =>
          source.name?.toLowerCase().includes(query) ||
          source.type?.toLowerCase().includes(query) ||
          source.description?.toLowerCase().includes(query)
      );
    }

    // 状态过滤
    if (statusFilter.value) {
      filtered = filtered.filter(
        source => source.status === statusFilter.value
      );
    }

    // 类型过滤
    if (typeFilter.value) {
      filtered = filtered.filter(source => source.type === typeFilter.value);
    }

    return filtered;
  });

  // 获取数据源列表
  const fetchDataSources = async () => {
    await superRequest({
      apiFunc: listDataSources,
      onBeforeRequest: () => {
        loading.value = true;
        error.value = "";
      },
      onSucceed: (data: DataSource[]) => {
        dataSources.value = data;
        stats.value = computedStats.value;
      },
      onFailed: (err: any) => {
        error.value = err.message || "获取数据源列表失败";
        dataSources.value = [];
      },
      onCompleted: () => {
        loading.value = false;
      }
    });
  };

  // 创建数据源
  const createNewDataSource = async (sourceData: Omit<DataSource, "id">) => {
    await superRequest({
      apiFunc: createDataSource,
      apiParams: sourceData,
      enableSucceedMsg: true,
      succeedMsgContent: "数据源创建成功！",
      onSucceed: () => {
        fetchDataSources();
      },
      onFailed: () => {
        message("创建数据源失败", { type: "error" });
      }
    });
  };

  // 更新数据源
  const updateExistingDataSource = async (
    id: string,
    sourceData: Partial<DataSource>
  ) => {
    await superRequest({
      apiFunc: updateDataSource,
      apiParams: [id, sourceData],
      enableSucceedMsg: true,
      succeedMsgContent: "数据源更新成功！",
      onSucceed: () => {
        fetchDataSources();
      },
      onFailed: () => {
        message("更新数据源失败", { type: "error" });
      }
    });
  };

  // 删除数据源
  const removeDataSource = async (id: string) => {
    await superRequest({
      apiFunc: deleteDataSource,
      apiParams: id,
      enableSucceedMsg: true,
      succeedMsgContent: "数据源删除成功！",
      onSucceed: () => {
        fetchDataSources();
      },
      onFailed: () => {
        message("删除数据源失败", { type: "error" });
      }
    });
  };

  // 测试连接
  const testConnection = async (id: string): Promise<boolean> => {
    let result = false;

    await superRequest({
      apiFunc: testDataSourceConnection,
      apiParams: id,
      onSucceed: (data: { success: boolean; message: string }) => {
        result = data.success;
        message(data.message, {
          type: data.success ? "success" : "error"
        });
      },
      onFailed: () => {
        message("连接测试失败", { type: "error" });
      }
    });

    return result;
  };

  // 刷新数据源
  const refreshDataSourceData = async (id: string) => {
    await superRequest({
      apiFunc: refreshDataSource,
      apiParams: id,
      enableSucceedMsg: true,
      succeedMsgContent: "数据源刷新成功！",
      onSucceed: () => {
        fetchDataSources();
      },
      onFailed: () => {
        message("刷新数据源失败", { type: "error" });
      }
    });
  };

  // 获取测试数据
  const fetchTestData = async (dataSourceId: string) => {
    await superRequest({
      apiFunc: getTestData,
      apiParams: dataSourceId,
      onBeforeRequest: () => {
        loading.value = true;
      },
      onSucceed: (data: TestData[]) => {
        testData.value = data;
        currentDataSource.value =
          dataSources.value.find(ds => ds.id === dataSourceId) || null;
      },
      onFailed: (err: any) => {
        error.value = err.message || "获取测试数据失败";
        testData.value = [];
      },
      onCompleted: () => {
        loading.value = false;
      }
    });
  };

  // 导入数据
  const importDataFile = async (config: ImportConfig): Promise<boolean> => {
    let result = false;

    await superRequest({
      apiFunc: importData,
      apiParams: [config.file, config.sourceId],
      enableSucceedMsg: true,
      succeedMsgContent: "数据导入成功！",
      onSucceed: (data: { success: boolean; recordCount: number }) => {
        result = data.success;
        if (data.success) {
          fetchDataSources();
        }
      },
      onFailed: () => {
        message("数据导入失败", { type: "error" });
      }
    });

    return result;
  };

  // 导出数据
  const exportDataFile = async (config: ExportConfig) => {
    await superRequest({
      apiFunc: exportData,
      apiParams: [config.sourceId, config.format],
      onSucceed: (blob: Blob) => {
        // 创建下载链接
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `data_export.${config.format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        message("数据导出成功！", { type: "success" });
      },
      onFailed: () => {
        message("数据导出失败", { type: "error" });
      }
    });
  };

  // 执行数据分析
  const analyzeData = async (sourceId: string, analysisType: string) => {
    await superRequest({
      apiFunc: performDataAnalysis,
      apiParams: [sourceId, analysisType],
      enableSucceedMsg: true,
      succeedMsgContent: "数据分析完成！",
      onSucceed: () => {
        fetchAnalysisResults(sourceId);
      },
      onFailed: () => {
        message("数据分析失败", { type: "error" });
      }
    });
  };

  // 获取分析结果
  const fetchAnalysisResults = async (sourceId: string) => {
    await superRequest({
      apiFunc: getAnalysisResults,
      apiParams: sourceId,
      onSucceed: (data: DataAnalysis[]) => {
        analysisResults.value = data;
      },
      onFailed: (err: any) => {
        error.value = err.message || "获取分析结果失败";
        analysisResults.value = [];
      }
    });
  };

  // 获取状态显示文本
  const getStatusText = (status: string) => {
    const statusMap = {
      connected: "已连接",
      disconnected: "未连接",
      error: "连接失败"
    };
    return statusMap[status] || status;
  };

  // 获取状态标签类型
  const getStatusType = (status: string) => {
    const typeMap = {
      connected: "success",
      disconnected: "info",
      error: "danger"
    };
    return typeMap[status] || "info";
  };

  // 获取类型显示文本
  const getTypeText = (type: string) => {
    const typeMap = {
      excel: "Excel文件",
      csv: "CSV文件",
      database: "数据库",
      json: "JSON文件"
    };
    return typeMap[type] || type;
  };

  return {
    // 响应式数据
    dataSources,
    testData,
    analysisResults,
    loading,
    error,
    stats,
    currentDataSource,
    searchQuery,
    statusFilter,
    typeFilter,

    // 计算属性
    computedStats,
    filteredDataSources,

    // 方法
    fetchDataSources,
    createNewDataSource,
    updateExistingDataSource,
    removeDataSource,
    testConnection,
    refreshDataSourceData,
    fetchTestData,
    importDataFile,
    exportDataFile,
    analyzeData,
    fetchAnalysisResults,
    getStatusText,
    getStatusType,
    getTypeText
  };
}
