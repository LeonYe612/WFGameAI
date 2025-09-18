import { reactive } from "vue";
import type { FormRules } from "element-plus";

/** 脚本管理表单规则校验 */
export const scriptFormRules = reactive(<FormRules>{
  filename: [
    { required: true, message: "脚本名称为必填项", trigger: "blur" },
    {
      min: 1,
      max: 100,
      message: "脚本名称长度应在1-100字符之间",
      trigger: "blur"
    },
    {
      pattern: /^[a-zA-Z0-9_\u4e00-\u9fa5.-]+$/,
      message: "脚本名称只能包含字母、数字、中文、下划线、点号和连字符",
      trigger: "blur"
    }
  ],
  category: [{ required: false, message: "脚本分类为必填项", trigger: "blur" }],
  description: [
    { max: 500, message: "描述长度不能超过500字符", trigger: "blur" }
  ],
  content: [
    { required: true, message: "脚本内容为必填项", trigger: "blur" },
    { min: 1, message: "脚本内容不能为空", trigger: "blur" }
  ],
  python_path: [
    { required: true, message: "Python路径为必填项", trigger: "blur" }
  ]
});

/** 回放配置表单规则 */
export const replayFormRules = reactive(<FormRules>{
  script_filename: [
    { required: true, message: "请选择要回放的脚本", trigger: "change" }
  ],
  delay: [
    {
      type: "number",
      min: 0,
      max: 10000,
      message: "延迟时间应在0-10000毫秒之间",
      trigger: "blur"
    }
  ],
  loop: [
    {
      type: "number",
      min: 1,
      max: 100,
      message: "循环次数应在1-100次之间",
      trigger: "blur"
    }
  ]
});
