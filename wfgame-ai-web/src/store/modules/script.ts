import { defineStore } from "pinia";
import { store } from "@/store";
import { scriptApi, actionTypeApi, type ScriptItem } from "@/api/scripts";
import { ref, computed } from "vue";
import { message } from "@/utils/message";
import { scriptTypeEnum } from "@/utils/enums";

export const useScriptStore = defineStore({
  id: "pure-script",
  state: () => ({
    // 当前正在编辑的脚本对象
    scriptItem: ref<Partial<ScriptItem>>({
      name: "",
      type: scriptTypeEnum.MANUAL.value,
      category: null,
      description: "",
      steps: [],
      meta: {},
      is_active: true,
      include_in_log: true
    }),
    // 动作库列表
    actionLibrary: ref([]),
    // 当前激活的步骤索引
    activeStep: ref<number | null>(null),
    // 当前聚焦的UI元素信息，用于组件间联动
    activeFocus: ref<{
      stepIndex: number | null;
      paramName: string | null;
    } | null>(null),
    // 组件复用
    components: {
      // 脚本目录编辑组件
      showCategoryEditor: false
    }
  }),
  getters: {
    /** 获取当前脚本的步骤 */
    getSteps: state => state.scriptItem.steps,
    /** 获取当前激活的步骤 */
    getActiveStep: state => state.activeStep,
    /** 获取当前聚焦信息 */
    getActiveFocus: state => state.activeFocus,
    /** 判断当前是创建模式还是编辑模式 */
    isEditMode: state => computed(() => !!state.scriptItem.id).value
  },
  actions: {
    /** 从 API 获取脚本详情 */
    async fetchScriptDetail(id: number) {
      this.resetScriptItem();
      if (!id) {
        return;
      }
      try {
        const { data } = await scriptApi.detail(id);
        this.scriptItem = data;
      } catch (error) {
        message("获取脚本详情失败，请在控制台查看错误详情", { type: "error" });
        console.error("Failed to fetch script detail:", error);
      }
    },
    /** 从 API 获取动作库列表 */
    async fetchActionLibrary() {
      try {
        const { data } = await actionTypeApi.listWithParams({
          is_enabled: true
        });
        this.actionLibrary = data;
      } catch (error) {
        message("获取动作库失败，请在控制台查看错误详情", { type: "error" });
        console.error("Failed to fetch action library:", error);
      }
    },
    /** 重置脚本对象为初始状态 */
    resetScriptItem() {
      this.scriptItem = {
        name: "",
        type: scriptTypeEnum.MANUAL.value,
        category: null,
        description: "",
        steps: [],
        meta: {},
        is_active: true,
        include_in_log: true
      };
      this.activeStep = null;
      this.activeFocus = null;
    },
    /** 更新步骤 */
    updateSteps(newSteps: any[]) {
      if (this.scriptItem) {
        this.scriptItem.steps = newSteps;
      }
    },
    /** 设置当前激活的步骤 */
    setActiveStep(index: number | null) {
      this.activeStep = index;
    },
    /** 设置当前聚焦的步骤和参数 */
    setActiveFocus(stepIndex: number | null, paramName: string | null = null) {
      if (
        !this.activeFocus ||
        this.activeFocus.stepIndex !== stepIndex ||
        this.activeFocus.paramName !== paramName
      ) {
        this.activeFocus = { stepIndex, paramName };
      }
      if (this.activeStep !== stepIndex) {
        this.setActiveStep(stepIndex);
      }
    },
    /**
     * 添加一个新步骤到结尾
     * @param action 动作库中的原始动作对象
     */
    addStep(action: any) {
      const newStep = {
        action: action.action_type,
        remark: action.name,
        ...action.params.reduce((acc, param) => {
          acc[param.name] = param.default?.value ?? null;
          return acc;
        }, {})
      };
      this.scriptItem.steps.push(newStep);
      // 添加后自动展开新的步骤
      this.activeStep = this.scriptItem.steps.length - 1;
      this.setActiveFocus(this.activeStep, null);
    },
    /** 向当前选中索引后方，插入 steps */
    insertSteps(steps: any[], changeActive = false) {
      const insertIndex =
        this.activeStep !== null
          ? this.activeStep + 1
          : this.scriptItem.steps.length;
      this.scriptItem.steps.splice(insertIndex, 0, ...steps);
      if (changeActive && steps.length > 0) {
        this.activeStep = insertIndex;
        this.setActiveFocus(this.activeStep, null);
      }
    },
    /** 保存（创建或更新）脚本 */
    async saveScript() {
      try {
        let response;
        if (this.isEditMode) {
          response = await scriptApi.update(this.scriptItem as ScriptItem);
          message("保存成功", { type: "success" });
        } else {
          response = await scriptApi.create(this.scriptItem as ScriptItem);
          message("创建成功", { type: "success" });
        }
        return response.data;
      } catch (error) {
        console.error("Failed to save script:", error);
        message("保存脚本失败，请在控制台查看错误详情", { type: "error" });
        return null;
      }
    }
  }
});
export function useScriptStoreHook() {
  return useScriptStore(store);
}
