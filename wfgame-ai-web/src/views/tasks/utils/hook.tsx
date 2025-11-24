import { listReports } from "@/api/reports";
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
import { preconnectReplayTask } from "@/views/replay/utils/socket";
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
    const restartLoadingMap = ref<Record<number, boolean>>({}); // 任务级重启 loading
    const restartLoadingTimers = ref<Record<number, number>>({}); // 任务级重启 loading 超时兜底
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
            onSucceed: async data => {
                taskList.value = data?.results;
                pagination.total = data?.count || 0;
                try {
                    await enrichReportIds(taskList.value || []);
                } catch (e) {
                    console.warn("附加报告ID失败", e);
                }
            },
            onCompleted: () => {
                loading.value = false;
            }
        });
    };

    /** 为已结束的任务补充 report_id（若后端未直接返回） */
    const enrichReportIds = async (tasks: Task[]) => {
        if (!Array.isArray(tasks) || tasks.length === 0) return;
        const endedStatuses = new Set([
            "completed",
            "failed",
            "cancelled",
            "finished",
            "success"
        ]);
        const candidates = tasks.filter(
            (t: any) =>
                !t.report_id && endedStatuses.has(String(t.status)) && t.id
        );
        if (candidates.length === 0) return;
        // 并发获取每个任务的最新报告，限制单个结果 size=1
        await Promise.all(
            candidates.map(async task => {
                try {
                    const resp = await superRequest({
                        apiFunc: listReports,
                        apiParams: { task_id: task.id, size: 1, page: 1 },
                        enableFailedMsg: false,
                        enableErrorMsg: false
                    });
                    const payload = resp?.data || {};
                    const items = payload.items || payload.results || [];
                    const first = Array.isArray(items) ? items[0] : null;
                    if (first && first.id) {
                        (task as any).report_id = first.id;
                    }
                } catch (e) {
                    // 忽略单个失败
                }
            })
        );
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
                    // 启动任务：先建立WS连接监听早期事件，再调用start接口，最后打开窗口并传递捕获的离线设备
                    const taskId = String(task.id);
                    const deviceIds = (task as any).device_ids || [];
                    const scriptIds = (task as any).script_ids || [];

                    // 1. 尝试预连接 WS (容错处理)
                    const capturedOffline = new Set<string>();
                    let socket: any = null;
                    try {
                        // 清理旧的离线记录
                        localStorage.removeItem(`replay_offline_${taskId}`);

                        socket = preconnectReplayTask(taskId, {
                            onError: (err: any) => {
                                try {
                                    // 后端 emit event="error" data={ device, reason: "device_not_connected", ... }
                                    const data = (err && err.data) ? err.data : err;
                                    const device = data?.device;
                                    const reason = data?.reason;

                                    if (device && reason === 'device_not_connected') {
                                        capturedOffline.add(device);
                                        // 写入 LocalStorage 以便新窗口读取
                                        const key = `replay_offline_${taskId}`;
                                        const existing = JSON.parse(localStorage.getItem(key) || '[]');
                                        if (!existing.includes(device)) {
                                            existing.push(device);
                                            localStorage.setItem(key, JSON.stringify(existing));
                                        }
                                    }
                                } catch (e) { /* ignore callback error */ }
                            }
                        });
                    } catch (e) {
                        console.error("Preconnect failed", e);
                    }

                    // 2. 调用 Start 接口
                    await superRequest({
                        apiFunc: startTask,
                        apiParams: task.id,
                        enableSucceedMsg: true,
                        succeedMsgContent: "任务开始执行",
                        onSucceed: (data: any) => {
                            const celeryId = data?.celery_task_id || (task as any).celery_id || "";
                            // 3. 打开窗口，传递捕获的离线设备
                            const extraQuery: any = {};
                            if (capturedOffline.size > 0) {
                                extraQuery.initial_offline = Array.from(capturedOffline).join(',');
                            }
                            openReplayRoom({
                                taskId,
                                deviceIds,
                                scriptIds,
                                celeryId,
                                blank: true,
                                extraQuery: Object.keys(extraQuery).length > 0 ? extraQuery : undefined
                            });
                        },
                        onCompleted: () => {
                            // 延迟断开预连接，确保新窗口有时间加载或事件已传递
                            if (socket) {
                                setTimeout(() => {
                                    try { socket.disconnect(); } catch (_) { /* ignore */ }
                                }, 5000);
                            }
                            loadTasks();
                        }
                    });
                    break;
                } case "stop":
                    await ElMessageBox.confirm("确认停止该任务？", "提示", {
                        confirmButtonText: "确定",
                        cancelButtonText: "取消",
                        type: "warning"
                    });
                    await stopTask(task.id);
                    await loadTasks();
                    break;

                case "restart": {
                    await ElMessageBox.confirm("确认重启该任务？将生成新的执行记录。", "重启任务", {
                        confirmButtonText: "重启",
                        cancelButtonText: "取消",
                        type: "warning"
                    });
                    restartLoadingMap.value[task.id] = true;

                    // 1. 尝试预连接 WS (容错处理)
                    const capturedOffline = new Set<string>();
                    let socket: any = null;
                    try {
                        // 清理旧的离线记录
                        localStorage.removeItem(`replay_offline_${task.id}`);

                        socket = preconnectReplayTask(task.id, {
                            onError: (err: any) => {
                                try {
                                    // 后端 emit event="error" data={ device, reason: "device_not_connected", ... }
                                    const data = (err && err.data) ? err.data : err;
                                    const device = data?.device;
                                    const reason = data?.reason;

                                    if (device && reason === 'device_not_connected') {
                                        capturedOffline.add(device);
                                        // 写入 LocalStorage 以便新窗口读取
                                        const key = `replay_offline_${task.id}`;
                                        const existing = JSON.parse(localStorage.getItem(key) || '[]');
                                        if (!existing.includes(device)) {
                                            existing.push(device);
                                            localStorage.setItem(key, JSON.stringify(existing));
                                        }
                                    }
                                } catch (e) { /* ignore callback error */ }
                            }
                        });
                    } catch (e) {
                        console.error("Preconnect failed", e);
                    }

                    // 兜底超时：10s 后无论成功/失败都解除 loading，防止 Celery 未启动导致前端卡死
                    if (restartLoadingTimers.value[task.id]) {
                        clearTimeout(restartLoadingTimers.value[task.id]);
                    }
                    restartLoadingTimers.value[task.id] = window.setTimeout(() => {
                        restartLoadingMap.value[task.id] = false;
                        delete restartLoadingTimers.value[task.id];
                        if (socket) {
                            try { socket.disconnect(); } catch (_) { /* ignore */ }
                        }
                    }, 10000);

                    await superRequest({
                        apiFunc: (id: string) => restartTask(id),
                        apiParams: task.id,
                        enableSucceedMsg: true,
                        succeedMsgContent: "任务重启成功！",
                        onSucceed: (data: any) => {
                            const taskId = task.id;
                            const deviceIds = (task as any).device_ids || [];
                            const scriptIds = (task as any).script_ids || [];
                            const celeryId = data?.celery_task_id || (task as any).celery_id || "";

                            const extraQuery: any = {};
                            if (capturedOffline.size > 0) {
                                extraQuery.initial_offline = Array.from(capturedOffline).join(',');
                            }
                            openReplayRoom({
                                taskId,
                                deviceIds,
                                scriptIds,
                                celeryId,
                                blank: true,
                                extraQuery: Object.keys(extraQuery).length > 0 ? extraQuery : undefined
                            });
                        },
                        onFailed: () => {
                            // 若无可用 celery worker 或失败，直接去掉 loading
                            restartLoadingMap.value[task.id] = false;
                            if (restartLoadingTimers.value[task.id]) {
                                clearTimeout(restartLoadingTimers.value[task.id]);
                                delete restartLoadingTimers.value[task.id];
                            }
                            if (socket) {
                                try { socket.disconnect(); } catch (_) { /* ignore */ }
                            }
                        },
                        onCompleted: () => {
                            restartLoadingMap.value[task.id] = false;
                            if (restartLoadingTimers.value[task.id]) {
                                clearTimeout(restartLoadingTimers.value[task.id]);
                                delete restartLoadingTimers.value[task.id];
                            }
                            if (socket) {
                                setTimeout(() => {
                                    try { socket.disconnect(); } catch (_) { /* ignore */ }
                                }, 5000);
                            }
                            loadTasks();
                        }
                    });
                    break;
                }

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
        restartLoadingMap,

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
