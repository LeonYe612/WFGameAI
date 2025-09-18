import { defineStore } from "pinia";
import { store } from "@/store";
import { FormInstance } from "element-plus";
import md5 from "md5";
import { cloneDeep } from "@pureadmin/utils";
import {
  detailCase,
  versionCase,
  listStep,
  delStep,
  editStep,
  setStepSettings,
  detailStep,
  sortStep,
  editCase,
  upgradeCase,
  detailErrorCode,
  detailProto,
  listServer,
  listWorkerQueue
} from "@/api/testcase";
import { editPlan } from "@/api/plan";
// import { editPlan, implementPlan } from "@/api/plan";
// import { listPlanReports } from "@/api/report";
import { superRequest } from "@/utils/request";
import { message } from "@/utils/message";
import {
  envEnum,
  planTypeEnum,
  planRunTypeEnum,
  protoGenreEnum,
  protoTypeEnum,
  caseTypeEnum
} from "@/utils/enums";
import { v4 as uuidv4 } from "uuid";

/** 一些初始值 */
const defaultBaseInfo = () => {
  return {
    id: 0, // case_base 表中的id，也即页面传入的ID值
    version: 0,
    catalog_id: null,
    name: "",
    env: envEnum.TEST, // 1-测试环境 2-开发环境
    server_no: null,
    account: "",
    prefix: "",
    type: caseTypeEnum.COMMON.value,
    worker_queue: ""
  };
};

const defaultStep = () => {
  return {
    id: null, // 步骤ID
    case_base_id: null,
    name: "未命名用例",
    send_total: 0,
    recv_total: 0,
    send: [],
    recv: [],
    version: null,
    queue: 0,
    interval: 1000,
    times: 1
  };
};

export const useTestcaseStore = defineStore({
  id: "pure-testcase",
  state: () => ({
    // 版本控制选项
    versionOptions: [
      {
        label: "第 0 版",
        value: 0
      }
    ],
    // 服务器列表
    serverOptions: [],
    // 执行器列表
    workerQueueOptions: [],
    // 用例基础信息数据
    baseInfo: defaultBaseInfo(),
    // 用例步骤列表
    stepsList: [], // 用例步骤列表 item: defaultStep()
    // 用例步骤详情
    currentStep: defaultStep(),
    savingStatus: {},
    currentStepMd5: "",
    // 当前步骤选中索引值
    currentStepIndex: -1,
    // 当前选择的ProtoType： send / recv
    currentProtoType: protoGenreEnum.SEND.value,
    // 当前选择的Proto位于 send/ recv 下的索引值
    currentProtoIndex: -1,
    // 当前操作的 send 或者 recv 下的 ProtoInfo对象
    currentProto: null,
    // 协议选择器类型
    protoSelectorType: protoTypeEnum.REQUEST.value,
    // 用例相关的多个组件的共享状态
    shareState: {
      baseInfoFormLoading: false,
      baseInfoFormVisible: true,
      baseInfoSaveLoading: false,
      upgradeVersionLoading: false,
      stepSettingsVisible: false,
      openReportInNewTab: true,
      jsonParserStrictMode: false,
      // loadingRef
      debugButtonLoading: false, // 调试按钮点击时的loading
      stepListLoading: false, // 查询步骤列表时候的loading
      stepDetailLoading: false, // 查询步骤详情时候的loading
      stepAddLoading: false, // 添加步骤时候的loading
      stepSaveLoading: false,
      stepDelLoadings: {}, // 删除步骤时候的loading
      stepCopyLoadings: {}, // 拷贝步骤时候的loading
      // messageEditor 全局设置
      simpleMode: true
    },
    // 跨页面组件实例
    components: {
      //---------- Ref 绑定实例方式 --------------
      baseInfoFormRef: null,
      variablesEditorRef: null, // 变量表格组件实例
      protoContentDisplayerRef: null,
      protoSelectorRef: null,
      stepSelectorRef: null,
      exprEditorRef: null,
      //---------- v-model 双向绑定方式 ----------
      showDebugConfirmer: false,
      showPlanConfirmer: false,
      showCatalogDialog: false
    }
  }),
  actions: {
    /** 设置baseInfo中的信息 */
    SET_BASE_INFO(obj: object) {
      Object.keys(obj).forEach(key => {
        if (key in this.baseInfo) {
          this.baseInfo[key] = obj[key];
        }
      });
    },
    /** 重置baseInfo的信息 */
    RESET_BASE_INFO() {
      const emptyInfo = defaultBaseInfo();
      delete emptyInfo.id;
      delete emptyInfo.version;
      this.SET_BASE_INFO(emptyInfo);
    },
    RESET_VERSION_OPTIONS(version = 0) {
      this.versionOptions.splice(0, this.versionOptions.length);
      this.versionOptions.push({
        label: `第 ${version} 版`,
        value: version
      });
    },
    /** 设置当前步骤信息 */
    SET_CURRENT_STEP(obj: object) {
      Object.keys(obj).forEach(key => {
        if (key in this.currentStep) {
          this.currentStep[key] = obj[key];
        }
      });
    },
    /** 重置当前步骤信息 */
    RESET_CURRENT_STEP() {
      this.SET_CURRENT_STEP(defaultStep());
    },
    /** 清空STEP列表 */
    CLEAR_STEPS_LIST() {
      this.stepsList.splice(0, this.stepsList.length);
      this.RESET_CURRENT_STEP();
      this.currentStepIndex = -1;
    },
    /** 修改STEPS_LIST中指定index的Item */
    UPDATE_STEPS_LIST_ITEM(key: string, value: any, idx?: number) {
      idx = idx || this.currentStepIndex;
      if (idx >= 0 && this.stepsList[idx]) {
        if (key in this.stepsList[idx]) {
          this.stepsList[idx][key] = value;
        }
      }
    },
    /** 查询currentStep 中的send或recv 消息 */
    GET_CURRENT_STEP_MSG(type: string) {
      return this.currentStep[type];
    },
    /** 查询currentStep 中的send或recv 中指定索引的proto对象 */
    GET_CURRENT_PROTOINFO(type: string, index: number) {
      return this.currentStep[type]?.[index];
    },
    /** 设置currentStep 中的send或recv 消息 */
    SET_CURRENT_STEP_MSG(type: string, msg: any) {
      this.currentStep[type] = msg;
    },
    /** 添加currentStep 中的send或recv 消息 */
    ADD_CURRENT_STEP_MSG(type: string, msg: any) {
      this.addKeyForProtoData(msg.proto_data);
      // 如果当前步骤中没有该类型的消息，则初始化为空数组
      if (!this.currentStep[type]) {
        this.currentStep[type] = [];
      }
      this.currentStep[type].push(msg);
      // this.UPDATE_STEPS_LIST_ITEM(type, this.currentStep[type]);
      this.UPDATE_STEPS_LIST_ITEM(
        `${type}_total`,
        this.currentStep[type]?.length || 0
      );
    },
    /** 移除currentStep 中send或recv指定index的消息 */
    REMOVE_CURRENT_STEP_MSG(type: string, index: number) {
      this.currentStep[type].splice(index, 1);
      // this.UPDATE_STEPS_LIST_ITEM(type, this.currentStep[type]);
      this.UPDATE_STEPS_LIST_ITEM(
        `${type}_total`,
        this.currentStep[type]?.length || 0
      );
    },
    /** 生成currentStep-md5 */
    CURRENT_STEP_MD5() {
      // 生成除id字段以外的 currentStep 字段 MD5
      return md5(JSON.stringify(this.currentStep));
    },
    /** 生成currentStep-md5 */
    SET_VAR_TABLE_REF(ref) {
      this.varTableRef = ref;
    },
    /** 用例点击调试 */
    openPlanConfirmer() {
      this.components.showPlanConfirmer = true;
    },
    /** 用例点击调试 */
    openDebugConfirmer() {
      this.shareState.baseInfoFormVisible = true;
      this.components.showDebugConfirmer = true;
    },
    onBaseInfoEnvChanged(val: number) {
      this.baseInfo.env = val;
      this.baseInfo.server_no = null;
      this.serverOptions = [];
      this.fetchServerOptions(val);
    },
    /** 获取服务器列表 */
    async fetchServerOptions(env: number, checkServerNo = false) {
      const { data } = await superRequest({
        apiFunc: listServer,
        apiParams: {
          env
        }
      });
      if (!data) return;
      this.serverOptions = data;

      // 判断 info.server_no
      // a. 值为空 ==> 保持不变
      // b. 值不为空 ==> 判断是否存在，不存在则清空(用户必须重新选择)
      if (!checkServerNo) return;
      if (!this.baseInfo.server_no) {
        return;
      }
      const isExist = this.serverOptions.some(
        item => item.key === this.baseInfo.server_no
      );
      if (!isExist) {
        this.baseInfo.server_no = "";
      }
    },
    /** 获取任务执行器列表 */
    async fetchWorkerQueueOptions() {
      const { data } = await superRequest({
        apiFunc: listWorkerQueue
      });
      if (!data) {
        this.workerQueueOptions = [];
        return;
      }

      this.workerQueueOptions = [...data];
      // 判断 info.worker_queue
      // a. 值为空 ==> 默认选中第一个
      // b. 值不为空 ==> 判断是否存在，不存在则清空(用户必须重新选择)
      if (!this.baseInfo.worker_queue) {
        this.baseInfo.worker_queue = this.workerQueueOptions[0]?.key || "";
      } else {
        const isExist = this.workerQueueOptions.some(
          item => item.key === this.baseInfo.worker_queue
        );
        if (!isExist) {
          this.baseInfo.worker_queue = "";
        }
      }
    },
    async debug(func: Function) {
      /**
       * 点击调试：就是默认创建 debug类型 & 立即执行 的测试计划
       * 后台根据新建的测试计划，会自动创建对应的 TaskObj 和 ResultObj
       */
      if (!this.baseInfo.worker_queue) {
        return message("请选择任务执行器！", { type: "warning" });
      }
      // 保存当前用例基础信息
      await this.saveBaseInfo(null, false);
      // 如果当前有激活步骤，先保存当前步骤
      if (this.currentStep.id && this.currentStep.case_base_id) {
        await this.saveStep();
      }

      // step1. 构造新建 Plan 必须的数据
      const postData = {
        id: null,
        name: this.baseInfo.name,
        env: this.baseInfo.env,
        server_no: this.baseInfo.server_no,
        account: this.baseInfo.account,
        prefix: this.baseInfo.prefix,
        case_base_id: this.baseInfo.id,
        case_version: this.baseInfo.version,
        worker_queue: this.baseInfo.worker_queue,
        plan_type: planTypeEnum.DEBUG.value,
        run_type: planRunTypeEnum.DEBUG.value, // 1: 调试-DEBUG 2: 单次-SINGLE 3: 定时-SCHEDULE 4: 周期-CIRCLE
        run_info: {
          schedule: null, // 定时执行类型：只需要采集一个日期时间即可。示例："2021-01-01 12:00:00"
          circle: {
            // 周期执行类型：需要采集一个日期范围，指定一周的哪些天，一个运行时间
            date_range: ["", ""], // 周期运行的日期范围，示例：["2021-01-01 00:00:00", "2021-01-31 23:59:59"]
            which_days: [], // 在一周的哪些天执行, 示例: [1, 2, 4, 7]
            run_time: "" // 运行时间, 示例："12:00:00"
          }
        },
        // inform: testcaseStore.baseInfo,
        // case_queue 中只编排当前测试用例
        case_queue: [
          {
            case_base_id: this.baseInfo.id,
            version: this.baseInfo.version,
            name: this.baseInfo.name
          }
        ]
      };
      // step2. 请求创建计划API，并尝试跳转到Debug报告页面中
      await superRequest({
        apiFunc: editPlan,
        apiParams: postData,
        enableSucceedMsg: false,
        onBeforeRequest: () => {
          this.shareState.debugButtonLoading = true;
        },
        onSucceed: data => {
          this.shareState.debugButtonLoading = false;
          // data 返回中的 latest_result_id 为新建的报告ID
          const reportId = data.latest_result_id || 0;
          if (!reportId) {
            return message(`生成测试报告失败！`, { type: "error" });
          } else {
            typeof func === "function" && func(reportId);
          }
        },
        onFailed: () => {
          this.shareState.debugButtonLoading = false;
        }
      });
    },
    /** 用例版本升级 */
    async upgradeVersion(version: number, onSucceed?: Function) {
      // 基于传递的 version 版本进行升级
      await superRequest({
        apiFunc: upgradeCase,
        apiParams: { id: this.baseInfo.id, version: version },
        onBeforeRequest: () => {
          this.shareState.upgradeVersionLoading = true;
        },
        onSucceed: (data: any) => {
          typeof onSucceed === "function" &&
            onSucceed({ id: this.baseInfo.id, version: data.version });
        },
        onCompleted: () => {
          this.shareState.upgradeVersionLoading = false;
        }
      });
    },
    /** 获取用例版本列表 */
    async fetchVersionOptions() {
      const case_base_id = this.baseInfo.id;
      await superRequest({
        apiFunc: versionCase,
        apiParams: { id: case_base_id },
        onBeforeRequest: () => {
          // 先清空
          this.versionOptions.splice(0, this.versionOptions.length);
        },
        onSucceed: (data: any) => {
          if (data?.length) {
            // 版本号从大到小排序
            data.sort((a, b) => b - a);
            data.forEach(version => {
              this.versionOptions.push({
                label: `第 ${version} 版`,
                value: version
              });
            });
          }
        }
      });
    },
    /** 获取用例基本信息 */
    async fetchBaseInfo() {
      this.RESET_BASE_INFO();
      this.RESET_VERSION_OPTIONS();
      const case_base_id = this.baseInfo.id;
      this.currentStepMd5 = "";
      // 如果是新增用例，无需按照ID查询用例详情信息
      if (!case_base_id) return;
      await superRequest({
        apiFunc: detailCase,
        apiParams: { id: case_base_id, version: this.baseInfo.version },
        onBeforeRequest: () => {
          this.shareState.baseInfoFormLoading = true;
          this.fetchVersionOptions();
        },
        onSucceed: (data: any) => {
          data.id = data.parent_id;
          this.SET_BASE_INFO(data);
        },
        onCompleted: () => {
          this.shareState.baseInfoFormLoading = false;
        }
      });
    },
    /** 保存用例基本信息 */
    async saveBaseInfo(
      formEl: FormInstance | undefined | null,
      enableValidate = true
    ) {
      // step1. 默认开启表单Validate 验证表单数据
      if (!formEl && enableValidate) {
        formEl = this.components.baseInfoFormRef?.formRef as FormInstance;
        if (!formEl) {
          message("未找到测试用例表单组件，请检查！");
          return;
        }
      }
      // step2. 验证表单数据
      if (enableValidate) {
        const isValid = await formEl.validate();
        if (!isValid) {
          return;
        }
      }
      // step3. 保存用例基本信息
      superRequest({
        apiFunc: editCase,
        apiParams: { ...this.baseInfo },
        enableSucceedMsg: true,
        succeedMsgContent: "用例保存成功！",
        onBeforeRequest: () => {
          this.shareState.baseInfoSaveLoading = true;
        },
        onSucceed: (data: any) => {
          const isNewCase = !this.baseInfo.id;
          // 新增或编辑后，从响应结果里更新
          this.baseInfo.id = data.parent_id;
          this.baseInfo.version = data.version;
          if (isNewCase) {
            this.fetchStepsList();
            this.RESET_VERSION_OPTIONS(1);
          }
        },
        onCompleted: () => {
          this.shareState.baseInfoSaveLoading = false;
        }
      });
    },
    /** 获取用例步骤列表 */
    async fetchStepsList() {
      this.CLEAR_STEPS_LIST();
      const case_base_id = this.baseInfo.id;
      const version = this.baseInfo.version;
      if (!case_base_id) return;
      await superRequest({
        apiFunc: listStep,
        apiParams: { case_base_id, version },
        onBeforeRequest: () => {
          this.shareState.stepListLoading = true;
        },
        onSucceed: (data: any) => {
          const stepsList = data.list || [];
          stepsList.forEach(step => this.stepsList.push(step));
        },
        onCompleted: () => {
          this.shareState.stepListLoading = false;
          this.RESET_CURRENT_STEP();
          this.currentProtoIndex = -1;
        }
      });
    },
    /** 获取用例步骤详情 */
    async fetchStepDetail(stepId: number) {
      await superRequest({
        apiFunc: detailStep,
        apiParams: { id: stepId },
        onBeforeRequest: () => {
          this.shareState.stepDetailLoading = true;
        },
        onSucceed: (data: any) => {
          // todo：测试方便，删除Detail返回的id，不执行记录
          // delete data.id;
          this.formatStepDetailBeforeRender(data);
          this.SET_CURRENT_STEP(data);
        },
        onCompleted: res => {
          this.shareState.stepDetailLoading = false;
          if (res.code !== 0) {
            // 失败或出错时需要重置当前步骤
            this.RESET_CURRENT_STEP();
          }
        }
      });
    },
    /** 查询完API：步骤详情(detailStep)，对返回data进行格式化后再绑定渲染 */
    formatStepDetailBeforeRender(stepData: any) {
      const send = stepData?.send || [];
      const recv = stepData?.recv || [];
      send.forEach(proto => {
        this.addKeyForProtoData(proto.proto_data);
      });
      recv.forEach(proto => {
        this.addKeyForProtoData(proto.proto_data);
      });
    },
    addKeyForProtoData(protoData: Array<any>) {
      if (protoData?.length > 0) {
        for (let i = 0; i < protoData?.length; i++) {
          protoData[i].key = this.uniqueId();
          if (protoData[i]?.children?.length) {
            this.addKeyForProtoData(protoData[i].children);
          }
        }
      }
    },
    // 保存前清除每个ProtoDataItem中的key，为后端数据库存储节省空间
    removeKeyForStep(step: any) {
      const props = [protoGenreEnum.SEND.value, protoGenreEnum.RECV.value];
      props.forEach(prop => {
        if (step?.[prop]?.length > 0) {
          step[prop].forEach(protoData => {
            this.removeKeyInProtoData(protoData.proto_data);
          });
        }
      });
    },
    removeKeyInProtoData(protoData: Array<any>) {
      if (protoData?.length > 0) {
        for (let i = 0; i < protoData.length; i++) {
          delete protoData[i].key;
          this.removeKeyInProtoData(protoData[i].children);
        }
      }
    },
    /** 激活选中某个用例步骤 */
    async activeStep(index: number, isNewStep?: boolean, newStep?: any) {
      // 隐藏信息录入侧边栏
      if (this.shareState.baseInfoFormVisible) {
        this.shareState.baseInfoFormVisible = false;
      }
      // ======= 激活(高亮显示)某个测试用例步骤【前】 ========
      // 记录当前步骤选中的类型(send/recv) 和选中的索引(index)
      const oldStepIndex = this.currentStepIndex;
      if (oldStepIndex !== -1) {
        this.stepsList[oldStepIndex].lastProtoType = this.currentProtoType;
        this.stepsList[oldStepIndex].lastProtoIndex = this.currentProtoIndex;
        this.currentProtoIndex = -1;
      }
      // 尝试对上一个处于激活状态的测试用例步骤进行自动保存
      if (this.currentStepMd5 !== "" && this.currentStepIndex !== -1) {
        const currMd5 = this.CURRENT_STEP_MD5();
        // console.log(`当前md5: ${currMd5}| 记录md5: ${this.currentStepMd5}`);
        if (currMd5 !== this.currentStepMd5) {
          // console.log("检测到上个步骤有修改，正在执行自动保存...");
          const step = cloneDeep(this.currentStep);
          this.saveStep({ step });
        }
      } // 为空时，说明为第一次激活某个步骤 => 无需保存
      // =================================================
      // 页面上根据id判断是否选中，先进行激活显示
      this.SET_CURRENT_STEP({ id: this.stepsList[index].id });
      this.currentStepIndex = index;
      // ======= 激活(高亮显示)某个测试用例步骤【后】 ========
      // 需要记录 currentStep 的初始md5值
      if (isNewStep) {
        // a. 新增步骤时候，无需查询api获取步骤详细信息
        this.SET_CURRENT_STEP(newStep);
      } else {
        // b. 非新增步骤，需要查询步骤详情信息并赋值给 currentStep
        await this.fetchStepDetail(this.stepsList[index].id);
      }
      this.autoActiveProto(index);
      this.currentStepMd5 = this.CURRENT_STEP_MD5();
    },
    /** 新增用例步骤 */
    async addStep(props: { onSucceed: Function }) {
      const case_base_id = this.baseInfo.id;
      const newStep = defaultStep();
      newStep.case_base_id = case_base_id;
      newStep.version = this.baseInfo.version;
      // 2025-06-04 修改逻辑
      // a. 当前有激活步骤，新增步骤插入到当前步骤的后面
      // b. 当前没有激活步骤，新增步骤插入到步骤列表的最后
      const currIdx =
        this.currentStepIndex >= 0
          ? this.currentStepIndex
          : this.stepsList.length - 1;
      await superRequest({
        apiFunc: editStep,
        apiParams: newStep,
        enableSucceedMsg: true,
        onBeforeRequest: () => {
          this.shareState.stepAddLoading = true;
        },
        onSucceed: (data: any) => {
          newStep.id = data.id;
          // this.stepsList.push(newStep);
          // this.activeStep(this.stepsList.length - 1, true, newStep);
          // 2025-06-04 修改逻辑
          this.stepsList.splice(currIdx + 1, 0, newStep);
          this.activeStep(currIdx + 1, true, newStep);
          // 更新排序
          this.sortStep();
          typeof props.onSucceed === "function" && props.onSucceed();
        },
        onCompleted: () => {
          this.shareState.stepAddLoading = false;
        }
      });
    },
    /** 将protoInfo中的变量替换为新的key */
    updateVariablesKey(respProto: any) {
      if (!respProto?.variables) return;
      Object.keys(respProto.variables).forEach(varName => {
        respProto.variables[varName].key = this.uniqueId();
      });
    },
    /** 拷贝用例步骤 */
    async copyStep(props: { stepId: number; onSucceed: Function }) {
      // step1. 拷贝步骤如果是当前步骤，需要先保存当前步骤
      if (this.currentStep.id == props.stepId) {
        await this.saveStep();
      }
      // step2. 查询待拷贝的步骤详情
      const detailResp = await superRequest({
        apiFunc: detailStep,
        apiParams: { id: props.stepId },
        onBeforeRequest: () => {
          this.shareState.stepCopyLoadings[props.stepId] = true;
        }
      });
      if (!detailResp?.data) {
        delete this.shareState.stepCopyLoadings[props.stepId];
        return;
      }
      // step3. 根据详情信息创建一个新步骤
      const data = detailResp.data;
      delete data.id;
      const newStep = cloneDeep(data);
      // 这里重新赋值的含义：导入步骤/拷贝步骤 都是相对当前的 case_base_id 操作
      newStep.case_base_id = this.baseInfo.id;
      const currIdx =
        this.currentStepIndex >= 0
          ? this.currentStepIndex
          : this.stepsList.length - 1;
      // newStep.queue = this.stepsList.length || 0;

      /**
       * 拷贝的目标步骤需要针对自定义变量处理下
       * 尝试将recv下的多个protoInfo.variables中的key替换为新key
       * 否则多个变量的key就相同了
       */
      if (newStep?.recv?.length) {
        for (let i = 0; i < newStep.recv.length; i++) {
          this.updateVariablesKey(newStep.recv[i]);
        }
      }
      // step4. 调用保存接口
      const editResp = await superRequest({
        apiFunc: editStep,
        apiParams: newStep,
        enableSucceedMsg: false
      });
      if (!editResp?.data) {
        delete this.shareState.stepCopyLoadings[props.stepId];
        return;
      }
      // c. 渲染显示
      newStep.id = editResp.data.id;
      newStep.send_total = editResp.data?.send?.length || 0;
      newStep.recv_total = editResp.data?.recv?.length || 0;

      // this.stepsList.push(newStep);
      // this.activeStep(this.stepsList.length - 1);
      // 2025-06-04 修改逻辑
      this.stepsList.splice(currIdx + 1, 0, newStep);
      this.activeStep(currIdx + 1);

      typeof props.onSucceed === "function" && props.onSucceed();
      delete this.shareState.stepCopyLoadings[props.stepId];
    },
    /** 删除用例步骤 */
    async delStep(index: number) {
      const step: any = this.stepsList[index];
      const stepId = step.id;
      await superRequest({
        apiFunc: delStep,
        apiParams: { id: stepId },
        enableSucceedMsg: true,
        onBeforeRequest: () => {
          this.shareState.stepDelLoadings[stepId] = true;
        },
        onSucceed: () => {
          // 从列表中删除
          this.stepsList.splice(index, 1);
          // 如果删除的是当前步骤，则清空当前步骤
          if (stepId === this.currentStep.id) {
            this.RESET_CURRENT_STEP();
            this.currentStepIndex = -1;
          } else if (index > this.currentStepIndex) {
            // 啥也不用做
          } else if (index < this.currentStepIndex) {
            this.currentStepIndex--;
          }
        },
        onCompleted: () => {
          delete this.shareState.stepDelLoadings[stepId];
        }
      });
    },
    /** 定位当前步骤在哪里 */
    locateCurrentStep() {
      const currentStepId = this.currentStep.id;
      if (!currentStepId) {
        this.currentStepIndex = -1;
        return;
      }
      this.currentStepIndex = this.stepsList.findIndex(
        step => step.id === currentStepId
      );
    },
    /** 用例步骤排序 */
    async sortStep() {
      // 定位当前步骤在哪里，重新赋值：currentStepIndex
      this.locateCurrentStep();
      // 遍历stepsList，更新每个步骤的index
      const sortData = this.stepsList.map(step => {
        return step.id;
      });
      await superRequest({
        apiFunc: sortStep,
        apiParams: { sort: sortData }
      });
    },
    /** 保存步骤运行设置 */
    async saveStepSettings(step: any) {
      await superRequest({
        apiFunc: setStepSettings,
        apiParams: {
          id: step.id,
          interval: step.interval || 0,
          times: step?.times || 1,
          is_pre: step?.is_pre || false
        }
      });
    },
    /** 保存用例步骤 */
    // 传递 step 时，依据 step参数保存
    // 未传递时，默认使用 this.currentStep 保存
    async saveStep(props?: { onSucceed?: Function; step?: any }) {
      const stepData = props?.step ? props.step : this.currentStep;
      const stepId = stepData.id;
      const postData = cloneDeep(stepData);
      this.removeKeyForStep(postData);
      await superRequest({
        apiFunc: editStep,
        apiParams: { ...postData, version: this.baseInfo.version },
        enableSucceedMsg: false,
        onBeforeRequest: () => {
          this.shareState.stepSaveLoading = true;
          this.savingStatus[stepId] = true;
        },
        onSucceed: (data: any) => {
          // 如果是当前步骤发生保存，更新md5
          if (!props?.step) {
            this.currentStepMd5 = this.CURRENT_STEP_MD5();
          }
          typeof props?.onSucceed === "function" && props?.onSucceed(data);
        },
        onCompleted: () => {
          this.shareState.stepSaveLoading = false;
          setTimeout(() => {
            delete this.savingStatus[stepId];
          }, 500);
        }
      });
    },
    activeProto(protoGenre: string, protoIndex: number) {
      this.currentProtoType = protoGenre;
      this.currentProtoIndex = protoIndex;
    },
    /** 自动判断并激活协议选择 */
    autoActiveProto(newStepIndex: number) {
      // a. 尝试寻找记忆的协议类型和索引
      if (this.stepsList[newStepIndex]?.lastProtoType) {
        const protoGenre = this.stepsList[newStepIndex].lastProtoType;
        const protoIndex = this.stepsList[newStepIndex].lastProtoIndex;
        this.activeProto(protoGenre, protoIndex);
        return;
      }
      // b. 找不到的话，尝试选中send[0]
      if (this.currentStep?.send?.length) {
        this.activeProto(protoGenreEnum.SEND.value, 0);
        return;
      }
      // c. 找不到的话，尝试选中recv[0]
      if (this.currentStep?.recv?.length) {
        this.activeProto(protoGenreEnum.RECV.value, 0);
        return;
      }
      // d. 啥也找不到
      this.activeProto(protoGenreEnum.SEND.value, -1);
    },
    /** 打开用例步骤选择器 */
    showStepSelector() {
      // return message("功能即将上线！", { type: "warning" });
      this.components.stepSelectorRef?.show(this.baseInfo.env);
    },
    /** 用例步骤选择器选择完成后,根据选择的用例步骤添加到步骤列表中 */
    async handleStepSelectorComplete(steps: any) {
      if (!steps || steps.length === 0) return;
      try {
        this.shareState.stepListLoading = true;
        for (let i = 0; i < steps.length; i++) {
          await this.copyStep({ stepId: steps[i].id });
        }
        await this.sortStep();
      } catch (error) {
        message(`导入用例步骤出错: ${error}`, { type: "error" });
      } finally {
        this.shareState.stepListLoading = false;
      }
    },
    /** 协议选择完成后, 根据选择的结果查询协议详情并添加到 Current step 中 */
    async handleProtoSelectorComplete(protos: any) {
      if (!protos || protos.length === 0) return;
      const protoGenre =
        this.protoSelectorType === protoTypeEnum.REQUEST.value
          ? protoGenreEnum.SEND.value
          : protoGenreEnum.RECV.value;
      try {
        this.shareState.stepDetailLoading = true;
        for (let i = 0; i < protos.length; i++) {
          await superRequest({
            apiFunc: detailProto,
            apiParams: { id: protos[i].id },
            onSucceed: protoInfo => {
              this.ADD_CURRENT_STEP_MSG(protoGenre, protoInfo);
              // 如果是 protoGenreEnum.SEND.value 类型，将当前步骤名称设置为第一个协议名称
              if (protoGenre === protoGenreEnum.SEND.value) {
                this.currentStep.name = protoInfo?.proto_name || "未命名步骤";
                this.UPDATE_STEPS_LIST_ITEM("name", this.currentStep.name);
              }
            }
          });
        }
        // Proto 激活状态变更
        this.currentProtoType = protoGenre;
        const currGenreLength = this.currentStep?.[protoGenre]?.length || 0;
        this.currentProtoIndex = currGenreLength - 1;
      } catch (error) {
        message(`查询协议详情出错: ${error}`, { type: "error" });
      } finally {
        this.shareState.stepDetailLoading = false;
      }
    },
    /**从 Current step 的指定类型(send/recv)中移除指定索引的 protoInfo */
    async handleRemoveProtoInCurrentStep(
      protoType: string,
      protoIndex: number
    ) {
      // a. 执行删除
      this.REMOVE_CURRENT_STEP_MSG(protoType, protoIndex);
      // b. 刷新选中态
      // b-1. 操作另一类型，无需变更
      if (protoType !== this.currentProtoType) {
        return;
      }
      // b-2. 操作同一类型
      let newIndex: number;
      const currGenreLength = this.currentStep?.[protoType]?.length || 0;
      if (protoIndex === this.currentProtoIndex) {
        newIndex = -1;
      } else if (protoIndex < this.currentProtoIndex) {
        newIndex = this.currentProtoIndex - 1;
      } else if (protoIndex > this.currentProtoIndex) {
        newIndex = this.currentProtoIndex;
      }
      this.currentProtoIndex =
        newIndex >= -1 && newIndex <= currGenreLength - 1 ? newIndex : -1;
    },
    /**参数类型判断 */
    isProto3BasicType(type: string) {
      // Proto3 中的所有类型
      const proto3BasicTypes = {
        double: true,
        float: true,
        int32: true,
        int64: true,
        uint32: true,
        uint64: true,
        sint32: true,
        sint64: true,
        fixed32: true,
        fixed64: true,
        sfixed32: true,
        sfixed64: true,
        bool: true,
        string: true,
        bytes: true
      };
      return !!proto3BasicTypes[type.toLowerCase()];
    },
    /**生成唯一ID */
    uniqueId() {
      return uuidv4();
    },
    /**在ProtoData中查找指定 rowKey的path */
    findDescriptionPathOld(protoData: any, key: string, path = []) {
      for (let i = 0; i < protoData.length; i++) {
        const item = protoData[i];
        if (item.key === key) {
          return [...path, item.field];
        }
        if (item.children) {
          const newPath =
            item.modifier === "item"
              ? [...path, i.toString()]
              : [...path, item.field];
          const result = this.findDescriptionPathOld(
            item.children,
            key,
            newPath
          );
          if (result) {
            return result;
          }
        }
      }
      return null;
    },
    /**在ProtoData中查找指定 rowKey的path */
    findDescriptionPathString(
      protoData: any,
      key: string,
      parentLocation: string
    ) {
      for (let i = 0; i < protoData.length; i++) {
        const item = protoData[i];
        let location = parentLocation;
        const currPath: string =
          item.modifier === "item" ? i.toString() : item.field;
        // 首个路径特殊处理
        location = location ? `${location}/${currPath}` : currPath;
        if (item.key === key) {
          return location;
        }
        if (item.children?.length > 0) {
          const path = this.findDescriptionPathString(
            item.children,
            key,
            location
          );
          if (path) {
            return path;
          }
        }
      }
      return "";
    },
    /** 尝试删除当前激活步骤中指定key的variable */
    tryDeleteCurrentStepVariable(varKey: string) {
      const sendProtos = this.GET_CURRENT_STEP_MSG(protoGenreEnum.SEND.value);
      const recvProtos = this.GET_CURRENT_STEP_MSG(protoGenreEnum.RECV.value);
      if (sendProtos?.length) {
        for (let i = 0; i < sendProtos.length; i++) {
          const sendProto = sendProtos[i];
          if (!sendProto?.variables) continue;
          Object.keys(sendProto.variables).forEach(varName => {
            if (sendProto?.variables[varName]?.key === varKey) {
              delete sendProto.variables[varName];
            }
          });
        }
      }
      if (recvProtos?.length) {
        for (let i = 0; i < recvProtos.length; i++) {
          const recvProto = recvProtos[i];
          if (!recvProto?.variables) continue;
          Object.keys(recvProto.variables).forEach(varName => {
            if (recvProto?.variables[varName]?.key === varKey) {
              delete recvProto.variables[varName];
            }
          });
        }
      }
    },
    /** 尝试删除当前激活协议中指定key的variable */
    tryDeleteCurrentProtoVariable(varKey: string) {
      if (!this.currentProto?.variables) return;
      Object.keys(this.currentProto.variables).forEach(varName => {
        if (this.currentProto?.variables[varName]?.key === varKey) {
          delete this.currentProto?.variables[varName];
        }
      });
    },
    /** 尝试更新当前协议中引用key变量的变量名 */
    tryUpdateCurrentProtoReferFields(
      varKey: string,
      newName: string,
      clearReferKey = false
    ) {
      if (!this.currentProto?.references) return;
      const locations = [];
      Object.keys(this.currentProto.references).forEach(location => {
        if (this.currentProto.references[location] == varKey) {
          locations.push(location);
        }
      });
      if (locations?.length <= 0) return;
      // 递归遍历所有参数，根据参数的refer_key去修改
      this.updateItemReferFields(
        this.currentProto.proto_data,
        varKey,
        newName,
        clearReferKey
      );
    },
    /** 尝试更新当前步骤中引用key变量的变量名 */
    tryUpdateCurrentStepReferFields(
      varKey: string,
      newName: string,
      clearReferKey = false
    ) {
      const sendProtos = this.GET_CURRENT_STEP_MSG(protoGenreEnum.SEND.value);
      const proto = sendProtos?.[0];
      if (!proto) return;
      const locations = [];
      if (!proto?.references) return;
      Object.keys(proto?.references).forEach(location => {
        if (proto.references[location] == varKey) {
          locations.push(location);
        }
      });
      if (locations?.length <= 0) return;
      // 递归遍历所有参数，根据参数的refer_key去修改
      this.updateItemReferFields(
        proto.proto_data,
        varKey,
        newName,
        clearReferKey
      );
    },
    updateItemReferFields(
      protoData: Array<any>,
      varKey: string,
      newName: string,
      clearReferKey = false
    ) {
      if (protoData?.length > 0) {
        for (let i = 0; i < protoData.length; i++) {
          if (protoData[i].refer_key == varKey) {
            protoData[i].refer_name = newName;
            if (clearReferKey) {
              protoData[i].refer_key = "";
            }
          }
          if (protoData[i]?.children?.length) {
            this.updateItemReferFields(
              protoData[i].children,
              varKey,
              newName,
              clearReferKey
            );
          }
        }
      }
    },
    /** 查询CodeDesc */
    async getCodeDesc(props?: {
      onSucceed?: Function;
      env: any;
      code: number;
    }) {
      await superRequest({
        apiFunc: detailErrorCode,
        apiParams: {
          env: props.env,
          keyword: `${props.code}`
        },
        enableSucceedMsg: false,
        onSucceed: (data: any) => {
          const codeDesc = data?.desc || "未知的错误码";
          typeof props?.onSucceed === "function" && props?.onSucceed(codeDesc);
        }
      });
    },
    /** 通用方法： 设置 proto.proto_data
     单个参数的delelted字段的值: true | false
     */
    setProtoDataItemDeletedValue(item, deletedVal: boolean) {
      item.deleted = deletedVal;
      if (item?.children?.length) {
        item.children.forEach(element => {
          this.setProtoDataItemDeletedValue(element, deletedVal);
        });
      }
    },
    /** 通用方法： 设置 proto.proto_data
     所有参数的delelted字段的值: true | false
     */
    setAllProtoDataItemDeletedValue(protoData, deletedVal: boolean) {
      if (protoData?.length) {
        protoData.forEach(element => {
          this.setProtoDataItemDeletedValue(element, deletedVal);
        });
      }
    },
    // ======================== 使用 Virtual Tree 的新方法 ====================
    /**
     * 遍历树节点
     */
    traverseTreeNode(
      treeNodes: any[],
      callback: (node: any, parent: any | undefined) => void,
      parent: any | undefined = undefined
    ) {
      for (const node of treeNodes) {
        callback(node, parent);
        if (!node.isLeaf) {
          this.traverseTreeNode(node.children, callback, node);
        }
      }
    },
    /**
     * 遍历树节点对应的data(也就是ProtoDataItem对象)
     */
    traverseTreeNodeData(
      nodeDatas: any[],
      callback: (nodeData: any, parentData: any | undefined) => void,
      parentData: any | undefined = undefined
    ) {
      for (const nodeData of nodeDatas) {
        callback(nodeData, parentData);
        if (nodeData?.children?.length) {
          this.traverseTreeNodeData(nodeData.children, callback, nodeData);
        }
      }
    },
    /**
     * 获取指定树节点的location描述
     */
    getNodeLocation(node: any): string {
      const paths: string[] = [];
      try {
        while (node?.parent) {
          // 非数组类型
          let path = node.data.field;
          // 数组类型
          if (node?.data?.modifier === "item") {
            path = node.parent.children.indexOf(node).toString();
          }
          paths.push(path);
          node = node.parent;
        }
        // 添加根节点
        paths.push(node.data.field);
        return paths.reverse().join("/");
      } catch (error) {
        console.error("[Error] getNodeLocation: ", error);
        return "";
      }
    },
    /**
     * 获取指定树节点存储的自定义变量的key
     */
    getNodeVariableKey(node: any): string {
      const location = this.getNodeLocation(node);
      if (!this.currentProto?.variables) {
        return "";
      }

      for (const varName in this.currentProto.variables) {
        const varObject = this.currentProto.variables[varName];
        if (varObject?.location === location) {
          return varObject?.key;
        }
      }

      return "";
    }
  }
});
export function useTestcaseStoreHook() {
  return useTestcaseStore(store);
}
