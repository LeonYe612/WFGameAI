import { reactive } from "vue";
import type { FormRules } from "element-plus";
import { usePlanStoreHook } from "@/store/modules/plan";
import { planRunTypeEnum } from "@/utils/enums";

/** 自定义表单规则校验 */
export const formRules = reactive(<FormRules>{
  plan_type: [{ required: true, message: "请选择计划类型", trigger: "blur" }],
  name: [{ required: true, message: "必填项", trigger: "blur" }],
  inform: [{ required: true, message: "请选择是否开启推送", trigger: "blur" }],
  account: [{ required: true, message: "必填项", trigger: "blur" }],
  prefix: [{ required: true, message: "必填项", trigger: "blur" }], // 默认规则，必填项，其他的规则动态生成，在 getPrefixRules 接口中（不同项目不同规则）
  nick_prefix: [{ required: false, message: "选填", trigger: "blur" }],
  env: [{ required: true, message: "请选择运行环境", trigger: "blur" }],
  server_no: [{ required: true, message: "请选择服务器", trigger: "change" }],
  worker_queue: [
    { required: true, message: "请选择执行器", trigger: "change" }
  ],
  run_type: [{ required: true, message: "请选择运行类型", trigger: "blur" }],
  is_reuse: [
    { required: true, message: "请选择是否复用账号", trigger: "blur" }
  ],
  assign_account_type: [
    { required: true, message: "请选择填写账号的方式", trigger: "blur" }
  ],
  assign_account: [{ required: true, message: "请上传文件", trigger: "blur" }],
  cycle_type: [
    { required: true, message: "请选择循环控制类型", trigger: "blur" }
  ],
  "run_info.schedule": [
    {
      validator: (rule, value, callback) => {
        if (
          usePlanStoreHook().info.run_type === planRunTypeEnum.SCHEDULE.value
        ) {
          // 如果选择【定时】类型，此参数必填
          if (!value) {
            callback(new Error("请选择此计划定时运行的时间"));
          }
          if (value <= new Date()) {
            callback(new Error("定时时间只能选未来的某一时间"));
          }
          callback();
        }
      },
      trigger: "blur"
    }
  ],
  account_num: [
    { required: true, message: "必填项", trigger: "blur" },
    { type: "number", message: "请输入数字", trigger: "blur" }
  ],
  // 分批参数校验: 当启用batch_enabled参数的时候，batch_interval和batch_size必须大于0
  batch_enabled: [
    {
      validator: (rule, value, callback) => {
        if (usePlanStoreHook().info.batch_enabled) {
          if (usePlanStoreHook().info.batch_interval <= 0) {
            callback(new Error("分批间隔时间必须大于0"));
          }
          if (usePlanStoreHook().info.batch_size <= 0) {
            callback(new Error("分批大小必须大于0"));
          }
        }
        callback();
      },
      trigger: "blur"
    }
  ]
  // times: [
  //   { required: true, message: "必填项", trigger: "blur" },
  //   { type: "number", message: "请输入数字", trigger: "blur" }
  // ],
  // interval: [
  //   { required: true, message: "必填项", trigger: "blur" },
  //   { type: "number", message: "请输入数字", trigger: "blur" }
  // ],
});
