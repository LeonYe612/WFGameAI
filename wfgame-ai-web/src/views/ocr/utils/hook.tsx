import { ref } from "vue";
import { ElMessageBox } from "element-plus";
import type {
  OcrRepository,
  OcrTask,
  OcrResult,
  OcrHistoryQuery
} from "@/api/ocr";
import { ocrRepositoryApi, ocrTaskApi } from "@/api/ocr";
import { superRequest } from "@/utils/request";
import { message } from "@/utils/message";

export const useOcr = () => {
  // 数据状态
  const repositories = ref<OcrRepository[]>([]);
  const tasks = ref<OcrTask[]>([]);
  const results = ref<OcrResult[]>([]);

  // ====================================================
  // [Git仓库] 相关方法
  const fetchRepositories = async () => {
    try {
      return await ocrRepositoryApi.list();
    } catch (error) {
      message("获取代码库列表失败", { type: "error" });
      console.error("fetchRepositories error:", error);
    }
  };

  const addRepository = async (
    projectId: string,
    repositoryData: { branch: string; url: string; token?: string }
  ) => {
    try {
      await ocrRepositoryApi.create({
        ...repositoryData
      });
      await fetchRepositories();
    } catch (error) {
      console.error("createRepository error:", error);
    }
  };

  const removeRepository = async (projectId: string, repositoryId: string) => {
    try {
      await ElMessageBox.confirm("确定要删除这个代码库吗？", "确认删除", {
        type: "warning"
      });
      await ocrRepositoryApi.delete(repositoryId);
      await fetchRepositories();
    } catch (error) {
      if (error !== "cancel") {
        console.error("deleteRepository error:", error);
      }
    }
  };

  // ====================================================

  // ====================================================
  // [Task] 相关方法
  const fetchTasks = async (params?: OcrHistoryQuery) => {
    try {
      const res = await superRequest({
        apiFunc: ocrTaskApi.history,
        apiParams: { ...params },
        enableSucceedMsg: false
      });
      return res;
    } catch (error) {
      message("获取任务列表失败", { type: "error" });
      console.error("fetchTasks error:", error);
    }
  };

  // [Task] 删除任务
  const deleteTask = async (taskId: string) => {
    try {
      await superRequest({
        apiFunc: ocrTaskApi.delete,
        apiParams: taskId,
        enableSucceedMsg: true
      });
    } catch (error) {
      message("删除任务失败", { type: "error" });
      console.error("deleteTask error:", error);
    }
  };

  // [Download] 下载任务结果
  const downloadTask = async (taskId: string) => {
    try {
      const response: any = await ocrTaskApi.download(taskId);
      // 兼容 axios/fetch 返回
      const text = response.data;
      const blob = new Blob([text], { type: "text/csv" });
      const disposition = response.headers["content-disposition"];

      // 获取文件名
      let filename = "download.csv";
      if (disposition) {
        const match = disposition.match(/filename=([^;]+)/i);
        if (match) {
          filename = decodeURIComponent(match[1].replace(/['"]/g, ""));
        }
      }
      // 创建下载链接
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || `ocr_results_${taskId}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (error) {
      message("下载任务结果失败", { type: "error" });
      console.error("downloadTask error:", error);
    }
  };

  return {
    // 状态
    repositories,
    tasks,
    results,

    // 代码库管理
    fetchRepositories,
    addRepository,
    removeRepository,

    // 任务管理
    fetchTasks,
    deleteTask,
    downloadTask
  };
};
