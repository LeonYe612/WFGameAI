import { reactive } from "vue";
import type { FormRules } from "element-plus";

/** 设备管理表单规则校验 */
export const deviceFormRules = reactive(<FormRules>{
  device_id: [
    { required: true, message: "设备ID为必填项", trigger: "blur" },
    { min: 3, max: 50, message: "设备ID长度应在3-50字符之间", trigger: "blur" }
  ],
  brand: [{ required: true, message: "品牌为必填项", trigger: "blur" }],
  model: [{ required: true, message: "型号为必填项", trigger: "blur" }],
  ip_address: [
    {
      pattern:
        /^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/,
      message: "请输入正确的IP地址格式",
      trigger: "blur"
    }
  ]
});
