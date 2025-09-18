import { reactive } from "vue";
import type { FormRules } from "element-plus";

/** 数据源表单规则校验 */
export const dataSourceFormRules = reactive(<FormRules>{
  name: [
    { required: true, message: "数据源名称为必填项", trigger: "blur" },
    { min: 2, max: 50, message: "名称长度应在2-50字符之间", trigger: "blur" }
  ],
  type: [{ required: true, message: "请选择数据源类型", trigger: "change" }],
  description: [{ max: 200, message: "描述不能超过200字符", trigger: "blur" }]
});

/** 导入数据表单规则校验 */
export const importDataFormRules = reactive(<FormRules>{
  file: [{ required: true, message: "请选择要导入的文件", trigger: "change" }],
  encoding: [{ required: true, message: "请选择文件编码", trigger: "change" }]
});

/** 数据库连接配置规则 */
export const databaseConfigRules = reactive(<FormRules>{
  host: [{ required: true, message: "主机地址为必填项", trigger: "blur" }],
  port: [
    { required: true, message: "端口号为必填项", trigger: "blur" },
    { pattern: /^\d+$/, message: "端口号必须为数字", trigger: "blur" }
  ],
  database: [{ required: true, message: "数据库名为必填项", trigger: "blur" }],
  username: [{ required: true, message: "用户名为必填项", trigger: "blur" }],
  password: [{ required: true, message: "密码为必填项", trigger: "blur" }]
});
