import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  getReportsList,
  deleteReport,
  type Report,
  type ReportQueryParams
} from "@/api/reports";
import type {
  ReportFilters,
  ReportAction,
  ReportWithSuccessRate
} from "../utils/types";
import { calculateSuccessRate } from "../utils/rules";

export const useReportsPage = () => {
  // 响应式数据
  const loading = ref(false);
  const reportList = ref<ReportWithSuccessRate[]>([]);
  const filters = ref<ReportFilters>({
    search: "",
    successRate: "all",
    date: ""
  });

  // 加载报告列表
  const loadReports = async () => {
    try {
      loading.value = true;

      const params: ReportQueryParams = {};

      // 添加过滤参数
      if (filters.value.search) {
        params.search = filters.value.search;
      }
      if (filters.value.successRate !== "all") {
        params.success_rate = filters.value.successRate;
      }
      if (filters.value.date) {
        params.date = filters.value.date;
      }

      const response = await getReportsList(params);

      // 处理报告数据，添加计算的成功率
      const reportsWithRate = (response.data?.reports || []).map(report => {
        const deviceCount = report.devices ? report.devices.length : 0;
        const successRate = calculateSuccessRate(
          report.success_count,
          deviceCount
        );

        return {
          ...report,
          successRate,
          deviceCount
        };
      });

      reportList.value = reportsWithRate;
    } catch (error) {
      console.error("加载报告列表失败:", error);
      ElMessage.error("加载报告列表失败");
      reportList.value = [];
    } finally {
      loading.value = false;
    }
  };

  // 处理过滤器变化
  const handleFilterChange = () => {
    loadReports();
  };

  // 处理报告操作
  const handleReportAction = async (action: ReportAction, report: Report) => {
    try {
      switch (action) {
        case "view":
          // 在新窗口打开报告
          window.open(report.url, "_blank");
          break;

        case "delete":
          await ElMessageBox.confirm(
            "确认删除该报告？删除后无法恢复！",
            "危险操作",
            {
              confirmButtonText: "删除",
              cancelButtonText: "取消",
              type: "error"
            }
          );

          await deleteReport({ id: report.id });
          ElMessage.success("报告删除成功");
          await loadReports();
          break;

        default:
          console.warn("未知操作:", action);
      }
    } catch (error) {
      if (error !== "cancel") {
        console.error(`执行操作 ${action} 失败:`, error);
        ElMessage.error("操作失败");
      }
    }
  };

  // 刷新数据
  const handleRefresh = () => {
    loadReports();
  };

  // 创建新测试
  const handleCreateTest = () => {
    window.location.href = "/automation/";
  };

  // 初始化
  onMounted(() => {
    loadReports();
  });

  return {
    // 数据状态
    loading,
    reportList,
    filters,

    // 方法
    loadReports,
    handleFilterChange,
    handleReportAction,
    handleRefresh,
    handleCreateTest
  };
};
