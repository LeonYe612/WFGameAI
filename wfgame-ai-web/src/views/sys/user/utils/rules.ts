import { reactive } from "vue";
import type { FormRules } from "element-plus";
import { REGEXP_PWD } from "@/views/login/utils/rule";

/** 自定义表单规则校验 */
export const formRules = reactive(<FormRules>{
  username: [{ required: true, message: "请填写用户名", trigger: "blur" }],
  chinese_name: [{ required: true, message: "请填写姓名", trigger: "blur" }],
  name: [{ required: true, message: "请填写姓名", trigger: "blur" }],
  phone: [{ required: true, message: "请填写手机号", trigger: "blur" }],
  password: [
    {
      validator: (rule, value, callback) => {
        // console.log(rule, value, callback);
        if (!value) {
          // callback(new Error("请输入密码"));
          callback();
        } else if (!REGEXP_PWD.test(value)) {
          callback(
            new Error("密码格式应为8-18位数字、字母、符号的任意两种组合")
          );
        }
      },
      trigger: "blur"
    }
  ]
});

export const getFormRules = (isAdd: boolean) => {
  const formRules = reactive(<FormRules>{
    username: [{ required: true, message: "请填写用户名", trigger: "blur" }],
    chinese_name: [{ required: true, message: "请填写姓名", trigger: "blur" }],
    name: [{ required: true, message: "请填写姓名", trigger: "blur" }],
    phone: [{ required: true, message: "请填写手机号", trigger: "blur" }],
    password: [
      {
        validator: (rule, value, callback) => {
          if (!value && !isAdd) {
            callback(); // 编辑操作且密码为空，直接通过验证
          } else if (!value) {
            callback(new Error("请输入密码"));
          } else if (!REGEXP_PWD.test(value)) {
            callback(
              new Error("密码格式应为8-18位数字、字母、符号的任意两种组合")
            );
          } else {
            callback(); // 符合密码格式，通过验证
          }
        },
        trigger: "blur"
      }
    ]
  });
  return formRules;
};
