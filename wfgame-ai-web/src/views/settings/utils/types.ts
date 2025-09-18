import type {
  SystemSettings,
  PythonEnvironment,
  PythonEnvResponse,
  SwitchEnvRequest,
  ApiResponse
} from "@/api/settings";

// 重新导出类型
export type {
  SystemSettings,
  PythonEnvironment,
  PythonEnvResponse,
  SwitchEnvRequest,
  ApiResponse
};

// 设置菜单项类型
export interface SettingsMenuItem {
  id: string;
  label: string;
  icon: string;
  component: string;
}

// 表单验证规则类型
export interface SettingsFormRules {
  [key: string]: any[];
}

// 时区选项类型
export interface TimeZoneOption {
  value: string;
  label: string;
}
