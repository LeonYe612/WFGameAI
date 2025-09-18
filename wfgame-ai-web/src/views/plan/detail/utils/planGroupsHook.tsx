import { computed, ref } from "vue";
import type { TabPaneName } from "element-plus";
import { ElMessage } from "element-plus";
import { usePlanStoreHook } from "@/store/modules/plan";
import { hasAuth } from "@/router/utils";
import { perms } from "@/utils/permsCode";
export function plansGroupsConfig() {
  const store = usePlanStoreHook();
  const whole_case_queue = computed(() => store.info.whole_case_queue);
  const case_queue = store.info.case_queue;
  const editableTabsValue = ref("0");
  const oldTabName = computed(() => store.info.old_tab_name);
  const newTabName = computed(() => store.info.new_tab_name);
  const editableTabs = computed(() => store.info.editableTabs);
  let tabIndex =
    whole_case_queue.value.length > 0 ? whole_case_queue.value.length - 1 : 0;
  // 获取 whole_case_queue 中键为 "0" 的对象
  const tab0 = whole_case_queue.value.find(tab => Object.keys(tab)[0] === "0");
  // 如果不存在键为 "0" 的对象，使用默认的空数组
  store.SET_CASE_QUEUE("0");

  // if (!tab0) {
  //   store.CLEAR_CASE_QUEUE();
  // } else {
  //   // 如果存在键为 "0" 的对象，将其值复制给 case_queue
  // 依次创建其他的顺序组
  for (let i = 1; i < whole_case_queue.value.length; i++) {
    const tab = whole_case_queue.value[i];
    const tabName = Object.keys(tab)[0];
    store.ADD_GROUP_TABS({
      title: `顺序执行组 ${tabName}`,
      name: tabName,
      content: `⚠️ 顺序执行组 ${tabName} .`,
      closable: true
    });
  }
  const handleTabsEdit = (
    targetName: TabPaneName | undefined,
    action: "remove" | "add"
  ) => {
    // 如果没有权限或者当前页面为编辑状态，则不允许操作
    if (!hasAuth(perms.plan.detail.writable) || store.info.id) {
      return;
    }
    // console.log("oldTabName : ", oldTabName);
    // ElMessage.warning("功能尚未开放！");
    // return;
    if (action === "add") {
      const newTabName = `${++tabIndex}`;
      store.ADD_GROUP_TABS({
        closable: true,
        title: `顺序执行组 ${tabIndex}`,
        name: newTabName,
        content: `⚠️ 顺序执行组 ${tabIndex}.`
      });
      editableTabsValue.value = newTabName;
      store.ADD_TO_WHOLE_CASE_QUEUE(newTabName); // 添加新的 tab_name 到 store.info.whole_case_queue
      handleTabsChange({ paneName: newTabName }); // 手动调用改变处理
      // handleTabsChange({ paneName: newTabName }); // 手动调用改变处理
    } else if (action === "remove") {
      const tabs = editableTabs.value;
      let activeName = editableTabsValue.value;
      const targetTab = tabs.find(tab => tab.name === targetName);
      if (targetTab && !targetTab.closable) {
        ElMessage.warning("不可删除默认组");
        return;
      }
      if (activeName === targetName) {
        tabs.forEach((tab, index) => {
          if (tab.name === targetName) {
            const nextTab = tabs[index + 1] || tabs[index - 1];
            if (nextTab) {
              activeName = nextTab.name;
            }
          }
        });
      }
      editableTabsValue.value = activeName;
      store.DELETE_GROUP_TABS(targetName);
      store.DELETE_TO_WHOLE_CASE_QUEUE(`${targetName}`); //  移除对应标签的用例列表
      // 只有当活动标签实际更改时才调用
      if (activeName !== editableTabsValue.value) {
        handleTabsChange({ paneName: activeName });
      }
    }
  };

  const handleTabsChange = ({ paneName }: { paneName: TabPaneName }) => {
    // step1 更新old tabName（上一次记录的激活的标签页名称变成了旧的标签页名称）
    store.SET_OLD_TAB_NAME(newTabName.value);
    // step2 更新new tabName（当前激活的标签页名称设置为新的标签页名称）
    store.SET_NEW_TAB_NAME(`${paneName}`);
    // step3 更新上一个页签的case_queue数据
    store.UPDATE_TO_WHOLE_CASE_QUEUE(oldTabName.value, case_queue);
    // step4 设置当前tab_name对应的case_queue队列到store.info.case_queue
    store.SET_CASE_QUEUE(`${paneName}`); // 设置当前tab_name对应的用例队列
  };

  return {
    editableTabs,
    editableTabsValue,
    handleTabsEdit,
    handleTabsChange
  };
}
