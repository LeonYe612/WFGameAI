/** 各个页面对应的按钮权限CODE */
// 按钮权限CODE命名规则：页面名+权限类型
export const perms = {
  /** 脚本管理 */
  script: {
    // 列表
    list: {
      view: "AI-SCRIPTS-LIST-VIEW",
      edit: "AI-SCRIPTS-LIST-EDIT",
      delete: "AI-SCRIPTS-LIST-DELETE"
    },
    // 详情
    detail: {
      view: "AI-SCRIPTS-DETAIL-VIEW",
      edit: "AI-SCRIPTS-DETAIL-EDIT",
      delete: "AI-SCRIPTS-DETAIL-DELETE"
    }
  },
  /** OCR */
  ocr: {
    // 列表
    list: {
      view: "AI-OCR-LIST-VIEW",
      edit: "AI-OCR-LIST-EDIT",
      delete: "AI-OCR-LIST-DELETE"
    },
    // 结果
    result: {
      view: "AI-OCR-RESULT-VIEW",
      edit: "AI-OCR-RESULT-EDIT",
      delete: "AI-OCR-RESULT-DELETE"
    }
  }
};
