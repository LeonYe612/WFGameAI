import type { FormRules } from "element-plus";

// 项目表单验证规则
export const projectRules: FormRules = {
  name: [
    { required: true, message: "请输入项目名称", trigger: "blur" },
    {
      min: 2,
      max: 50,
      message: "项目名称长度在 2 到 50 个字符",
      trigger: "blur"
    }
  ],
  description: [
    { max: 200, message: "描述不能超过 200 个字符", trigger: "blur" }
  ]
};

// 代码库表单验证规则
export const repositoryRules: FormRules = {
  url: [
    { required: true, message: "请输入代码库地址", trigger: "blur" },
    {
      pattern: /^https?:\/\/.+/,
      message: "请输入有效的代码库地址",
      trigger: "blur"
    }
  ],
  branch: [
    { required: true, message: "请输入分支名称", trigger: "blur" },
    {
      min: 1,
      max: 100,
      message: "分支名称长度在 1 到 100 个字符",
      trigger: "blur"
    }
  ],
  pathPattern: [
    { max: 200, message: "路径模式不能超过 200 个字符", trigger: "blur" }
  ]
};

// Git OCR 表单验证规则
export const gitOcrRules: FormRules = {
  projectId: [{ required: true, message: "请选择项目", trigger: "change" }],
  repositoryUrl: [
    { required: true, message: "请输入代码库地址", trigger: "blur" },
    {
      pattern: /^https?:\/\/.+/,
      message: "请输入有效的代码库地址",
      trigger: "blur"
    }
  ],
  branch: [{ required: true, message: "请输入分支名称", trigger: "blur" }],
  pathPattern: [
    { required: true, message: "请输入文件路径模式", trigger: "blur" }
  ],
  languages: [
    {
      validator: (rule, value, callback) => {
        if (!value || value.length === 0) {
          callback(new Error("请至少选择一种语言"));
        } else {
          callback();
        }
      },
      trigger: "change"
    }
  ]
};

// 上传 OCR 表单验证规则
export const uploadOcrRules: FormRules = {
  projectId: [{ required: true, message: "请选择项目", trigger: "change" }],
  files: [
    {
      validator: (rule, value, callback) => {
        if (!value || value.length === 0) {
          callback(new Error("请至少选择一个文件"));
        } else {
          callback();
        }
      },
      trigger: "change"
    }
  ],
  languages: [
    {
      validator: (rule, value, callback) => {
        if (!value || value.length === 0) {
          callback(new Error("请至少选择一种语言"));
        } else {
          callback();
        }
      },
      trigger: "change"
    }
  ]
};

// 过滤表单验证规则
export const filterRules: FormRules = {
  startDate: [
    {
      validator: (rule, value, callback) => {
        if (value && rule.field === "startDate") {
          const _form = rule.fullField?.split(".")[0];
          // 这里可以添加开始日期与结束日期的比较逻辑
        }
        callback();
      },
      trigger: "change"
    }
  ],
  endDate: [
    {
      validator: (rule, value, callback) => {
        if (value && rule.field === "endDate") {
          // 这里可以添加结束日期与开始日期的比较逻辑
        }
        callback();
      },
      trigger: "change"
    }
  ]
};
