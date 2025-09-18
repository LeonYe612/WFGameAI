import { reactive } from "vue";
import type { FormRules } from "element-plus";

/** 自定义表单规则校验 */
export const formRules = reactive(<FormRules>{
  catalog_id: [{ required: true, message: "必填项", trigger: "blur" }],
  name: [{ required: true, message: "必填项", trigger: "blur" }],
  type: [{ required: true, message: "必填项", trigger: "blur" }],
  env: [{ required: false, message: "必填项", trigger: "blur" }],
  server_no: [{ required: false, message: "必填项", trigger: "blur" }],
  account: [{ required: false, message: "必填项", trigger: "blur" }]
});
