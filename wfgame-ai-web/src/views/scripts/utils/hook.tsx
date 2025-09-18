import { ref, computed } from "vue";
import {
  listScripts,
  getScriptCategories,
  executeDebugCommand,
  replayScripts,
  getScriptContent,
  saveScriptContent,
  importScript,
  batchImportScripts,
  copyScript,
  deleteScript,
  updateScriptLogStatus
} from "@/api/scripts";
import type {
  ScriptInfo,
  ScriptStats,
  ScriptCategory,
  ScriptSettings,
  ReplayRequest
} from "@/api/scripts";
import { superRequest } from "@/utils/request";
import { message } from "@/utils/message";

export function useScriptsManagement() {
  // 响应式数据
  const scripts = ref<ScriptInfo[]>([]);
  const categories = ref<ScriptCategory[]>([]);
  const loading = ref(false);
  const error = ref("");
  const stats = ref<ScriptStats>({
    total: 0,
    included_in_log: 0,
    excluded_from_log: 0,
    categories: {}
  });

  // 搜索和筛选
  const searchQuery = ref("");
  const categoryFilter = ref("");
  const typeFilter = ref("");
  const includeInLogFilter = ref("");
  const viewMode = ref("table");

  // 排序
  const sortField = ref("filename");
  const sortDirection = ref("asc");

  // 脚本设置
  const settings = ref<ScriptSettings>({
    python_path: "python",
    debug_cmd: "record_script.py",
    record_cmd: "record_script.py --record",
    replay_cmd: "replay_script.py --show-screens"
  });

  // 计算统计数据
  const computedStats = computed(() => {
    const total = scripts.value.length;
    const included_in_log = scripts.value.filter(s => s.include_in_log).length;
    const excluded_from_log = total - included_in_log;
    const categories = {};

    scripts.value.forEach(script => {
      if (script.category) {
        categories[script.category] = (categories[script.category] || 0) + 1;
      }
    });

    return { total, included_in_log, excluded_from_log, categories };
  });

  // 过滤和排序的脚本列表
  const filteredAndSortedScripts = computed(() => {
    let filtered = [...scripts.value];

    // 搜索过滤
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase();
      filtered = filtered.filter(
        script =>
          script.filename?.toLowerCase().includes(query) ||
          script.category?.toLowerCase().includes(query) ||
          script.description?.toLowerCase().includes(query)
      );
    }

    // 分类过滤
    if (categoryFilter.value) {
      filtered = filtered.filter(
        script => script.category === categoryFilter.value
      );
    }

    // 类型过滤
    if (typeFilter.value) {
      filtered = filtered.filter(
        script => script.script_type === typeFilter.value
      );
    }

    // 日志包含状态过滤
    if (includeInLogFilter.value !== "") {
      const includeInLog = includeInLogFilter.value === "true";
      filtered = filtered.filter(
        script => script.include_in_log === includeInLog
      );
    }

    // 排序
    if (sortField.value) {
      filtered = filtered.sort((a, b) => {
        const aVal = a[sortField.value] || "";
        const bVal = b[sortField.value] || "";
        const result = aVal.toString().localeCompare(bVal.toString());
        return sortDirection.value === "asc" ? result : -result;
      });
    }

    return filtered;
  });

  // 获取脚本列表
  const fetchScripts = async () => {
    await superRequest({
      apiFunc: listScripts,
      onBeforeRequest: () => {
        loading.value = true;
        error.value = "";
      },
      onSucceed: (data: ScriptInfo[]) => {
        scripts.value = data;
        // 更新统计数据
        stats.value = computedStats.value;
      },
      onFailed: (err: any) => {
        error.value = err.message || "获取脚本列表失败";
        scripts.value = [];
      },
      onCompleted: () => {
        loading.value = false;
      }
    });
  };

  // 获取脚本分类
  const fetchCategories = async () => {
    await superRequest({
      apiFunc: getScriptCategories,
      onSucceed: (data: ScriptCategory[]) => {
        categories.value = data;
      },
      onFailed: (err: any) => {
        console.error("获取脚本分类失败:", err);
      }
    });
  };

  // 执行调试命令
  const executeDebug = async () => {
    const command = `${settings.value.python_path} ${settings.value.debug_cmd}`;

    await superRequest({
      apiFunc: executeDebugCommand,
      apiParams: command,
      enableSucceedMsg: true,
      succeedMsgContent: "调试命令执行成功！",
      onFailed: () => {
        message("调试命令执行失败", { type: "error" });
      }
    });
  };

  // 执行录制命令
  const executeRecord = async () => {
    const command = `${settings.value.python_path} ${settings.value.record_cmd}`;

    await superRequest({
      apiFunc: executeDebugCommand,
      apiParams: command,
      enableSucceedMsg: true,
      succeedMsgContent: "录制命令执行成功！",
      onFailed: () => {
        message("录制命令执行失败", { type: "error" });
      }
    });
  };

  // 回放脚本
  const performReplay = async (replayData: ReplayRequest) => {
    await superRequest({
      apiFunc: replayScripts,
      apiParams: replayData,
      enableSucceedMsg: true,
      succeedMsgContent: "脚本回放开始执行！",
      onFailed: () => {
        message("脚本回放失败", { type: "error" });
      }
    });
  };

  // 获取脚本内容
  const getScript = async (filename: string): Promise<ScriptInfo | null> => {
    let result: ScriptInfo | null = null;

    await superRequest({
      apiFunc: getScriptContent,
      apiParams: filename,
      onSucceed: (data: ScriptInfo) => {
        result = data;
      },
      onFailed: () => {
        message("获取脚本内容失败", { type: "error" });
      }
    });

    return result;
  };

  // 保存脚本内容
  const saveScript = async (filename: string, content: string) => {
    await superRequest({
      apiFunc: saveScriptContent,
      apiParams: [filename, content],
      enableSucceedMsg: true,
      succeedMsgContent: "脚本保存成功！",
      onSucceed: () => {
        // 重新获取脚本列表
        fetchScripts();
      },
      onFailed: () => {
        message("脚本保存失败", { type: "error" });
      }
    });
  };

  // 创建新脚本
  const createScript = async (filename: string, content: string) => {
    await superRequest({
      apiFunc: saveScriptContent,
      apiParams: [filename, content],
      enableSucceedMsg: true,
      succeedMsgContent: "脚本创建成功！",
      onSucceed: () => {
        // 重新获取脚本列表
        fetchScripts();
      },
      onFailed: () => {
        message("脚本创建失败", { type: "error" });
      }
    });
  };

  // 导入单个脚本
  const importSingleScript = async (formData: FormData) => {
    await superRequest({
      apiFunc: importScript,
      apiParams: formData,
      enableSucceedMsg: true,
      succeedMsgContent: "脚本导入成功！",
      onSucceed: () => {
        // 重新获取脚本列表
        fetchScripts();
      },
      onFailed: () => {
        message("脚本导入失败", { type: "error" });
      }
    });
  };

  // 批量导入脚本
  const importBatchScripts = async (formData: FormData) => {
    await superRequest({
      apiFunc: batchImportScripts,
      apiParams: formData,
      enableSucceedMsg: true,
      succeedMsgContent: "批量导入完成！",
      onSucceed: () => {
        // 重新获取脚本列表
        fetchScripts();
      },
      onFailed: () => {
        message("批量导入失败", { type: "error" });
      }
    });
  };

  // 复制脚本
  const duplicateScript = async (filename: string, newName: string) => {
    await superRequest({
      apiFunc: copyScript,
      apiParams: [filename, newName],
      enableSucceedMsg: true,
      succeedMsgContent: "脚本复制成功！",
      onSucceed: () => {
        // 重新获取脚本列表
        fetchScripts();
      },
      onFailed: () => {
        message("脚本复制失败", { type: "error" });
      }
    });
  };

  // 删除脚本
  const removeScript = async (filename: string) => {
    await superRequest({
      apiFunc: deleteScript,
      apiParams: filename,
      enableSucceedMsg: true,
      succeedMsgContent: "脚本删除成功！",
      onSucceed: () => {
        // 重新获取脚本列表
        fetchScripts();
      },
      onFailed: () => {
        message("脚本删除失败", { type: "error" });
      }
    });
  };

  // 切换脚本日志状态
  const toggleScriptLogStatus = async (
    filename: string,
    includeInLog: boolean
  ) => {
    await superRequest({
      apiFunc: updateScriptLogStatus,
      apiParams: [filename, includeInLog],
      enableSucceedMsg: true,
      succeedMsgContent: `脚本${includeInLog ? "已加入" : "已移出"}日志！`,
      onSucceed: () => {
        // 更新本地状态
        const script = scripts.value.find(s => s.filename === filename);
        if (script) {
          script.include_in_log = includeInLog;
        }
        // 更新统计数据
        stats.value = computedStats.value;
      },
      onFailed: () => {
        message("更新脚本日志状态失败", { type: "error" });
      }
    });
  };

  // 排序处理
  const sortBy = (field: string) => {
    if (sortField.value === field) {
      sortDirection.value = sortDirection.value === "asc" ? "desc" : "asc";
    } else {
      sortField.value = field;
      sortDirection.value = "asc";
    }
  };

  // 加载设置
  const loadSettings = () => {
    try {
      const stored = localStorage.getItem("scriptSettings");
      if (stored) {
        const parsed = JSON.parse(stored);
        settings.value = { ...settings.value, ...parsed };
      }
    } catch (error) {
      console.error("加载设置失败:", error);
    }
  };

  // 保存设置
  const saveSettings = (newSettings: ScriptSettings) => {
    try {
      settings.value = { ...newSettings };
      localStorage.setItem("scriptSettings", JSON.stringify(settings.value));
      message("设置保存成功", { type: "success" });
    } catch (error) {
      console.error("保存设置失败:", error);
      message("设置保存失败", { type: "error" });
    }
  };

  return {
    // 响应式数据
    scripts,
    categories,
    loading,
    error,
    stats,
    searchQuery,
    categoryFilter,
    typeFilter,
    includeInLogFilter,
    viewMode,
    sortField,
    sortDirection,
    settings,

    // 计算属性
    computedStats,
    filteredAndSortedScripts,

    // 方法
    fetchScripts,
    fetchCategories,
    executeDebug,
    executeRecord,
    performReplay,
    getScript,
    saveScript,
    createScript,
    importSingleScript,
    importBatchScripts,
    duplicateScript,
    removeScript,
    toggleScriptLogStatus,
    sortBy,
    loadSettings,
    saveSettings
  };
}
