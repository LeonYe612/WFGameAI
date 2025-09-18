import { ref, reactive } from "vue";
import {
  getSystemSettings,
  saveSystemSettings,
  resetSystemSettings,
  getPythonEnvironments,
  switchPythonEnvironment
} from "@/api/settings";
import type {
  SystemSettings,
  PythonEnvironment,
  SwitchEnvRequest,
  SettingsMenuItem,
  TimeZoneOption
} from "./types";
import { superRequest } from "@/utils/request";
import { message } from "@/utils/message";

export function useSettingsManagement() {
  // 响应式数据
  const loading = ref(false);
  const activeMenu = ref("general");
  const systemSettings = reactive<SystemSettings>({
    systemName: "WFGame AI自动化测试平台",
    adminEmail: "admin@example.com",
    maxDevice: 100,
    reportRetentionDays: 90,
    timeZone: "Asia/Shanghai",
    enableNotifications: true,
    enableAutoBackup: true,
    debugMode: false
  });

  const pythonEnvs = ref<PythonEnvironment[]>([]);
  const pythonEnvLoading = ref(false);
  const pythonEnvError = ref("");

  // 菜单项配置
  const menuItems: SettingsMenuItem[] = [
    {
      id: "general",
      label: "通用设置",
      icon: "Setting",
      component: "GeneralSettings"
    },
    {
      id: "python",
      label: "Python环境",
      icon: "Monitor",
      component: "PythonSettings"
    },
    {
      id: "user",
      label: "用户管理",
      icon: "User",
      component: "UserManagement"
    },
    { id: "ai", label: "AI设置", icon: "MagicStick", component: "AISettings" },
    {
      id: "backup",
      label: "备份与恢复",
      icon: "Download",
      component: "BackupRestore"
    },
    { id: "log", label: "系统日志", icon: "Document", component: "SystemLog" },
    { id: "api", label: "API配置", icon: "Link", component: "APISettings" }
  ];

  // 时区选项
  const timeZoneOptions: TimeZoneOption[] = [
    { value: "Asia/Shanghai", label: "中国标准时间 (UTC+8)" },
    { value: "UTC", label: "协调世界时 (UTC)" },
    { value: "America/New_York", label: "美国东部时间 (UTC-5)" },
    { value: "Europe/London", label: "英国时间 (UTC+0)" }
  ];

  // 获取系统设置
  const fetchSystemSettings = async () => {
    await superRequest({
      apiFunc: getSystemSettings,
      onBeforeRequest: () => {
        loading.value = true;
      },
      onSucceed: (data: SystemSettings) => {
        Object.assign(systemSettings, data);
      },
      onFailed: (err: any) => {
        message(`获取系统设置失败: ${err}`, { type: "error" });
      },
      onCompleted: () => {
        loading.value = false;
      }
    });
  };

  // 保存系统设置
  const saveSettings = async () => {
    await superRequest({
      apiFunc: saveSystemSettings,
      apiParams: systemSettings,
      enableSucceedMsg: true,
      succeedMsgContent: "系统设置保存成功！",
      onFailed: () => {
        message("保存系统设置失败", { type: "error" });
      }
    });
  };

  // 重置系统设置
  const resetSettings = async () => {
    await superRequest({
      apiFunc: resetSystemSettings,
      enableSucceedMsg: true,
      succeedMsgContent: "系统设置重置成功！",
      onSucceed: () => {
        // 重置成功后重新获取设置
        fetchSystemSettings();
      },
      onFailed: () => {
        message("重置系统设置失败", { type: "error" });
      }
    });
  };

  // 获取Python环境列表
  const fetchPythonEnvironments = async () => {
    await superRequest({
      apiFunc: getPythonEnvironments,
      onBeforeRequest: () => {
        pythonEnvLoading.value = true;
        pythonEnvError.value = "";
      },
      onSucceed: (data: any) => {
        if (data.success) {
          pythonEnvs.value = data.envs || [];
        } else {
          pythonEnvError.value = data.message || "获取Python环境失败";
        }
      },
      onFailed: (err: any) => {
        pythonEnvError.value = err.message || "获取Python环境失败";
        pythonEnvs.value = [];
      },
      onCompleted: () => {
        pythonEnvLoading.value = false;
      }
    });
  };

  // 切换Python环境
  const switchPythonEnv = async (envPath: string) => {
    const requestData: SwitchEnvRequest = { path: envPath };

    await superRequest({
      apiFunc: switchPythonEnvironment,
      apiParams: requestData,
      enableSucceedMsg: true,
      succeedMsgContent: "Python环境切换成功！",
      onSucceed: () => {
        // 切换成功后重新获取环境列表
        fetchPythonEnvironments();
      },
      onFailed: () => {
        message("切换Python环境失败", { type: "error" });
      }
    });
  };

  // 切换菜单
  const switchMenu = (menuId: string) => {
    activeMenu.value = menuId;
  };

  return {
    // 响应式数据
    loading,
    activeMenu,
    systemSettings,
    pythonEnvs,
    pythonEnvLoading,
    pythonEnvError,

    // 配置数据
    menuItems,
    timeZoneOptions,

    // 方法
    fetchSystemSettings,
    saveSettings,
    resetSettings,
    fetchPythonEnvironments,
    switchPythonEnv,
    switchMenu
  };
}
