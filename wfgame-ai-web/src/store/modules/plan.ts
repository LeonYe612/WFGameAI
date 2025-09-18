import { defineStore } from "pinia";
import { store } from "@/store";
import { editPlan, generateAccountPrefix } from "@/api/plan";
import {
  ElMessage,
  ElMessageBox,
  FormInstance,
  UploadRequestOptions,
  UploadUserFile
} from "element-plus";
import { superRequest } from "@/utils/request";
import {
  envEnum,
  planTypeEnum,
  planInformEnum,
  planRunTypeEnum,
  planTypeEnumTabs,
  caseTypeEnum,
  reuseAccountEnum
} from "@/utils/enums";
import { message } from "@/utils/message";
import { ref } from "vue";
import { fileUpload, generareAccountCsv } from "@/api/file";
import { cloneDeep } from "@pureadmin/utils";
import { CaseQueueItem } from "../types";
// import md5 from "md5";
/** 一些初始值 */
const defaultInfo = () => {
  return {
    id: null,
    name: "",
    env: envEnum.TEST,
    server_no: null,
    account: "",
    worker_queue: "",
    plan_type: planTypeEnum.PLAN.value,
    run_type: planRunTypeEnum.SINGLE.value, // 1: 调试-DEBUG 2: 单次-SINGLE 3: 定时-SCHEDULE 4: 周期-CIRCLE
    run_info: {
      schedule: null, // 定时执行类型：只需要采集一个日期时间即可。示例："2021-01-01 12:00:00"
      circle: {
        // 周期执行类型：需要采集一个日期范围，指定一周的哪些天，一个运行时间
        date_range: ["", ""], // 周期运行的日期范围，示例：["2021-01-01 00:00:00", "2021-01-31 23:59:59"]
        which_days: [], // 在一周的哪些天执行, 示例: [1, 2, 4, 7]
        run_time: "" // 运行时间, 示例："12:00:00"
      }
    },
    inform: planInformEnum.DISABLE.value,
    prefix: "", // 账号前缀
    assign_account: "", // 指定具体测试账号 & 密码，和prefix互斥（前端该值为文件路径【服务器】，由后端统一处理）
    account_num: 1, // 默认账号数量1
    account_num_min: 1, // 账号数量最小值
    account_num_max: 1, // 账号数量最大值
    cycle_type: 0, // 默认循环控制类型0（循环次数控制），1（循环时间控制）
    times: 1, // 默认执行次数1
    interval: 0, // 默认执行间隔0毫秒
    case_type: 0, // 用例类型，
    is_reuse: reuseAccountEnum.ENABLE.value, // 是否复用账号
    account_len: 10, // 账号长度
    nick_prefix: "", // 账号前缀长度
    // 分批次操作相关参数
    batch_enabled: false, // 是否启用分批次操作
    batch_size: 0, // 分批次操作的批次大小
    batch_interval: 0, // 分批次操作的批次间隔(毫秒)
    // 以下字段切换plan_type时候需要单独清理
    case_queue: ref<CaseQueueItem[][]>([]),
    old_tab_name: ref("0"), // 上一次选中的tab（默认并发执行组）
    new_tab_name: ref("0"), // 当前选中的tab（默认并发执行组）
    whole_case_queue: ref([{ "0": [] }]), // 所有执行组的case_queue信息，示例：[{"tab_name1": [case_queue1}, {"tab_name2": [case_queue2}]]
    editableTabs: ref([planTypeEnumTabs.PLAN.value]), // 执行组分类
    assign_account_type: 0,
    upload_file_list: [],
    cycle_text: "次，间隔",
    select_disabled: false
  };
};

export const usePlanStore = defineStore({
  id: "pure-plan",
  state: () => ({
    info: defaultInfo(),
    // 相关组件间的共享状态值
    shareState: {
      // loading
      detailLoading: false, // 详情信息加载loading
      saveLoading: false, // 保存loading
      // planConfirmer组件全局设置：用来控制每次打开 confirmer 时是否保留当前设置
      keepCurrentSettings: true,
      uploading: false // 上传文件loading
    }
  }),
  actions: {
    assignValue(to: any, from: any) {
      if (from === null || typeof from !== "object") return;
      Object.keys(from).forEach(key => {
        if (key in to) {
          const value = to[key];
          if (Array.isArray(value)) {
            // 数组类型，不能改变原数组的引用，需要先清空，再push
            to[key].splice(0, to[key].length);
            // 防止没有值的情况
            if (from[key] === null || from[key] === undefined) {
              return;
            }
            // 非ref数组嵌套数组类型
            if (Array.isArray(from[key])) {
              from[key].forEach(item => {
                if (typeof item === "object" && item !== null) {
                  to[key].push({ ...item });
                } else {
                  to[key].push(item);
                }
              });
            } else if (Array.isArray(from[key].value)) {
              // ref数组嵌套数组类型-whole_case_queue
              to[key].push(...from[key].value);
            }
          } else if (typeof value === "object" && value !== null) {
            // 如果属性值是对象，则递归处理
            this.assignValue(to[key], from[key]);
          } else {
            // 其他类型的属性直接赋值
            to[key] = from[key];
          }
        }
        // else {
        //   console.warn(`Key ${key} not found in target object`, to);
        // }
      });
    },
    /** 设置info中的信息 */
    SET_INFO(obj: any) {
      this.assignValue(this.info, obj);
    },
    /** 重置info的信息 */
    RESET_INFO() {
      this.assignValue(this.info, defaultInfo());
    },
    /** 清空STEP列表 */
    CLEAR_CASE_QUEUE() {
      this.info.case_queue.splice(0, this.info.case_queue.length);
    },
    /** 清空全量列表 */
    CLEAR_WHOLE_CASE_QUEUE() {
      this.info.whole_case_queue.splice(0, this.info.whole_case_queue.length);
    },
    /** 生成版本列表 */
    GET_VERSION_LIST(caseElement: any) {
      const { version_list, version } = caseElement;
      if (version_list?.length) {
        const versionOptions = [];
        for (let i = 0; i < version_list?.length; i++) {
          // 判断item是否为整数
          const item = version_list[i];
          if (typeof item === "number") {
            versionOptions.push({
              label: `第 ${item} 版`,
              value: item
            });
          } else if (typeof item === "object") {
            versionOptions.push({
              label: `第 ${item?.value} 版`,
              value: item?.value
            });
          }
        }
        return versionOptions;
      } else if (version) {
        const versionOptions = [];
        for (let i = 1; i <= version; i++) {
          versionOptions.push({
            label: `第 ${i} 版`,
            value: i
          });
        }
        return versionOptions;
      } else {
        return [];
      }
    },
    /** 将选中的用例添加到 case_queue 中 */
    ADD_TO_CASE_QUEUE(selected: any[]) {
      // 兼容plan模式（多执行组）为嵌套结构体[[{}], [{}]]，debug模式为单层[{}, {}]
      if (!Array.isArray(selected)) {
        return;
      }
      if (!Array.isArray(selected[0])) {
        selected.forEach(item => {
          this.info.case_queue.push({
            // 从list页面跳转过来，需要从 item.case_base_id 中获取用例id
            // 从用例选择器中添加用例时，需要从 item.id 中获取用例id
            case_base_id: item.case_base_id || item.id,
            version: item.version,
            selectedVersion: item.selectedVersion || item.version,
            name: item.name,
            version_list: this.GET_VERSION_LIST(item.version)
          });
        });
      }
    },
    /** 从 case_queue中移除指定index的用例 */
    REMOVE_FROM_CASE_QUEUE(index: number) {
      this.info.case_queue.splice(index, 1);
    },
    /** 设置run_info.circle */
    SET_RUN_INFO_CIRCLE(circleObj: any) {
      const circle = this.info.run_info.circle;
      circle.date_range[0] = circleObj.date_range[0];
      circle.date_range[1] = circleObj.date_range[1];
      circle.which_days.splice(0, circle.which_days.length);
      circleObj.which_days.forEach(item => {
        circle.which_days.push(item);
      });
      circle.run_time = circleObj.run_time;
    },

    /** 设置old_tab_name */
    SET_OLD_TAB_NAME(tabName: string) {
      this.info.old_tab_name = tabName;
    },
    /** 设置new_tab_name */
    SET_NEW_TAB_NAME(tabName: string) {
      this.info.new_tab_name = tabName;
    },
    /** 添加新的 tab_name 到 store.info.whole_case_queue */
    ADD_TO_WHOLE_CASE_QUEUE(tabName: string) {
      const addExistingTab = this.info.whole_case_queue.find(
        tab => Object.keys(tab)[0] === tabName
      );

      if (!addExistingTab) {
        const newTab = {};
        newTab[tabName] = [];
        this.info.whole_case_queue.push(newTab);
      }
    },
    /** 删除对应 tab_name 的用例选择器数据 */
    DELETE_TO_WHOLE_CASE_QUEUE(tabName: string) {
      const delExistingTab = this.info.whole_case_queue.find(
        tab => Object.keys(tab)[0] === tabName.toString()
      );
      if (delExistingTab) {
        this.info.whole_case_queue = this.info.whole_case_queue.filter(
          tab => Object.keys(tab)[0] !== tabName.toString()
        );
      }
    },
    /** 更新对应 tab_name 的用例选择器数据 到 store.info.whole_case_queue */
    UPDATE_TO_WHOLE_CASE_QUEUE(tabName: string, case_queue: any[]) {
      // 过滤掉 Proxy 对象
      const filteredCaseQueue = case_queue.map(item => {
        if (typeof item === "object" && item !== null) {
          return { ...item };
        }
        return item;
      });

      const existingTab = this.info.whole_case_queue.find(
        tab => Object.keys(tab)[0] === tabName
      );
      if (existingTab) {
        existingTab[tabName] = [...filteredCaseQueue];
      } else {
        const newTab = {};
        newTab[tabName] = [...filteredCaseQueue];
        this.info.whole_case_queue.push(newTab);
      }
    },
    /** 调整当前页签的case_queue，而不是重置 */
    SET_CASE_QUEUE(tabName: string) {
      const existingTab = this.info.whole_case_queue.find(
        tab => Object.keys(tab)[0] === tabName
      );
      if (existingTab) {
        // 使用 Vue.set 设置 case_queue 的值
        this.info.case_queue.splice(0, this.info.case_queue.length);
        this.info.case_queue.push(...existingTab[tabName]);
      } else {
        this.info.case_queue.splice(0, this.info.case_queue.length);
      }
    },
    /** plans/list接口数据中的case_queue解析后，拍平放入whole_case_queue中*/
    UPDATE_TO_CASE_QUEUE(selected: any[]) {
      this.CLEAR_WHOLE_CASE_QUEUE();
      this.CLEAR_CASE_QUEUE();
      if (!Array.isArray(selected[0])) {
        // 处理非嵌套数组情况
        const caseList = selected.map(item => ({
          case_base_id: item.case_base_id || item.id,
          version: item.version,
          selectedVersion: item.selectedVersion || item.version,
          name: item.name,
          version_list: this.GET_VERSION_LIST(item.version),
          account: "",
          token: ""
        }));
        this.info.case_queue.push(...caseList);
        this.UPDATE_TO_WHOLE_CASE_QUEUE("0", caseList);
      } else {
        // 处理嵌套数组情况
        selected.forEach((tab, tabIndex) => {
          const caseList = tab.map(item => ({
            case_base_id: item.case_base_id,
            version: item.version,
            selectedVersion: item.selectedVersion || item.version,
            name: item.name,
            version_list: this.GET_VERSION_LIST(item)
          }));
          const tabName = tabIndex.toString();
          this.UPDATE_TO_WHOLE_CASE_QUEUE(tabName, caseList);
          this.info.case_queue.push(...caseList);
        });
      }
    },
    /** 更新当前计划类型*/
    UPDATE_PLAN_TYPE(planType: number) {
      this.info.plan_type = planType;
    },
    /** 根据plan_type动态更新对应的tab页签默认组类型 */
    UPDATE_DEFAULT_EDITTABLES(planType: number) {
      let plan_type_key;
      if (planType) {
        plan_type_key = this.PLAN_TYPE_VALUE_TO_KEY(planType);
      } else {
        plan_type_key = "PLAN";
      }
      this.info.editableTabs.splice(
        0,
        1,
        planTypeEnumTabs[plan_type_key].value
      );
    },
    /** 根据plan_type获取对应默认执行组的key，例如：【DEBUG、ROBOT】 */
    PLAN_TYPE_VALUE_TO_KEY(planType: number) {
      const planTypeValueToKey: Record<number, string> = {};
      for (const key in planTypeEnum) {
        const value = planTypeEnum[key].value;
        planTypeValueToKey[value] = key;
      }
      return planTypeValueToKey[planType];
    },
    /** 新增执行组页签*/
    ADD_GROUP_TABS(tab) {
      this.info.editableTabs.push(tab);
    },
    /** 删除执行组页签*/
    DELETE_GROUP_TABS(tabName) {
      this.info.editableTabs = this.info.editableTabs.filter(
        tab => tab.name !== tabName
      );
    },
    /** 根据计划类型，更新对应用例类型*/
    UPDATE_CASE_TYPE() {
      switch (this.info.plan_type) {
        case planTypeEnum.DEBUG.value:
        case planTypeEnum.PLAN.value:
          this.info.case_type = caseTypeEnum.COMMON.value;
          break;
        case planTypeEnum.ROBOT.value:
          this.info.case_type = caseTypeEnum.ROBOT.value;
          break;
        case planTypeEnum.BET.value:
          this.info.case_type = caseTypeEnum.BET.value;
          break;
        case planTypeEnum.FIRE.value:
          this.info.case_type = caseTypeEnum.FIRE.value;
          break;
        default:
          this.info.case_type = caseTypeEnum.ALL.value;
      }
    },
    /** 更新指定字段为初始值 case_queue && whole_case_queue && 执行组*/
    RESET_ASSIGN_FIELD_INFO(fieldsToUpdate) {
      const defaultValues = defaultInfo();
      fieldsToUpdate.forEach(field => {
        if (Object.prototype.hasOwnProperty.call(this.info, field)) {
          if (Array.isArray(this.info[field])) {
            this.info[field].splice(0, this.info[field].length);
          } else {
            this.info[field] = defaultValues[field];
          }
        }
      });
    },
    GENERATE_ACCOUNT_CSV() {
      // 调用生成文件接口，然后把返回的文件名 更新给assign_account
      //"url": "/v1/download/admin/test/account_202409052057.csv"
      if (this.info.assign_account) {
        const jsonData = {
          env: this.info.env,
          assign_account: JSON.stringify(this.info.assign_account)
        };
        superRequest({
          apiFunc: generareAccountCsv,
          apiParams: jsonData, // 修改这里
          enableSucceedMsg: true,
          succeedMsgContent: `生成账号csv文件至服务器成功 ！`,
          enableFailedMsg: true,
          onSucceed: data => {
            this.info.assign_account = data.url; //上传成功后，需要动态更新当前的文件路径
            const uploadFile: UploadUserFile = {
              name: data.url.split("/").pop()
            };
            this.info.upload_file_list = [uploadFile];
          }
        });
      }
    },
    UPDATE_ASSIGN_PARAMS(row) {
      // 2025-06-10 修改：增加[自定义编排]类型
      // 说明：自定义编排类型只需要简单双向绑定 case_queue 字段即可，无需其他渲染操作
      if (row.plan_type === planTypeEnum.ARRANGE.value) {
        this.info.case_queue = cloneDeep(row.case_queue);
        return;
      } else {
        // 把添加完的用例信息添加到case_queue，用于显示 & 记录当前执行组的用例信息
        this.ADD_TO_CASE_QUEUE(cloneDeep(row.case_queue));
        // 查看计划内容前，要先把接口中的case_queue的数据更新到whole_case_queue中，注意区分此处case_queue是接口中的内容，而不是前端store中的
        this.UPDATE_TO_CASE_QUEUE(cloneDeep(row.case_queue));
        // 根据计划类型，动态更新对应的默认执行组
        this.UPDATE_DEFAULT_EDITTABLES(cloneDeep(row.plan_type));
      }

      // 根据测试账号是否有值，更新账号填写类型(当前字段在上传后返回的是文件路径string，在下载时为账号对应的值array[object])
      if (this.info.assign_account && this.info.assign_account.length !== 0) {
        this.info.assign_account_type = 1;
      } else {
        this.info.assign_account_type = 0;
      }
      // 根据循环控制类型，更新循环控制文字描述
      if (this.info.cycle_type === 0) {
        this.info.cycle_text = "次，间隔";
      } else {
        this.info.cycle_text = "分钟，间隔";
      }
    },

    // 保存函数备份（稳定后移除）
    async save(formEl: FormInstance | undefined, onSucceed?: Function) {
      let isReuse = this.info.is_reuse;
      if (
        this.info.id &&
        this.info.run_type === planRunTypeEnum.WEBHOOK.value
      ) {
        // 编辑计划时，如果是webhook类型，允许复用账号
        isReuse = reuseAccountEnum.ENABLE.value;
      }
      // 先校验账号前缀是否合规
      superRequest({
        apiFunc: generateAccountPrefix,
        apiParams: {
          env: this.info.env,
          target_name: this.info.prefix,
          is_reuse: isReuse,
          target_num: this.info.account_num,
          target_num_min: this.info.account_num_min,
          target_num_max: this.info.account_num_max
        },
        enableSucceedMsg: false, // 禁用成功提示
        enableFailedMsg: false,
        onBeforeRequest: () => {
          this.shareState.saveLoading = true;
        },
        onSucceed: async data => {
          // 校验表单
          if (!formEl) {
            this.shareState.saveLoading = false;
            return;
          }
          try {
            // Validate the form asynchronously
            const valid = await formEl.validate();
            if (!valid) {
              this.shareState.saveLoading = false;
              return;
            }

            // 用来保存最后一次操作的页签内容
            const new_tab_case_queue = this.info.case_queue;
            this.UPDATE_TO_WHOLE_CASE_QUEUE(
              this.info.new_tab_name,
              new_tab_case_queue
            );

            // 处理用例队列，过滤whole_case_queue中的空数据，避免提交空数据，同时点击保存后，自动更新最后一个页签的case_queue数据，
            const case_queue = this.info.whole_case_queue
              .map(tab => {
                const tabName = Object.keys(tab)[0];
                const cases = tab[tabName];

                if (cases.length === 0) {
                  return [];
                }

                return cases.map(item => {
                  return {
                    case_base_id: item.case_base_id,
                    version: item.selectedVersion,
                    name: item.name
                  };
                });
              })
              .filter((item, index) => index === 0 || item.length > 0);

            // 更新的数据
            this.info.account_len = data.account_len;
            const postData = { ...this.info, case_queue };
            if (case_queue[0].length === 0 && case_queue.length <= 1) {
              message("尚未在测试计划中添加用例！", { type: "warning" });
              this.shareState.saveLoading = false;
              return;
            }
            // console.log("postData : ", JSON.stringify(postData));
            // 确认是否继续创建测试计划(只有在新建计划时才会弹出)
            if (!this.info.id) {
              await ElMessageBox.confirm(
                "测试计划一旦创建后无法再次编辑，确认继续？",
                "友情提示",
                {
                  confirmButtonText: "继续",
                  cancelButtonText: "取消",
                  type: "warning"
                }
              );
            }

            // 发送新建测试计划请求
            await superRequest({
              apiFunc: editPlan,
              apiParams: postData,
              enableSucceedMsg: true, // 启用成功提示
              onBeforeRequest: () => {
                this.shareState.saveLoading = true;
              },
              onSucceed: data => {
                // 更新测试计划id
                this.info.id = data?.id;
                // 执行成功回调
                if (onSucceed) {
                  typeof onSucceed === "function" && onSucceed(data);
                }
                // 根据当前所在页面判断跳转逻辑
                const currRoute = this.$router.currentRoute;
                if (currRoute.name === "TestCaseList") {
                  // a. 在用例列表页面
                  if (!onSucceed) {
                    message("计划创建成功，您可以前往计划列表查看！", {
                      type: "success"
                    });
                  }
                } else {
                  // b. 计划创建页面
                  history.back();
                }
              },
              onCompleted: () => {
                this.shareState.saveLoading = false;
              }
            });
          } catch (error) {
            console.error("editPlan error occurred:", error);
            this.shareState.saveLoading = false;
          }
        },
        onFailed: (data, msg) => {
          this.shareState.saveLoading = false;
          if (msg.includes("账号前缀已注册")) {
            ElMessage.error("账号前缀已注册，请重新生成");
          } else {
            ElMessageBox.alert(
              `您设置的账号长度超出输入范围<br>` +
                `规则：账号长度 = 前缀字符长度 + 执行人数单位长度<br>` +
                `即10 = 7【前缀字符长度】+ 3【执行人数 999】<br>`,
              {
                dangerouslyUseHTMLString: true,
                type: "error"
              }
            );
          }
        },
        onCompleted: () => {
          this.shareState.saveLoading = false;
        }
      });
    },

    // 保存函数（用于编排计划类型）
    async saveArrangePlan(
      formEl: FormInstance | undefined,
      onSucceed?: Function
    ) {
      let isReuse = this.info.is_reuse;
      if (
        this.info.id &&
        this.info.run_type === planRunTypeEnum.WEBHOOK.value
      ) {
        // 编辑计划时，如果是webhook类型，允许复用账号
        isReuse = reuseAccountEnum.ENABLE.value;
      }
      // 先校验账号前缀是否合规
      superRequest({
        apiFunc: generateAccountPrefix,
        apiParams: {
          env: this.info.env,
          target_name: this.info.prefix,
          is_reuse: isReuse,
          target_num: this.info.account_num,
          target_num_min: this.info.account_num_min,
          target_num_max: this.info.account_num_max
        },
        enableSucceedMsg: false, // 禁用成功提示
        enableFailedMsg: false,
        onBeforeRequest: () => {
          this.shareState.saveLoading = true;
        },
        onSucceed: async data => {
          // 校验表单
          if (!formEl) {
            this.shareState.saveLoading = false;
            return;
          }
          try {
            const valid = await formEl.validate();
            if (!valid) {
              this.shareState.saveLoading = false;
              return;
            }

            // [遍历 case_queue]
            // a. 设置每个 caseQueueItem 的 block_index 和 inner_index
            // b. 计算总用例数
            // c. 校验用例的账户信息：相同执行组内不能使用同账号；所有用例都需要有账号信息；
            let totalCases = 0;
            for (let i = 0; i < this.info.case_queue.length; i++) {
              const block = this.info.case_queue[i];
              const blockUidSet = new Set(); // 用于存储当前块的账号信息
              for (let j = 0; j < block.length; j++) {
                const uid = block[j]?.uid || 0;
                // 检查用例是否指定客户端UID
                if (!uid) {
                  message(
                    `第 ${i + 1} 执行组中的第 ${j + 1} 个用例尚未指定客户端！ `,
                    {
                      type: "error"
                    }
                  );
                  this.shareState.saveLoading = false;
                  return;
                }
                // 检查账号是否重复
                if (blockUidSet.has(uid)) {
                  message(
                    `第 ${i + 1} 执行组中的第 ${
                      j + 1
                    } 个用例的客户端(ID: ${uid})重复使用，请修改！ `,
                    {
                      type: "error"
                    }
                  );
                  this.shareState.saveLoading = false;
                  return;
                }
                // 添加账号到当前块的账号集合
                blockUidSet.add(uid);
                // 设置块索引和块内索引
                const caseItem = block[j];
                caseItem.block_index = i; // 设置块索引
                caseItem.inner_index = j; // 设置块内索引
                // 计算总用例数
                totalCases++;
              }
            }

            // 更新的数据
            this.info.account_len = data.account_len;
            const postData = { ...this.info };

            if (totalCases === 0) {
              message("尚未在测试计划中添加用例！", { type: "warning" });
              this.shareState.saveLoading = false;
              return;
            }

            // 确认是否继续创建测试计划(只有在新建计划时才会弹出)
            if (!this.info.id) {
              await ElMessageBox.confirm(
                "测试计划一旦创建后无法再次编辑，确认继续？",
                "友情提示",
                {
                  confirmButtonText: "继续",
                  cancelButtonText: "取消",
                  type: "warning"
                }
              );
            }

            // 发送新建测试计划请求
            await superRequest({
              apiFunc: editPlan,
              apiParams: postData,
              enableSucceedMsg: true, // 启用成功提示
              onBeforeRequest: () => {
                this.shareState.saveLoading = true;
              },
              onSucceed: data => {
                // 更新测试计划id
                this.info.id = data?.id;
                // 执行成功回调
                typeof onSucceed === "function" && onSucceed(data);
              },
              onCompleted: () => {
                this.shareState.saveLoading = false;
              }
            });
          } catch (error) {
            console.error("editPlan error occurred:", error);
            this.shareState.saveLoading = false;
          }
        },
        onFailed: (data, msg) => {
          this.shareState.saveLoading = false;
          if (msg.includes("账号前缀已注册")) {
            ElMessage.error("账号前缀已注册，请重新生成");
          } else {
            ElMessageBox.alert(
              `您设置的账号长度超出输入范围<br>` +
                `规则：账号长度 = 前缀字符长度 + 执行人数单位长度<br>` +
                `即10 = 7【前缀字符长度】+ 3【执行人数 999】<br>`,
              {
                dangerouslyUseHTMLString: true,
                type: "error"
              }
            );
          }
        },
        onCompleted: () => {
          this.shareState.saveLoading = false;
        }
      });
    },

    async uploadFile(option: UploadRequestOptions) {
      const formData = new FormData();
      formData.append("local_file", option.file);
      formData.append("remote_file", "");
      formData.append("env", this.info.env);
      const fileName = option.file.name;
      await superRequest({
        apiFunc: fileUpload,
        apiParams: formData, // 修改这里
        enableSucceedMsg: true,
        succeedMsgContent: `上传【 ${fileName} 】至服务器成功 ！`,
        enableFailedMsg: true,
        onSucceed: data => {
          this.info.assign_account = data.url; //上传成功后，需要动态更新当前的文件路径
        }
      });
    }
  }
});

export function usePlanStoreHook() {
  return usePlanStore(store);
}
