import {
    createTask,
    deleteTask,
    duplicateTask,
    getTaskList,
    restartTask,
    startTask,
    stopTask,
    type Task,
    type TaskQueryParams
} from "@/api/tasks";
import { superRequest } from "@/utils/request";
import { ElMessage, ElMessageBox } from "element-plus";
import { onMounted, reactive, ref } from "vue";
// import { useRouter } from "vue-router";
import { useNavigate } from "@/views/common/utils/navHook";
import type {
    CreateTaskPayload,
    PaginationInfo,
    TaskAction,
    TaskFilters
} from "../utils/types";

export const useTasksPage = () => {
    const { openReplayRoom } = useNavigate();
    const loading = ref(false);
    const taskList = ref<Task[]>([]);
    const filters = ref<TaskFilters>({
        search: "",
        status: null,
        type: null
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
        loading.value = true;

        const params: TaskQueryParams = {
            page: pagination.currentPage,
            pageSize: pagination.pageSize
        };

        // 添加过滤参数（仅在不为 null 时添加）
        if (filters.value.search) {
            params.search = filters.value.search;
        }
        if (filters.value.status !== null && filters.value.status !== undefined) {
            params.status = filters.value.status as any;
        }
        if (filters.value.type !== null && filters.value.type !== undefined) {
            params.type = filters.value.type as any;
        }

        await superRequest({
            apiFunc: getTaskList,
            apiParams: params,
            onSucceed: data => {
                taskList.value = data?.results;
                pagination.total = data?.count || 0;
            },
            onCompleted: () => {
                loading.value = false;
            }
        });
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
    const handleSubmitTask = async (formData: CreateTaskPayload) => {
        formLoading.value = true;

        if (currentTask.value) {
            // 编辑逻辑（如果有编辑API的话）
            // 可根据实际编辑API返回值处理
        } else {
            // 创建任务：直接把 TaskFormData 的字段作为顶层参数发送
            await superRequest({
                apiFunc: createTask,
                apiParams: formData as any,
                enableSucceedMsg: true,
                succeedMsgContent: "创建任务成功！",
                onCompleted: () => {
                    formLoading.value = false;
                    loadTasks();
                }
            });
        }
    };

    // 处理任务操作
    const handleTaskAction = async (action: TaskAction, task: Task) => {
        try {
            switch (action) {
                case "start": {
                    await superRequest({
                        apiFunc: startTask,
                        apiParams: task.id,
                        enableSucceedMsg: true,
                        succeedMsgContent: "任务开始执行",
                        onSucceed: (data: any) => {
                            const taskId = String(task.id);
                            const deviceIds = (task as any).device_ids || [];
                            const scriptIds = (task as any).script_ids || [];
                            const celeryId =
                                data?.celery_task_id || (task as any).celery_id || "";

                            // 打开回放页面（封装复用）
                            openReplayRoom({
                                taskId,
                                deviceIds,
                                scriptIds,
                                celeryId,
                                newTab: true
                            });
                        },
                        onCompleted: () => {
                            loadTasks();
                        }
                    });
                    break;
                }

                case "stop":
                    await ElMessageBox.confirm("确认停止该任务？", "提示", {
                        confirmButtonText: "确定",
                        cancelButtonText: "取消",
                        type: "warning"
                    });
                    await stopTask(task.id);
                    await loadTasks();
                    break;

                case "restart":
                    await restartTask(task.id);
                    await loadTasks();
                    break;

                case "view":
                    handleViewTask(task);
                    break;

                case "duplicate": {
                    // 弹出输入框，允许用户确认并修改副本名称
                    const defaultName = `${task.name || "任务"}_cp_${task.id}`;
                    const { value } = await ElMessageBox.prompt(
                        "请输入副本名称",
                        "复制任务",
                        {
                            confirmButtonText: "复制",
                            cancelButtonText: "取消",
                            inputValue: defaultName,
                            inputValidator: (val: string) => {
                                if (!val || !val.trim()) return "名称不能为空";
                                if (val.length > 50) return "名称长度不能超过50个字符";
                                return true;
                            }
                        }
                    );
                    await superRequest({
                        apiFunc: (id: number) => duplicateTask(id, { name: value }),
                        apiParams: task.id,
                        enableSucceedMsg: true,
                        succeedMsgContent: "复制任务成功！",
                        onCompleted: () => {
                            loadTasks();
                        }
                    });
                    break;
                }

                case "delete":
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
