import { reactive } from "vue";
import type { FormRules } from "element-plus";
/** 自定义表单规则校验 */
export const formRules = reactive(<FormRules>{
  date_range: [
    {
      validator: (rule, value, callback) => {
        if (!value) {
          callback(new Error("必填项"));
        }
        if (Array.isArray(value) && value.length === 0) {
          callback(new Error("必填项"));
        }
        if (Array.isArray(value) && value.length === 2 && !value[0]) {
          callback(new Error("必填项"));
        }
        callback();
      },
      trigger: "blur"
    }
  ],
  which_days: [{ required: true, message: "必填项", trigger: "blur" }],
  run_time: [{ required: true, message: "必填项", trigger: "blur" }]
});
