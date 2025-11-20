import { ref, onMounted, reactive } from "vue";
import { ElMessage } from "element-plus";
import { listReports, type ReportItem } from "@/api/reports";
import type { ReportQueryParams } from "./types";
import { superRequest } from "@/utils/request";

export const useReportsTable = (_tableRef: any) => {
  // 响应式数据
  const loading = ref(false);
  const dataList = ref<ReportItem[]>([]);
  const dataTotal = ref(0);

  // 查询参数
  const queryForm = reactive({
    page: 1,
    size: 20,
    keyword: "",
    status: ""
  });

  // 加载报告列表
  const fetchData = async () => {
    try {
      loading.value = true;

      const params: ReportQueryParams = {
        page: queryForm.page,
        size: queryForm.size
      };

      // 添加过滤参数
      if (queryForm.keyword) {
        params.keyword = queryForm.keyword;
      }
      if (queryForm.status) {
        params.status = queryForm.status;
      }

      await superRequest({
        apiFunc: listReports,
        apiParams: params,
        onSucceed: (data: any) => {
          dataList.value = data?.items || [];
          dataTotal.value = data?.total || 0;
        }
      });
    } catch (error) {
      console.error("加载报告列表失败:", error);
      ElMessage.error("加载报告列表失败");
      dataList.value = [];
      dataTotal.value = 0;
    } finally {
      loading.value = false;
    }
  };

  // 重置查询表单
  const handleResetQuery = () => {
    queryForm.page = 1;
    queryForm.size = 20;
    queryForm.keyword = "";
    queryForm.status = "";
    fetchData();
  };

  // 初始化
  onMounted(() => {
    fetchData();
  });

  return {
    // 数据状态
    loading,
    dataList,
    dataTotal,
    queryForm,

    // 方法
    fetchData,
    handleResetQuery
  };
};
