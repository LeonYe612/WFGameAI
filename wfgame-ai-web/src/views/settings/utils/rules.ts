import { reactive } from "vue";
import type { FormRules } from "element-plus";

/** 系统设置表单规则校验 */
export const systemSettingsRules = reactive(<FormRules>{
  systemName: [
    { required: true, message: "系统名称为必填项", trigger: "blur" },
    {
      min: 2,
      max: 50,
      message: "系统名称长度应在2-50字符之间",
      trigger: "blur"
    }
  ],
  adminEmail: [
    { required: true, message: "管理员邮箱为必填项", trigger: "blur" },
    { type: "email", message: "请输入正确的邮箱格式", trigger: "blur" }
  ],
  maxDevice: [
    { required: true, message: "最大设备数量为必填项", trigger: "blur" },
    {
      type: "number",
      min: 1,
      max: 1000,
      message: "设备数量应在1-1000之间",
      trigger: "blur"
    }
  ],
  reportRetentionDays: [
    { required: true, message: "报告保留天数为必填项", trigger: "blur" },
    {
      type: "number",
      min: 1,
      max: 365,
      message: "保留天数应在1-365天之间",
      trigger: "blur"
    }
  ],
  timeZone: [{ required: true, message: "请选择时区", trigger: "change" }]
});
