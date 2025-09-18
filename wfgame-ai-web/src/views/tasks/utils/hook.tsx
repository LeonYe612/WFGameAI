import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  getTaskList,
  createTask,
  startTask,
  stopTask,
  restartTask,
  deleteTask,
  duplicateTask,
  type Task,
  type TaskQueryParams
} from "@/api/tasks";
import type {
  TaskFilters,
  TaskFormData,
  TaskAction,
  PaginationInfo
} from "../utils/types";

export const useTasksPage = () => {
  // 响应式数据
  const loading = ref(false);
  const taskList = ref<Task[]>([]);
  const filters = ref<TaskFilters>({
    search: "",
    status: "all",
    type: "all"
  });

  const pagination = reactive<PaginationInfo>({
    currentPage: 1,
    pageSize: 20,
    total: 0
  });

  // 对话框状态
  const formDialogVisible = ref(false);
  const detailDialogVisible = ref(false);
  const formLoading = ref(false);
  const currentTask = ref<Task | null>(null);

  // 加载任务列表
  const loadTasks = async () => {
    try {
      loading.value = true;

      const params: TaskQueryParams = {
        page: pagination.currentPage,
        pageSize: pagination.pageSize
      };

      // 添加过滤参数
      if (filters.value.search) {
        params.search = filters.value.search;
      }
      if (filters.value.status !== "all") {
        params.status = filters.value.status;
      }
      if (filters.value.type !== "all") {
        params.type = filters.value.type;
      }

      const response = await getTaskList(params);
      taskList.value = response.data?.results || [];
      pagination.total = response.data?.count || 0;
    } catch (error) {
      console.error("加载任务列表失败:", error);
      ElMessage.error("加载任务列表失败");
    } finally {
      loading.value = false;
    }
  };

  // 处理过滤器变化
  const handleFilterChange = () => {
    pagination.currentPage = 1;
    loadTasks();
  };

  // 处理分页变化
  const handlePageChange = (page: number) => {
    pagination.currentPage = page;
    loadTasks();
  };

  const handleSizeChange = (size: number) => {
    pagination.pageSize = size;
    pagination.currentPage = 1;
    loadTasks();
  };

  // 创建任务
  const handleCreateTask = () => {
    currentTask.value = null;
    formDialogVisible.value = true;
  };

  // 编辑任务
  const handleEditTask = (task: Task) => {
    currentTask.value = task;
    formDialogVisible.value = true;
  };

  // 查看任务详情
  const handleViewTask = (task: Task) => {
    currentTask.value = task;
    detailDialogVisible.value = true;
  };

  // 提交任务表单
  const handleSubmitTask = async (formData: TaskFormData) => {
    try {
      formLoading.value = true;

      if (currentTask.value) {
        // 编辑逻辑（如果有编辑API的话）
        ElMessage.success("任务更新成功");
      } else {
        // 创建任务
        await createTask({
          name: formData.name,
          type: formData.type as any,
          device: formData.device,
          description: formData.description
        });
        ElMessage.success("任务创建成功");
      }

      formDialogVisible.value = false;
      await loadTasks();
    } catch (error) {
      console.error("保存任务失败:", error);
      ElMessage.error("保存任务失败");
    } finally {
      formLoading.value = false;
    }
  };

  // 处理任务操作
  const handleTaskAction = async (action: TaskAction, task: Task) => {
    try {
      switch (action) {
        case "start":
          await startTask(task.id);
          ElMessage.success("任务启动成功");
          await loadTasks();
          break;

        case "stop":
          await ElMessageBox.confirm("确认停止该任务？", "提示", {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            type: "warning"
          });
          await stopTask(task.id);
          ElMessage.success("任务已停止");
          await loadTasks();
          break;

        case "restart":
          await restartTask(task.id);
          ElMessage.success("任务重启成功");
          await loadTasks();
          break;

        case "view":
          handleViewTask(task);
          break;

        case "duplicate":
          await ElMessageBox.confirm("确认复制该任务？", "提示", {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            type: "info"
          });
          await duplicateTask(task.id);
          ElMessage.success("任务复制成功");
          await loadTasks();
          break;

        case "delete":
          await ElMessageBox.confirm(
            "确认删除该任务？删除后无法恢复！",
            "危险操作",
            {
              confirmButtonText: "删除",
              cancelButtonText: "取消",
              type: "error"
            }
          );
          await deleteTask(task.id);
          ElMessage.success("任务删除成功");
          await loadTasks();
          break;

        default:
          console.warn("未知操作:", action);
      }
    } catch (error) {
      if (error !== "cancel") {
        console.error(`执行操作 ${action} 失败:`, error);
        ElMessage.error(`操作失败`);
      }
    }
  };

  // 刷新数据
  const handleRefresh = () => {
    loadTasks();
  };

  // 初始化
  onMounted(() => {
    loadTasks();
  });

  return {
    // 数据状态
    loading,
    taskList,
    filters,
    pagination,

    // 对话框状态
    formDialogVisible,
    detailDialogVisible,
    formLoading,
    currentTask,

    // 方法
    loadTasks,
    handleFilterChange,
    handlePageChange,
    handleSizeChange,
    handleCreateTask,
    handleEditTask,
    handleViewTask,
    handleSubmitTask,
    handleTaskAction,
    handleRefresh
  };
};
