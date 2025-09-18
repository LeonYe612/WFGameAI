import { ref, Ref } from "vue";
// import { protoGenreEnum } from "@/utils/enums";
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { menuClickEvent } from "./types";
import { message } from "@/utils/message";

export function useMenuOperateHooks(props: {
  paramTreeRef: Ref; // 参数树组件
  enableTreeCheck: Ref; // 是否开启参数树勾选框
  saveVariableDialogRef: Ref; // 新增变量弹窗组件
}) {
  const testcaseStore = useTestcaseStoreHook();

  const menuTipBarVisible = ref(false);
  const menuTipBarLabel = ref("Tips");

  // ======================= 右键菜单栏相关操作 ===============================
  /**
   * Tree Node 节点选中状态发生变化时的触发事件
   * @param data: tree 当前节点响应式数据
   * @param checked: 当前节点选中与否
   */
  const handleMenuClick = (event: menuClickEvent) => {
    console.log(event);
    switch (event.menuLabel) {
      case "不校验此参数":
        setNodeDeletedValue([event.currNode], true);
        break;
      case "校验此参数":
        setNodeDeletedValue([event.currNode], false);
        break;
      case "重置参数校验范围":
        resetAllParamsDeletedValue(false);
        break;
      case "批量设置不校验参数":
        menuTipBarShow(event);
        break;
      case "批量保存自定义变量":
        menuTipBarShow(event);
        break;
      case "保存为自定义变量":
        showSaveVariableDialog([event.currNode]);
        break;
      case "查看变量引用关系":
        queryNodeVariableRefs(event.currNode);
        break;
      case "删除自定义变量":
        deleteNodeVariable(event.currNode);
        break;
      case "引用自定义变量":
        setNodeReference(event.currNode);
        break;
      case "设置高级表达式":
        setNodeExpression(event.currNode);
        break;
    }
  };

  /**
   * 通用方法：根据传递的 TreeNodes 树节点，设置不校验参数字段deleted的值
   * 本质上是修改: deleted 字段值，然后调用 Tree 的 FilterMethod 方法
   * @param data: tree 当前节点响应式数据
   * @param checked: 当前节点选中与否
   */
  const setNodeDeletedValue = (nodeList: any[], deleted: boolean) => {
    // a. 如果不是不校验，则直接设置node及其所有子节点为 true
    // b. 如果是将参数重置为校验，则需要将 node及其所有子项，以及node.parent 设置为 false
    testcaseStore.traverseTreeNode(nodeList, (node: any) => {
      node.data.deleted = deleted;
      if (!deleted) {
        if (node?.parent?.data && node.parent.data.deleted) {
          node.parent.data.deleted = deleted;
        }
      }
    });

    // props.paramTreeRef.value?.filter();
  };

  /**
   * 重置所有节点的 deleted 字段值
   * 本质上是修改: deleted 字段值，然后调用 Tree 的 FilterMethod 方法
   * @param data: tree 当前节点响应式数据
   * @param checked: 当前节点选中与否
   */
  const resetAllParamsDeletedValue = (value: boolean) => {
    testcaseStore.traverseTreeNodeData(
      testcaseStore.currentProto.proto_data || [],
      nodeData => {
        nodeData.deleted = value;
      }
    );
    // props.paramTreeRef.value?.filter();
  };

  /**
   * 打开保存自定义变量编辑框
   * 将当前选择的TreeNodes传递给 组件的show方法
   * @param data: tree 当前节点响应式数据
   * @param checked: 当前节点选中与否
   */
  const showSaveVariableDialog = (nodes: any[]) => {
    props.saveVariableDialogRef?.value?.show(nodes);
  };

  /**
   * 查询当前节点的自定义变量的引用关系
   * @param node: tree 当前节点
   */
  const queryNodeVariableRefs = (node: any) => {
    // 1. 尝试根据node的路径描述，去获取变量的key
    const key = testcaseStore.getNodeVariableKey(node);
    if (!key) {
      message(
        `未在当前协议 currentProto.variables 找到自定义变量: ${node.data.field}`,
        { type: "error" }
      );
      return;
    }
    testcaseStore.components.variablesEditorRef?.queryVariableRef(
      testcaseStore.currentStep.case_base_id,
      testcaseStore.currentStep.version,
      testcaseStore.currentStep.id,
      key
    );
  };

  /**
   * 删除指定node的自定义变量
   * 调用 VariablesEditor 中的 gentleDeleteVariable 方法
   * @param node: tree 当前节点
   */
  const deleteNodeVariable = (node: any) => {
    // 1. 尝试根据node的路径描述，去获取变量的key
    const key = testcaseStore.getNodeVariableKey(node);
    if (!key) {
      message(
        `未在当前协议 currentProto.variables 找到自定义变量: ${node.data.field}`,
        { type: "error" }
      );
      return;
    }
    testcaseStore.components.variablesEditorRef?.gentleDeleteVariable(
      testcaseStore.currentStep.case_base_id,
      testcaseStore.currentStep.version,
      testcaseStore.currentStep.id,
      key,
      false
    );
  };

  /**
   * 为 node 节点引用变量
   * @param node: tree 当前节点
   */
  const setNodeReference = (node: any) => {
    testcaseStore.components.variablesEditorRef?.show({
      case_base_id: testcaseStore.baseInfo.id,
      version: testcaseStore.baseInfo.version,
      step_id: testcaseStore.currentStep.id,
      protoInfo: testcaseStore.currentProto,
      protoDataItem: node.data
    });
  };

  /**
   * 删除 node 节点的引用变量
   * @param node: tree 当前节点
   */
  const deleteNodeReference = (node: any) => {
    const locationStr = testcaseStore.getNodeLocation(node);
    if (!location) {
      message("无法获取当前节点 location !", { type: "error" });
      return;
    }
    // 删除引用
    if (testcaseStore.currentProto?.references?.[locationStr]) {
      delete testcaseStore.currentProto.references[locationStr];
    }
    // 清空引用相关字段
    node.data.refer_name = "";
    node.data.refer_key = "";
    // 保存step
    testcaseStore.saveStep();
  };

  /**
   * 为 node 节点设置表达式
   * @param node: tree 当前节点
   */
  const setNodeExpression = (node: any) => {
    testcaseStore.components.exprEditorRef?.show({
      // case_base_id: testcaseStore.baseInfo.id,
      // version: testcaseStore.baseInfo.version,
      // step_id: testcaseStore.currentStep.id,
      protoInfo: testcaseStore.currentProto,
      protoDataItem: node.data
    });
  };

  /**
   * 删除 node 节点的表达式
   * @param node: tree 当前节点
   */
  const deleteNodeExpression = (node: any) => {
    const locationStr = testcaseStore.getNodeLocation(node);
    if (!location) {
      message("无法获取当前节点 location !", { type: "error" });
      return;
    }
    // 删除proto中记录的表达式
    if (
      Object.keys(testcaseStore.currentProto?.expressions || {}).includes(
        locationStr
      )
    ) {
      delete testcaseStore.currentProto.expressions[locationStr];
    }
    // 清空表达式字段
    node.data.expr = "";
    // 保存step
    testcaseStore.saveStep();
  };

  // ========================== 批量操作提示栏 =========================
  const menuTipBarShow = (event: menuClickEvent) => {
    menuTipBarLabel.value = event.menuLabel;
    menuTipBarVisible.value = true;
    props.enableTreeCheck.value = true;
    props.paramTreeRef.value!.setCheckedKeys([]);
  };

  const menuTipBarCancel = () => {
    menuTipBarVisible.value = false;
    props.enableTreeCheck.value = false;
  };

  const menuTipBarConfirm = () => {
    switch (menuTipBarLabel.value) {
      case "批量设置不校验参数": {
        // 获取当前选中节点(无需校验)
        const nodeList = props.paramTreeRef.value?.getCheckedNodes();
        testcaseStore.traverseTreeNodeData(nodeList, (node: any) => {
          node.deleted = true;
        });
        // props.paramTreeRef.value?.filter();
        break;
      }
      case "批量保存自定义变量": {
        // 获取当前选中节点(show方法中会校验节点是否允许保存为自定义变量)
        const keys = props.paramTreeRef.value?.getCheckedKeys() || [];
        const nodes = [];
        for (let i = 0; i < keys.length; i++) {
          const node = props.paramTreeRef.value?.getNode(keys[i]);
          if (node.isLeaf) {
            nodes.push(node);
          }
        }
        showSaveVariableDialog(nodes);
        break;
      }
    }
    menuTipBarVisible.value = false;
    props.enableTreeCheck.value = false;
  };

  return {
    menuTipBarVisible,
    menuTipBarLabel,
    handleMenuClick,
    menuTipBarCancel,
    menuTipBarConfirm,
    setNodeReference,
    deleteNodeReference,
    setNodeExpression,
    deleteNodeExpression
  };
}
