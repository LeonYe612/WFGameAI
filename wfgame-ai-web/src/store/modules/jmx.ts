import { defineStore } from "pinia";
import { store } from "@/store";
import { ElNotification, UploadRequestOptions } from "element-plus";
import { superRequest } from "@/utils/request";
import { fileUpload } from "@/api/file";
import { remoteServerList } from "@/api/server";
import {
  planTypeEnum,
  envEnum,
  planRunTypeEnum,
  planInformEnum,
  getLabel
} from "@/utils/enums";
import { jmxContentApi } from "@/api/jmx";
import { message } from "@/utils/message";
import { formatTimestamp } from "@/utils/time";
import { assetItem } from "../types";
import { editPlan } from "@/api/plan";
import { listWorkerQueue } from "@/api/testcase";
import { ossUploadText } from "@/api/oss";

// import { message } from "@/utils/message";
// import { ref } from "vue";
// import { cloneDeep } from "@pureadmin/utils";

/** 表单初始值 */
const defaultFormData = () => {
  return {
    id: null,
    name: "",
    env: envEnum.TEST, // 环境
    worker_queue: "",
    plan_type: planTypeEnum.JMX.value, // 计划类型
    run_type: planRunTypeEnum.SINGLE.value,
    run_info: {
      schedule: null, // 定时执行类型：只需要采集一个日期时间即可。示例："2021-01-01 12:00:00"
      circle: {
        // 周期执行类型：需要采集一个日期范围，指定一周的哪些天，一个运行时间
        date_range: ["", ""], // 周期运行的日期范围，示例：["2021-01-01 00:00:00", "2021-01-31 23:59:59"]
        which_days: [], // 在一周的哪些天执行, 示例: [1, 2, 4, 7]
        run_time: "" // 运行时间, 示例："12:00:00"
      }
    },
    inform: planInformEnum.DISABLE.value, // 计划结果推送设置
    case_queue: null
  };
};

export const useJmxStore = defineStore({
  id: "pure-jmx",
  state: () => ({
    jmxConfig: {
      base_url: "",
      project_path: "",
      default_ref: "",
      token: ""
    },
    runParams: {
      server: "", // 执行Jmeter的服务器IP
      ref: "", // 分支
      command: "", // 执行命令
      jmx: {
        name: "",
        url: ""
      } as assetItem, // JMX 文件路径
      assets: [] as assetItem[] // 已选依赖文件
    },
    formData: defaultFormData(),
    // =========== 组件属性 ============
    bucket: "jmx", // OSS 桶名称
    jmxParamsDialog: {
      visible: false
    },
    jmxEditor: {
      ref: null, // 组件实例
      loading: false,
      content: "", // JMX 文件内容
      xmlObj: null // JMX XML 对象
    },
    // ============ 页面选项 ============
    serverOptions: [], // JMX 服务器选项
    assetsOptions: [] as assetItem[], // 其他依赖文件
    workerQueueOptions: [] as any[], // 执行器队列选项
    // 相关组件间的共享状态值
    shareState: {}
  }),
  actions: {
    /**
     * resetRunParams
     * 重置运行参数
     * @returns {void}
     */
    resetRunParams() {
      this.runParams.server = "";
      this.runParams.ref = this.jmxConfig.default_ref || "";
      this.runParams.command = "";
      this.runParams.jmx.name = "";
      this.runParams.jmx.url = "";
      this.runParams.assets = [];
    },

    // 查询执行器列表选项
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
      if (!this.formData.worker_queue) {
        this.formData.worker_queue = this.workerQueueOptions[0]?.key || "";
      } else {
        const isExist = this.workerQueueOptions.some(
          item => item.key === this.formData.worker_queue
        );
        if (!isExist) {
          this.formData.worker_queue = "";
        }
      }
    },

    /**
     * GenGitFileRawUrl
     * https://git.wanfeng-inc.com/playmore-test/playmore-jmx/-/raw/main/liwei/%E5%9B%BD%E5%86%85%E6%B8%B8%E6%88%8F1.jmx
     * */
    genGitFileRawUrl(ref: string, filePath: string) {
      const { base_url, project_path } = this.jmxConfig;
      return `${base_url}/${project_path}/-/raw/${ref}/${filePath}`;
    },

    /**
     * randomJmxPlanName
     * 生成随机 JMX 计划名称
     * 重置表单数据
     */
    randomJmxPlanName() {
      const label = getLabel(planTypeEnum, this.formData.plan_type);
      const dateStr = formatTimestamp(Date.now());
      const randomSuffix = Math.floor(Math.random() * 9000 + 1000); // 1000-9999之间的随机数
      const randomName = `${label}_${dateStr}_${randomSuffix}`;
      this.formData.name = randomName;
    },

    /**
     * parseJmxAssets
     * 解析 JMX 文件中的依赖资源
     */
    parseJmxAssets(): boolean {
      if (!this.jmxEditor.ref) return false;
      const treeData = this.jmxEditor.ref.treeData || [];
      const filenames = this.jmxEditor.ref.collectEnabledFilenames(treeData);
      console.log("解析到的 JMX 依赖文件:", filenames);
      // 尝试在 assetsOptions 中查找已存在的资源并更新 runParams.assets
      const requiredAssets = [];
      for (const asset of filenames) {
        const existingAsset = this.assetsOptions.find(
          item => item.name === asset
        );
        if (existingAsset) {
          requiredAssets.push(existingAsset);
        } else {
          // 如果不存在，需要报错
          message(`${this.runParams.jmx.name} 同级目录下未找到文件: ${asset}`, {
            type: "error"
          });
          return false; // 停止执行，避免使用未定义的资源
        }
      }
      this.runParams.assets = requiredAssets;
      return true;
    },

    /**
     * refreshServerOptions
     * 获取 JMX 服务器选项
     */
    async refreshServerOptions() {
      superRequest({
        apiFunc: remoteServerList,
        apiParams: {},
        enableSucceedMsg: false
      })
        .then(res => {
          this.serverOptions = res.data || [];
        })
        .catch(error => {
          message(`获取远程服务器列表失败: ${error.message}`, {
            type: "error"
          });
        });
    },

    /**
     * fetchJmxEditorContent
     * 刷新 JMX 编辑器内容
     * @param branch 分支名称
     * @param jmxPath JMX 文件路径
     * @returns {Promise<void>}
     */
    async fetchJmxEditorContent(branch: string, jmxPath: string) {
      this.jmxEditor.loading = true; // 显示加载状态
      try {
        const res = await superRequest({
          apiFunc: jmxContentApi,
          apiParams: {
            ref: branch,
            path: jmxPath
          }
        });
        if (res?.code !== 0) {
          message(`获取 JMX 文件内容失败: ${res?.msg || "未知错误"}`, {
            type: "error"
          });
          return;
        }
        this.jmxEditor.content = res.data.content || ""; // 设置 JMX 编辑器内容
      } catch (error) {
        message(`获取 JMX 文件内容失败: ${error.message}`, { type: "error" });
      } finally {
        this.jmxEditor.loading = false; // 确保加载状态被隐藏
      }
    },

    /**
     * initJmxParamsByNode
     * 初始化 JMX 参数
     * 特别说明：当用户点击 JMX 节点时，判断当前节点名称和历史JMX名称是否相同。
     * a. 相同 --> 说明点击相同文件，不需要深度初始化
     * b. 不同 --> 说明点击了不同的 JMX 文件，需要深度初始化
     * @param node JMX 节点数据
     * @param deep 是否深度初始化，默认为 true
     */
    async initJmxParamsByNode(node: any, deep = true) {
      // A. deep == true | deep == false 均需要执行的参数初始化
      this.randomJmxPlanName(); // 生成随机 JMX 计划名称
      this.fetchWorkerQueueOptions(); // 获取执行器队列选项

      // B. deep == false 时需要执行的参数初始化
      if (!deep) {
        // 初始化
        return;
      }

      // C. deep == true 时需要执行的参数初始化
      const jmxName = node.data.name;
      // 请求 JMX 文件内容
      this.fetchJmxEditorContent(this.runParams.ref, node.data.path);

      // 2. 设置运行参数
      // 当前分支参数无需设置，与页面组件已经绑定
      this.runParams.server = "";
      this.runParams.jmx.name = jmxName;
      this.runParams.jmx.url = "";
      const cmd = `jmeter -n -t ${jmxName} -l jmeter.jtl -e -o html`;
      this.runParams.command = cmd;
      this.runParams.assets = [];

      this.assetsOptions = []; // 清空依赖文件选项
      node.parent.children?.forEach((subnode: any) => {
        if (subnode.isLeaf && !subnode.label.endsWith(".jmx")) {
          const asset: assetItem = {
            name: subnode.label,
            url: this.genGitFileRawUrl(this.runParams.ref, subnode.data.path)
          };
          this.assetsOptions.push(asset); // 添加到依赖文件选项中
        }
      });
    },

    /**
     * ShowJmxParamsDialog
     * 显示 JMX 参数配置对话框
     * @param node JMX 节点数据
     */
    showJmxParamsDialog(node: any) {
      this.jmxParamsDialog.visible = true; // 先关闭对话框，避免重复打开
      const isNewJmx = node.data.name !== this.runParams.jmx.name;
      this.initJmxParamsByNode(node, isNewJmx);
    },

    /**
     * validateBeforeCreate
     * 在创建 JMX 计划之前进行表单数据、执行参数的校验
     * @returns {boolean} 是否通过校验
     */
    validateBeforeCreate() {
      const { formData, runParams } = this;
      // 校验必填字段
      if (!formData.name) {
        message("请填写 JMX 计划名称", { type: "warning" });
        return false;
      }
      if (!runParams.ref) {
        message("请选择 Git 分支", { type: "warning" });
        return false;
      }
      if (!runParams.jmx.name) {
        message("请选择 JMX 文件", { type: "warning" });
        return false;
      }
      if (!runParams.server) {
        message("请选择执行jmx的远程服务器", { type: "warning" });
        return false;
      }
      if (!formData.worker_queue) {
        message("请选择接口平台任务执行器", { type: "warning" });
        return false;
      }
      if (!this.parseJmxAssets()) {
        return false;
      }
      return true;
    },

    /**
     * uploadContentAndGetUrl
     * 上传 JMX 文件内容并获取文件 URL
     */
    async uploadContentAndGetUrl(data: {
      bucket: string;
      name: string;
      content: string;
      path?: string;
    }) {
      // 发送请求上传 JMX 文件内容
      try {
        const res = await superRequest({
          apiFunc: ossUploadText,
          apiParams: data,
          enableSucceedMsg: false,
          enableFailedMsg: true
        });
        return res?.data || ""; // 返回上传后的文件 URL
      } catch (error) {
        message(`上传 JMX 文件内容失败: ${error.message}`, { type: "error" });
        return "";
      }
    },

    /**
     * 创建 JMX 计划
     * @param
     */
    async createJmxPlan(e: {
      show: (arg0: boolean) => void;
      loading: (arg0: boolean) => void;
    }) {
      try {
        // 1. 参数校验
        e.loading(true);
        if (!this.validateBeforeCreate()) return;

        // 2. 上传 JMX 文件内容并获取 URL
        const uploadData = {
          bucket: this.bucket,
          name: this.runParams.jmx.name,
          content: this.jmxEditor.content
        };
        const jmxUrl = await this.uploadContentAndGetUrl(uploadData);
        console.log("上传 JMX 文件内容后获取的 URL:", jmxUrl);
        if (!jmxUrl) {
          return;
        }

        // 3. 组织 JMX 计划所需参数
        this.runParams.jmx.url = jmxUrl;
        this.formData.id = null; // 确保新建时 ID 为空
        this.formData.case_queue = JSON.parse(JSON.stringify(this.runParams));
        console.log("创建 JMX 计划参数:", this.formData);

        // 发送请求创建 JMX 计划
        const res = await superRequest({
          apiFunc: editPlan,
          apiParams: this.formData,
          enableSucceedMsg: false,
          enableFailedMsg: true
        });
        console.log("创建 JMX 计划响应:", res);
        if (res?.code === 0) {
          e.show(false);
          const resultId = res.data?.latest_result_id || 0;
          const planId = res.data?.id || 0;
          this.showCreatedNotify({ resultId, planId });
        }
      } catch (error) {
        console.error("创建 JMX 计划失败:", error);
      } finally {
        e.loading(false); // 确保加载状态被隐藏
      }
    },

    /**
     * showCreatedNotify
     * JMX 计划创建成功通知
     * @param option
     */
    showCreatedNotify(option: { resultId; planId: number }) {
      // 创建成功通知
      const { resultId } = option;
      let html = `您可以：<br/>`;
      html += `
      <a href="#/plan/list/index"
          target="_blank"
          style="color:#409EFF;cursor:pointer;">
          ◾ 前往计划列表
      </a><br/>`;
      if (resultId > 0) {
        html += `
        <a href="#/report/detail/index?id=${resultId}" 
          target="_blank"
          style="color:#409EFF;margin-right:16px;cursor:pointer;">
          ◾ 查看任务报告
        </a><br/>`;
      }

      // 创建成功通知
      ElNotification({
        type: "success",
        title: `Jmeter Plan ${option.planId} 已创建！`,
        message: html,
        dangerouslyUseHTMLString: true,
        showClose: true,
        duration: 0 // 不自动关闭
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

export function useJmxStoreHook() {
  return useJmxStore(store);
}
