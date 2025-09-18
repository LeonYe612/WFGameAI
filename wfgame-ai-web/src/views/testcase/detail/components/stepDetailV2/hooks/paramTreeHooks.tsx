import { ref, watch, nextTick, computed } from "vue";
// import { protoGenreEnum } from "@/utils/enums";
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { message } from "@/utils/message";

export function useParamTreeHooks() {
  const testcaseStore = useTestcaseStoreHook();

  const treeContainerRef = ref(null);
  const treeHeight = ref(300);
  const checkCode = ref(true);
  const checkData = ref(true);

  watch(
    [
      () => testcaseStore.currentProtoType,
      () => testcaseStore.currentProtoIndex
    ],
    () => {
      nextTick(() => {
        treeHeight.value = (treeContainerRef.value?.clientHeight || 300) - 1;
      });
    },
    {
      immediate: false,
      flush: "post"
    }
  );

  // ===========================  Code码相关功能 ========================
  const setCheckCode = (val: boolean) => {
    checkCode.value = val;
  };

  const setCheckData = (val: boolean) => {
    checkData.value = val;
  };

  // 自动查询Code的值并显示
  const handleCodeChanged = newCode => {
    if (newCode) {
      testcaseStore.currentProto.code_desc = "";
      testcaseStore.getCodeDesc({
        onSucceed: data => {
          testcaseStore.currentProto.code_desc = data;
        },
        env: testcaseStore.baseInfo.env,
        code: newCode
      });
    }
  };

  const onCheckCodeChange = val => {
    testcaseStore.currentProto.verify_rules.omit_code = !val;
  };

  const onCheckDataChange = val => {
    testcaseStore.currentProto.verify_rules.omit_data = !val;
  };

  // ===========================  Param Tree ========================
  // 组件实例 ref
  const paramTreeRef = ref(null);
  const bigInputRef = ref(null);
  const saveVariableDialogRef = ref(null);
  const treeContextMenuRef = ref(null);
  const fishInfoDialogRef = ref(null);
  const scoreInfoDialogRef = ref(null);
  // 响应式数据
  const enableTreeCheck = ref(false);
  const treeQuery = ref("");

  const treeProps = {
    value: "key", // 每个树节点用来作为唯一标识的属性，在整棵树中应该是唯一的
    label: "field", // 	指定节点标签为节点对象的某个属性值
    children: "children" // 指定子树为节点对象的某个属性值
  };

  const treeNodeHeight = ref(40);
  const onOperatorClick = data => {
    if (data.operator === "=") {
      data.operator = "!=";
    } else if (data.operator === "!=") {
      data.operator = "=";
    }
  };

  // 定义 proto3 中的所有基本类型
  const proto3BasicTypes = {
    double: true,
    float: true,
    int16: true,
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

  // 创建计算属性来判断字符串是否是 proto3 中的基本类型
  const isProto3BasicType = computed(() => {
    return typeString => {
      const lowerCaseString = typeString.toLowerCase();
      if (proto3BasicTypes[lowerCaseString]) {
        return true;
      }
      return !!proto3FireBasicTypes[lowerCaseString];
    };
  });

  // 定义 proto3 中的所有数字类型
  const proto3NumberTypes = {
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
    sfixed64: true
  };

  // 定义 proto3 纸老虎特殊处理的基本类型
  const proto3FireBasicTypes = {
    int8: true,
    int16: true,
    float64: true
  };

  // 定义 proto3 纸老虎特殊处理的数字类型
  const proto3FireNumberTypes = {
    int8: true,
    int16: true,
    float64: true
  };

  const isProto3NumberType = computed(() => {
    return typeString => {
      const lowerCaseString = typeString.toLowerCase();
      if (proto3NumberTypes[lowerCaseString]) {
        return true;
      }
      return !!proto3FireNumberTypes[lowerCaseString];
    };
  });

  const currentProtoVarsMap = computed(() => {
    const vars = testcaseStore.currentProto?.variables;
    if (!vars) {
      return {};
    }
    const map = {};
    Object.keys(vars).forEach(varName => {
      map[vars[varName].location] = true;
    });
    return map;
  });

  const isCustomVar = computed(() => {
    return node => {
      const nodeLocation = testcaseStore.getNodeLocation(node);
      return currentProtoVarsMap.value?.[nodeLocation];
    };
  });

  const tooltip = computed(() => {
    return nodeData => {
      // 使用正则表达式将 "<" 和 ">" 转换为 HTML 实体
      const fieldType = nodeData.type
        ? nodeData.type.replace(/</g, "&lt;").replace(/>/g, "&gt;")
        : "无";
      const fieldModifier = nodeData.modifier
        ? nodeData.modifier.replace(/</g, "&lt;").replace(/>/g, "&gt;")
        : "无";
      return `
  <ul style="list-style: square;padding: 5px;font-size: 14px;margin-left: 5px;">
    <li>含义:${nodeData.remark || "暂无参数描述"}</li>
    <li>类型：${fieldType}</li>
    <li>描述符: ${fieldModifier}</li>
  </ul>
      `;
    };
  });

  const fieldClass = computed(() => {
    return nodeData => {
      if (nodeData.deleted) {
        return "text-gray-300";
      }
      if (nodeData.modifier === "item") {
        return "text-blue-500";
      }
      if (nodeData.modifier === "key" || nodeData.modifier === "value") {
        return "text-blue-500";
      }
      return "text-gray-700";
    };
  });
  /**
   * 打开便捷输入框
   * @param protoDataItem: tree 当前节点响应式数据
   */
  const showBigInputDialog = (protoDataItem: any) => {
    bigInputRef.value?.show(protoDataItem, protoDataItem.field || "编辑框");
  };

  /**
   * @description: 刷新树形数据
   */
  const refreshTreeData = () => {
    paramTreeRef.value.setData(testcaseStore.currentProto?.proto_data || []);
  };

  /**
   * @description: 树形数据过滤
   */
  const treeFilterMetod = (query: string, node: any) => {
    return !node.deleted;
  };

  /**
   * 删除数组类型(repeated)的子项
   * @param node: tree 当前节点
   * @param data: tree 当前节点响应式数据
   */
  const deleteRepeatedItem = (node, data) => {
    // a. 确保父节点存在
    const parentNode = node.parent;
    const parentData = parentNode.data;
    if (!parentNode) {
      console.error("node.parent is null, curr node is: ", node);
      return;
    }
    // b. 如果子项中存在自定义变量，则不允许删除
    const itemLocation = testcaseStore.getNodeLocation(node);
    if (
      Object.keys(currentProtoVarsMap.value).some(location =>
        location.includes(itemLocation)
      )
    ) {
      message("当前子项存在自定义变量，请先删除自定义变量后再删除子项！", {
        type: "warning"
      });
      return;
    }
    // c. 如果子项中存在引用，则不允许删除
    if (
      testcaseStore.currentProto?.references &&
      Object.keys(testcaseStore.currentProto?.references).some(location =>
        location.includes(itemLocation)
      )
    ) {
      message("当前子项存在变量引用，请先删除引用后再删除子项！", {
        type: "warning"
      });
      return;
    }

    // d. 每次删除子项前尝试将其保存在父级 node.childTemplate 中
    // 如果已经有 childTemplate 则不再重复保存
    if (!parentData?.childTemplate) {
      parentData.childTemplate = JSON.parse(JSON.stringify(data));
    }
    // e. 删除子项
    const index = parentData.children.indexOf(data); // 获取要移除节点在父节点的索引
    parentData.children.splice(index, 1); // 移除节点
    refreshTreeData();
  };

  /**
   * 添加数组类型(repeated)的子项
   * @param node: tree 当前节点
   * @param data: tree 当前节点响应式数据
   */
  const addRepeatedItem = (node, data) => {
    // Step1. 获取新增的子项数据
    // a. 尝试从data.children[-1] 获取新增的子项
    // b. 如果没有则获取 data.childTemplate 中存储的子项模板
    let newChild = null;
    if (data?.children?.length) {
      newChild = JSON.parse(
        JSON.stringify(data.children[data.children.length - 1])
      );
    } else {
      newChild = data?.childTemplate;
    }
    if (!newChild) {
      message("未找到子项模板！", { type: "error" });
      return;
    }

    // Step2. 为子项及其所有子项, 赋予新的key(否则node的key相同, 导致异常)
    newChild.key = testcaseStore.uniqueId();
    if (newChild?.children?.length) {
      testcaseStore.addKeyForProtoData(newChild.children);
    }

    // step3. 保留新子项的删除状态(deleted)

    // step4. 添加新的子项到父项
    if (!data.children) {
      data.children = [];
    }
    data.children.push(newChild);
    refreshTreeData();

    // step5. 展开当前父节点 --> 合并父节点下的所有子节点 --> 展开新增子节点
    paramTreeRef.value?.expandNode(node);
    node.children?.forEach(node => {
      paramTreeRef.value?.collapseNode(node);
    });
    nextTick(() => {
      const newChildNode = paramTreeRef.value?.getNode(newChild.key);
      if (newChildNode) {
        paramTreeRef.value?.expandNode(newChildNode);
      }
    });
  };

  /**
   * Tree Node 节点选中状态发生变化时的触发事件
   * @param data: tree 当前节点响应式数据
   * @param checked: 当前节点选中与否
   */
  const handleTreeNodeCheckChange = (data: any, checked: boolean) => {
    console.log(data, checked);
  };

  /**
   * Tree Node 节点右键点击事件
   * @param e: 右键点击事件
   * @param data: tree 当前节点响应式数据
   * @param node: tree 当前节点
   */
  const handleNodeContextMenu = (event: any, data: any, node: any) => {
    event.preventDefault();
    console.log("handleNodeContextMenu", treeContextMenuRef.value);
    treeContextMenuRef.value?.show(event, node);
  };

  /**
   *显示多多玩-捕鱼 鱼列表（db获取）
   * //todo 后续看是否需要加入环境区分，当前只有test环境
   */
  const showFishInfoDialog = (protoDataItem: any) => {
    fishInfoDialogRef.value?.show(protoDataItem);
  };

  /**
   *显示多多玩-捕鱼 鱼列表（db获取）
   * //todo 后续看是否需要加入环境区分，当前只有test环境
   */
  const showScoreInfoDialog = (protoDataItem: any) => {
    scoreInfoDialogRef.value?.show(protoDataItem);
  };
  return {
    // constants
    treeProps,
    treeNodeHeight,
    // ref
    treeContainerRef,
    paramTreeRef,
    bigInputRef,
    saveVariableDialogRef,
    treeContextMenuRef,
    fishInfoDialogRef,
    scoreInfoDialogRef,
    treeHeight,
    checkCode,
    checkData,
    enableTreeCheck,
    treeQuery,
    // computed
    tooltip,
    fieldClass,
    isProto3BasicType,
    isProto3NumberType,
    isCustomVar,
    // methods
    setCheckCode,
    setCheckData,
    handleCodeChanged,
    onCheckCodeChange,
    onCheckDataChange,
    onOperatorClick,
    showBigInputDialog,
    deleteRepeatedItem,
    addRepeatedItem,
    treeFilterMetod,
    handleTreeNodeCheckChange,
    handleNodeContextMenu,
    showFishInfoDialog,
    showScoreInfoDialog
  };
}
