<script setup lang="ts">
import { ref, computed } from "vue";
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import AddIcon from "@/assets/svg/add.svg?component";
import ProtoSelector from "@/views/common/selectors/protoSelector/index.vue";
import EmptyIcon from "@/assets/svg/empty.svg?component";
import type { TabPaneName } from "element-plus";
import { detailProto } from "@/api/testcase";
import { superRequest } from "@/utils/request";
import { message } from "@/utils/message";
import { ElMessageBox } from "element-plus";
import ArrayInput from "@/views/common/input/arrayInput.vue";
import { perms } from "@/utils/permsCode";
import { hasAuth } from "@/router/utils";
import {
  View,
  Minus,
  CirclePlus,
  CircleClose,
  MagicStick,
  Connection,
  CloseBold,
  Refresh
} from "@element-plus/icons-vue";
import ProtoContentDisplayer from "./protoContentDisplayer.vue";
import GmHelper from "./gmHelper.vue";
import "v-contextmenu/dist/themes/default.css";
import {
  directive,
  Contextmenu,
  ContextmenuItem,
  ContextmenuDivider,
  ContextmenuSubmenu,
  ContextmenuGroup
} from "v-contextmenu";
import { protoGenreEnum } from "@/utils/enums";

const testcaseStore = useTestcaseStoreHook();

defineOptions({
  name: "TestcaseMessagesEditor",
  components: {
    [Contextmenu.name]: Contextmenu,
    [ContextmenuItem.name]: ContextmenuItem,
    [ContextmenuDivider.name]: ContextmenuDivider,
    [ContextmenuSubmenu.name]: ContextmenuSubmenu,
    [ContextmenuGroup.name]: ContextmenuGroup
  },
  directives: {
    contextmenu: directive
  }
});
const props = defineProps({
  type: {
    type: String,
    default: protoGenreEnum.SEND.value // send | recv
  }
});

const protoSelectorRef = ref(null);
const protoContentDisplayerRef = ref(null);
const gmHelperRef = ref(null);
const gmParamRow = ref(null);

const operatorEnums = computed(() => {
  if (props.type === protoGenreEnum.SEND.value) {
    return [
      {
        label: "=",
        value: "="
      }
    ];
  } else {
    return [
      {
        label: "=",
        value: "="
      },
      {
        label: "!=",
        value: "!="
      }
    ];
  }
});

// ========================== Table 相关 =============================
//记录多个 protoTableRefs
const protoTableRefs = ref({});
const rememberRefs = el => {
  if (el && el.$attrs && el.$attrs["refname"]) {
    protoTableRefs.value[el.$attrs["refname"]] = el;
  }
};
const getCurrentIdxTableRef = () => {
  const refName = `${props.type}_proto_table_${currentTabIndex.value}`;
  const table = protoTableRefs.value[refName];
  return table;
};

// Table 行点击事件
const handleRowClick = row => {
  getCurrentIdxTableRef()?.toggleRowExpansion(row);
};

/** GM Helper 相关 */
const handleShowGmHelper = (gmRow: any) => {
  // 记住当前的行;
  if (gmRow) {
    gmHelperRef.value?.show();
    gmParamRow.value = gmRow;
  }
};

const handleGmHelperCompleted = (value: string) => {
  gmParamRow.value.value = value;
};

/** 表格内操作 */

// 操作符变更触发事件
const handleOperatorChange = (value: string, row: any) => {
  if (value === "=") {
    row.value = "";
  } else if (value === "in") {
    row.value = [];
  }
};

// 删除参数的变量引用
const handleDeleteRowReference = row => {
  const protoInfos = testcaseStore.GET_CURRENT_STEP_MSG(props.type);
  const protoInfo = protoInfos?.[currentTabIndex.value];
  const locationStr = testcaseStore.findDescriptionPathString(
    protoInfo.proto_data,
    row.key,
    ""
  );
  delete protoInfo.references[locationStr];

  // 清空 protoDataItem 字段
  row.refer_name = "";
  row.refer_key = "";
  // 保存step
  testcaseStore.saveStep();
};

// 重新为参数指定变量引用
const handleChangeRowReference = row => {
  // step1. 将当前的 ProtoInfo 对象和当前的 Row 传递给 VariablesEditor
  const protoInfos = testcaseStore.GET_CURRENT_STEP_MSG(props.type);
  const protoInfo = protoInfos?.[currentTabIndex.value];
  const protoDataItem = row;

  testcaseStore.components.variablesEditorRef?.show({
    case_base_id: testcaseStore.baseInfo.id,
    version: testcaseStore.baseInfo.version,
    step_id: testcaseStore.currentStep.id,
    protoInfo,
    protoDataItem
  });
};
/** Repeated 类型操作 */

// 删除 repeated 子项
const handleDeleteRepeatedItem = (tableData, row) => {
  // 删除前将row row.parent 备份到 row.itemTemplate 中
  const parent = findRowParentRecursive(tableData, row);
  if (!parent) {
    console.error("未在tableData中找到row的父节点:", tableData, row);
    return;
  }
  const childTemplate = JSON.parse(JSON.stringify(row));
  parent.childTemplate = childTemplate;
  const index = parent.children.indexOf(row);
  parent.children.splice(index, 1);
};

// 添加 repeated 类型的子项
const handleAddRepeatedItem = row => {
  // row 即为 repeated 类型的父项
  let newChild = null;
  if (row.childTemplate) {
    // a. 如果 row.childTemplate 存在则从中恢复
    newChild = JSON.parse(JSON.stringify(row.childTemplate));
  } else {
    // b. 如果 row.childTemplate 不存在则从 row.children 中复制一个
    newChild = JSON.parse(JSON.stringify(row.children[0]));
  }
  // 为新item及其子项赋予新的key
  newChild.key = testcaseStore.uniqueId();
  testcaseStore.addKeyForProtoData(newChild?.children);
  setProtoDataItemDeleted(newChild, false);
  row.children.push(newChild);

  getCurrentIdxTableRef()?.toggleRowExpansion(row, true);
};

const findRowParentRecursive = (nodes, child) => {
  for (const node of nodes) {
    if (node.children && node.children.includes(child)) {
      return node;
    } else if (node.children) {
      const result = findRowParentRecursive(node.children, child);
      if (result) {
        return result;
      }
    }
  }
  return null;
};

const enableVerifyCode = computed({
  // 读取计算属性的值
  get() {
    const protoInfos = testcaseStore.GET_CURRENT_STEP_MSG(props.type);
    const protoInfo = protoInfos?.[currentTabIndex.value];
    if (protoInfo?.verify_rules?.omit_code === undefined) {
      return true;
    }
    return !protoInfo?.verify_rules?.omit_code;
  },
  // 设置计算属性的值
  set(value) {
    const protoInfos = testcaseStore.GET_CURRENT_STEP_MSG(props.type);
    const protoInfo = protoInfos?.[currentTabIndex.value];
    protoInfo.verify_rules.omit_code = !value;
  }
});

const enableVerifyData = computed({
  // 读取计算属性的值
  get() {
    const protoInfos = testcaseStore.GET_CURRENT_STEP_MSG(props.type);
    const protoInfo = protoInfos?.[currentTabIndex.value];
    if (protoInfo?.verify_rules?.omit_data === undefined) {
      return true;
    }
    return !protoInfo?.verify_rules?.omit_data;
  },
  // 设置计算属性的值
  set(value) {
    const protoInfos = testcaseStore.GET_CURRENT_STEP_MSG(props.type);
    const protoInfo = protoInfos?.[currentTabIndex.value];
    protoInfo.verify_rules.omit_data = !value;
  }
});

// ========================== tabs 相关 =============================
const tabs = computed(() => {
  return testcaseStore.GET_CURRENT_STEP_MSG(props.type);
});

const isAddable = computed(() => {
  if (!hasAuth(perms.testcase.detail.writable)) return false;
  if (props.type === protoGenreEnum.SEND.value) {
    return testcaseStore.currentStep.send.length < 1;
  } else if (props.type === protoGenreEnum.RECV.value) {
    return true;
  } else {
    return false;
  }
});

const isNumberType = computed(() => {
  return (row: any) => {
    return (
      row.type.includes("uint") ||
      row.type.includes("int") ||
      row.type.includes("float") ||
      row.type.includes("double") ||
      row.type.includes("float64")
    );
  };
});

const isGmReq = computed(() => {
  return row => {
    return (
      props.type === protoGenreEnum.SEND.value &&
      tabs.value &&
      tabs.value.length > 0 &&
      tabs.value[0].proto_message === "GMReq" &&
      tabs.value[0].proto_data[0]?.value == 4 &&
      row.field == "param"
    );
  };
});

const currentTabIndex = ref(0);

// 点击新增按钮
const handleTabAdd = () => {
  protoSelectorRef.value?.show();
};
// 协议选择完成后, 根据选择的结果查询协议详情并添加到tab
const handleProtoSelectorComplete = async (protos: any) => {
  if (!protos || protos.length === 0) return;
  try {
    testcaseStore.shareState.stepDetailLoading = true;
    for (let i = 0; i < protos.length; i++) {
      await superRequest({
        apiFunc: detailProto,
        apiParams: { id: protos[i].id },
        onSucceed: protoInfo => {
          testcaseStore.ADD_CURRENT_STEP_MSG(props.type, protoInfo);
        }
      });
    }
  } catch (error) {
    message(`查询协议详情出错: ${error}`, { type: "error" });
  } finally {
    // 默认选择最后一个tab
    currentTabIndex.value = tabs.value.length - 1;
    testcaseStore.shareState.stepDetailLoading = false;
  }
};
// 点击移除tab
const handleTabRemove = (targetName: TabPaneName) => {
  // 这里的tabName就是tab的索引值
  const removeIndex = parseInt(targetName);
  ElMessageBox.confirm(
    `确认要移除此：${
      props.type === protoGenreEnum.SEND.value ? "请求" : "响应"
    }消息？`,
    "友情提示",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning"
    }
  )
    .then(() => {
      // 重新设置tab当前选中的索引
      if (currentTabIndex.value === removeIndex) {
        // a. 删除tab为当前选中tab
        if (tabs.value.length === 1) {
          // 当前tab为最后一个tab
          currentTabIndex.value = -1;
        } else if (removeIndex === tabs.value.length - 1) {
          // 当前tab为最后一个tab
          currentTabIndex.value = removeIndex - 1;
        } else {
          // 当前tab为中间tab
          currentTabIndex.value = removeIndex;
        }
      } else {
        // b. 删除tab不是当前选中tab
        if (removeIndex > currentTabIndex.value) {
          // currentTabIndex.value = currentTabIndex.value;
        } else {
          currentTabIndex.value--;
        }
      }
      testcaseStore.REMOVE_CURRENT_STEP_MSG(props.type, removeIndex);
    })
    .catch(() => {});
};

const rowClassName = ({ row }) => {
  return row.deleted ? "hideTableRow" : "";
};

const setProtoDataItemDeleted = (item, deletedVal: boolean) => {
  item.deleted = deletedVal;
  if (item.children && item.children.length > 0) {
    item.children.forEach(element => {
      setProtoDataItemDeleted(element, deletedVal);
    });
  }
};

const setProtoDataAllDeleted = (protoData, deletedVal: boolean) => {
  if (protoData && protoData.length > 0) {
    protoData.forEach(element => {
      setProtoDataItemDeleted(element, deletedVal);
    });
  }
};

const handleViewProtoContent = (protoItem: any) => {
  protoContentDisplayerRef.value?.show(protoItem);
};

const handleResetProto = (protoInfo: any) => {
  setProtoDataAllDeleted(protoInfo.proto_data, false);
};

// =============== Table 右键菜单相关 =======================
const contextmenu = ref(null);
const currentRow = ref(null);
const menuStatus = ref(0); // 0: 初始状态 1-填写变量名状态
const varName = ref("");
const varRemark = ref("");
const isBasicType = ref(false);

// 右键 Table 行显示菜单
const handleRowContextMenu = (row: any, column: any, event: any) => {
  console.log("右键点击表格行:", row);
  console.log(
    "已记录此行至 messageEditor -> currentRow.value！其中key:",
    row.key
  );
  currentRow.value = row;
  // a. 阻止浏览器默认右键菜单
  event.preventDefault();

  // b. 判断是否满足弹出菜单条件
  isBasicType.value = testcaseStore.isProto3BasicType(row.type);

  // c. 满足条件显示菜单
  // 菜单高度200,需要判断是否超出屏幕高度调整 top
  let top = event.clientY;
  if (window.innerHeight - event.clientY < 200) {
    top = window.innerHeight - 200;
  }
  contextmenu.value?.show({
    left: event.clientX,
    top: top
  });
};

// 重置并隐藏菜单
const resetContextMenu = () => {
  currentRow.value = null;
  contextmenu.value?.hide();
  menuStatus.value = 0;
  varName.value = "";
  varRemark.value = "";
};

// 菜单选项1：保存变量-Click
const handleSaveVariable = () => {
  menuStatus.value = 1;
  // 自动填充初始 varName 和 varRemark
  varName.value = currentRow.value.field;
  varRemark.value = currentRow.value.remark.trim();
};

// 菜单选项2：不校验此参数-Click
const handleHideProtoDataItemParam = () => {
  // 如果参数有子级，则需要将子级中的所有 deleted 字段标记删除(1)
  setProtoDataItemDeleted(currentRow.value, true);
};

const confirmSaveVariable = () => {
  // step1. 校验是否为合法变量名
  const name = varName.value;
  const pattern = /^[a-zA-Z_][a-zA-Z0-9_]*$/;
  const isValid = pattern.test(name);
  if (!isValid) {
    return message("请输入合法的变量名", { type: "warning" });
  }
  // step2. 检查变量名是否重复
  const protoInfos = testcaseStore.GET_CURRENT_STEP_MSG(props.type);
  const protoInfo = protoInfos?.[currentTabIndex.value];
  if (!protoInfo?.variables) {
    protoInfo.variables = {};
  }
  const locationStr = testcaseStore.findDescriptionPathString(
    protoInfo.proto_data,
    currentRow.value.key,
    ""
  );
  const customVar = {
    name: name,
    remark: varRemark.value,
    location: locationStr,
    value: null,
    type: currentRow.value.type,
    key: testcaseStore.uniqueId()
  };
  protoInfo.variables[name] = customVar;
  resetContextMenu();
  testcaseStore.saveStep({
    onSucceed: () => {
      message(`变量 ${name} 保存成功!`, { type: "success" });
    }
  });
};

const handleReferVariable = () => {
  // step1. 将当前的 ProtoInfo 对象和当前的 Row 传递给 VariablesEditor
  const protoInfos = testcaseStore.GET_CURRENT_STEP_MSG(props.type);
  const protoInfo = protoInfos?.[currentTabIndex.value];
  const protoDataItem = currentRow.value;

  testcaseStore.components.variablesEditorRef?.show({
    case_base_id: testcaseStore.baseInfo.id,
    version: testcaseStore.baseInfo.version,
    step_id: testcaseStore.currentStep.id,
    protoInfo,
    protoDataItem
  });
};

// 自动查询Code的值并显示
const handleCodeChanged = (code, item) => {
  item.code_desc = "";
  testcaseStore.getCodeDesc({
    onSucceed: data => {
      item.code_desc = data;
    },
    env: testcaseStore.baseInfo.env,
    code: code
  });
};
</script>

<template>
  <div class="h-full">
    <el-tabs
      class="msg-editor-tab"
      type="border-card"
      v-model="currentTabIndex"
      :addable="isAddable"
      :closable="hasAuth(perms.testcase.detail.writable)"
      @tab-add="handleTabAdd"
      @tab-remove="handleTabRemove"
    >
      <template #addIcon>
        <el-icon size="34"><AddIcon /></el-icon>
      </template>
      <!-- 为空时 -->
      <el-result
        class="mx-auto h-full"
        v-if="!tabs || tabs.length === 0"
        title="空空如也"
      >
        <template #icon>
          <el-icon size="60"><EmptyIcon /></el-icon>
        </template>
        <template #sub-title>
          <p>单击右上角添加按钮以添加消息</p>
        </template>
      </el-result>
      <!-- tab 内容 -->
      <el-tab-pane
        v-for="(item, index) in tabs"
        :key="item.proto_id"
        :label="`${index + 1}. ${item.proto_name}`"
        :name="index"
        :lazy="true"
      >
        <el-scrollbar class="h-full w-full" v-if="index === currentTabIndex">
          <!-- 协议标题 -->
          <div
            class="mb-2 flex items-center justify-between p-3 rounded-md bg-slate-100 dark:bg-transparent"
          >
            <div class="flex items-center">
              <el-tag size="large">
                <span class="font-bold text-sm">{{ item.proto_message }}</span>
              </el-tag>
              <span class="ml-2 text-sm font-bold text-primary">
                {{ item.proto_name || "未命名协议" }}
              </span>
            </div>
            <div>
              <el-button
                title="查看原始协议"
                class="ml-2"
                type="primary"
                plain
                :icon="View"
                circle
                size="small"
                @click="handleViewProtoContent(item)"
              />
              <el-button
                title="重新加载"
                class="ml-2"
                type="success"
                plain
                :icon="Refresh"
                circle
                size="small"
                @click="handleResetProto(item)"
              />
              <el-tag class="ml-2" type="info" size="large">
                <span class="font-bold text-sm">ID: {{ item.proto_id }}</span>
              </el-tag>
              <el-switch
                class="ml-2"
                style="zoom: 1.2"
                v-model="testcaseStore.shareState.simpleMode"
                inline-prompt
                inactive-color="#a6a6a6"
                active-text="精简模式"
                inactive-text="完整模式"
              />
            </div>
          </div>

          <div v-if="props.type === 'recv'">
            <!-- 校验响应码 -->
            <el-divider content-position="left">
              <el-checkbox
                v-model="enableVerifyCode"
                label="校验响应码"
                size="large"
              />
            </el-divider>
            <div
              v-show="enableVerifyCode"
              class="mb-2 flex items-center justify-between p-2 rounded-md"
            >
              <el-input-number
                clearable
                style="width: 180px; margin-left: 50px"
                type="number"
                :disabled="!hasAuth(perms.testcase.detail.writable)"
                v-model="item.code"
                :controls="false"
                placeholder="请填写预期响应码"
                @change="handleCodeChanged($event, item)"
              />
              <span>
                <span class="text-base font-light text-gray-400">含义：</span>
                <span
                  class="text-base mr-4 font-light"
                  :class="{
                    'text-red-400': item.code_desc == '错误码不存在',
                    'text-yellow-500': item.code != 0,
                    'text-green-400': item.code == 0
                  }"
                >
                  {{ item.code == 0 ? "成功" : item.code_desc }}
                </span>
              </span>
            </div>
            <div class="py-1" />
            <!-- 校验响应参数-->
            <el-divider content-position="left">
              <el-checkbox
                v-model="enableVerifyData"
                label="校验响应值"
                size="large"
              />
            </el-divider>
          </div>

          <el-table
            v-if="enableVerifyData"
            :refname="`${props.type}_proto_table_${index}`"
            :ref="rememberRefs"
            :data="item.proto_data"
            style="width: 100%; margin-bottom: 20px"
            :tree-props="{
              children: 'children'
            }"
            :row-class-name="rowClassName"
            row-key="key"
            table-layout="auto"
            tooltip-effect="light"
            @row-click="handleRowClick"
            @row-contextmenu="handleRowContextMenu"
            fit
          >
            <el-table-column v-if="false" prop="key" label="KEY" width="60" />
            <el-table-column label="" type="" width="40">
              <template #header>
                <!-- item 类型的显示删除按钮-->
                <el-button
                  v-if="false"
                  :disabled="!hasAuth(perms.testcase.detail.writable)"
                  title="所有参数均不校验"
                  type="danger"
                  :icon="CloseBold"
                  circle
                  size="small"
                  @click.stop="setProtoDataAllDeleted(item.proto_data, true)"
                />
              </template>
              <template #default="{ row }">
                <!-- item 类型的显示删除按钮-->
                <el-button
                  v-if="row.modifier === 'item'"
                  :disabled="!hasAuth(perms.testcase.detail.writable)"
                  title="移除子项"
                  type="warning"
                  plain
                  :icon="Minus"
                  circle
                  size="small"
                  @click.stop="handleDeleteRepeatedItem(item.proto_data, row)"
                />
              </template>
            </el-table-column>
            <el-table-column label="参数含义" show-overflow-tooltip>
              <template #default="{ row }">
                <!-- item 类型的时候无需显示名称-->
                <span class="text-base" v-if="row.modifier !== 'item'">
                  {{ row.remark || "无" }}
                </span>
                <span class="text-base text-gray-400/70" v-else>
                  {{ "子项" }}
                </span>
              </template>
            </el-table-column>
            <el-table-column
              label="修饰词"
              v-if="!testcaseStore.shareState.simpleMode"
            >
              <template #default="{ row }">
                <el-tag
                  v-if="row.modifier"
                  :type="row.modifier == 'item' ? 'info' : 'success'"
                  size="large"
                >
                  <span class="text-sm font-semibold">
                    {{ row.modifier }}
                  </span>
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              v-if="!testcaseStore.shareState.simpleMode"
              label="类型"
              prop="type"
            >
              <template #default="{ row }">
                <el-tag
                  type="warning"
                  size="large"
                  v-if="row.type"
                  effect="plain"
                >
                  <span class="text-sm font-semibold">
                    {{ row.type }}
                  </span>
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="参数名" prop="type">
              <template #default="{ row }">
                <span class="text-sm font-semibold text-primary">
                  {{ row.modifier === "item" ? "" : row.field }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作符" width="80">
              <template #default="{ row }">
                <div v-if="row.children && row.children.length" />
                <div v-else>
                  <el-select
                    :disabled="!hasAuth(perms.testcase.detail.writable)"
                    v-model="row.operator"
                    placeholder=""
                    @change="handleOperatorChange($event, row)"
                  >
                    <el-option
                      v-for="item in operatorEnums"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                    />
                  </el-select>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="结果值">
              <template #default="{ row }">
                <el-button
                  v-if="row.modifier === 'repeated'"
                  type="primary"
                  plain
                  :icon="CirclePlus"
                  @click.stop="handleAddRepeatedItem(row)"
                  >添加子项</el-button
                >
                <div v-if="row.modifier !== 'repeated' && !row.children">
                  <div v-if="row.operator === '=' || row.operator === '!='">
                    <!-- A. 引用自定义变量 -->
                    <div v-if="row.refer_name">
                      <el-button-group style="width: 96%">
                        <el-button
                          style="width: calc(100% - 46px)"
                          type="warning"
                          :icon="Connection"
                          plain
                          :disabled="!hasAuth(perms.testcase.detail.writable)"
                          @click.stop="handleChangeRowReference(row)"
                        >
                          <span class="text-sm font-bold mx-2">
                            {{ row.refer_name }}
                          </span>
                        </el-button>
                        <el-button
                          type="warning"
                          :icon="CloseBold"
                          plain
                          :disabled="!hasAuth(perms.testcase.detail.writable)"
                          @click.stop="handleDeleteRowReference(row)"
                        />
                      </el-button-group>
                    </div>
                    <!-- B. 手动填写参数值 -->
                    <div v-else>
                      <!-- 根据字段类型生成不同组件 -->
                      <!-- 数字类型 -->
                      <el-input-number
                        style="width: 96%"
                        :controls="false"
                        v-if="isNumberType(row)"
                        :disabled="!hasAuth(perms.testcase.detail.writable)"
                        v-model="row.value"
                      />
                      <!-- 布尔类型 -->
                      <el-switch
                        v-else-if="row.type === 'bool'"
                        :disabled="!hasAuth(perms.testcase.detail.writable)"
                        v-model="row.value"
                        active-text="true"
                        inactive-text="false"
                        :active-value="true"
                        :inactive-value="false"
                      />
                      <!-- 字符串类型 -->
                      <el-input
                        v-else-if="row.type === 'string'"
                        :disabled="!hasAuth(perms.testcase.detail.writable)"
                        type="textarea"
                        v-model="row.value"
                        placeholder="请输入"
                        style="width: 96%"
                        autosize
                      />
                      <!-- 枚举类型 -->
                      <el-select
                        style="width: 96%"
                        v-else-if="row.choices && row.choices.length > 0"
                        :disabled="!hasAuth(perms.testcase.detail.writable)"
                        v-model="row.value"
                        placeholder="请选择"
                      >
                        <el-option
                          v-for="choice in row.choices"
                          :key="choice.value"
                          :label="`【${choice.value}】 ${
                            choice.comment || choice.name
                          }`"
                          :value="choice.value"
                        />
                      </el-select>
                      <!-- GM 输入助手（仅在GM命令时显示） -->
                      <el-button
                        v-if="
                          isGmReq(row) &&
                          hasAuth(perms.testcase.detail.writable)
                        "
                        size="small"
                        class="mt-1"
                        type="warning"
                        plain
                        @click="handleShowGmHelper(row)"
                      >
                        GM 指令助手
                      </el-button>
                    </div>
                  </div>
                  <div v-else-if="row.operator === 'in'">
                    <ArrayInput
                      v-model="row.value"
                      :disabled="!hasAuth(perms.testcase.detail.writable)"
                      :type="isNumberType(row) ? 'number' : 'text'"
                    />
                  </div>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-scrollbar>
      </el-tab-pane>
    </el-tabs>
    <!-- 协议选择器 -->
    <ProtoSelector
      ref="protoSelectorRef"
      :env="testcaseStore.baseInfo.env"
      :proto-type="props.type === 'send' ? 'request' : 'response'"
      @complete="handleProtoSelectorComplete"
    />
    <!-- 协议原始内容显示 -->
    <ProtoContentDisplayer ref="protoContentDisplayerRef" />
    <!-- Gm输入助手 -->
    <GmHelper
      ref="gmHelperRef"
      :env="testcaseStore.baseInfo.env"
      @complete="handleGmHelperCompleted"
    />
    <!-- 右键菜单-文档：https://github.com/CyberNika/v-contextmenu/blob/main/docs/usage.md -->
    <v-contextmenu ref="contextmenu" autoAdjustPlacement>
      <div
        class="fixed left-0 top-0 bg-transparent"
        style="width: 100vw; height: 100vh; z-index: -1"
        @click.stop="resetContextMenu"
      />
      <div v-show="menuStatus == 0">
        <v-contextmenu-item
          v-if="props.type === 'recv' && isBasicType"
          :hideOnClick="false"
          @click="handleSaveVariable"
        >
          <div class="p-1">
            <el-icon size="12">
              <CirclePlus />
            </el-icon>
            <span class="ml-1">保存为自定义变量</span>
          </div>
        </v-contextmenu-item>
        <v-contextmenu-item
          v-if="props.type === 'recv'"
          :hideOnClick="true"
          @click="handleHideProtoDataItemParam"
        >
          <div class="p-1 text-orange-300">
            <el-icon size="12">
              <CircleClose />
            </el-icon>
            <span class="ml-1">不校验此参数</span>
          </div>
        </v-contextmenu-item>
        <v-contextmenu-item
          v-if="props.type === 'send' && isBasicType"
          @click="handleReferVariable"
        >
          <div class="p-1">
            <el-icon size="12">
              <MagicStick />
            </el-icon>
            <span class="ml-1">引用自定义变量</span>
          </div>
        </v-contextmenu-item>
      </div>

      <div v-show="menuStatus == 1">
        <v-contextmenu-item :hideOnClick="false" disabled>
          <span class="font-bold text-sm">🔰 变量名不能由数字开头</span>
        </v-contextmenu-item>
        <v-contextmenu-divider />
        <v-contextmenu-item :hideOnClick="false">
          <div class="w-56 flex justify-between items-center">
            <span class="text-blue-300 font-bold">变量名：</span>
            <el-input style="width: 70%" v-model="varName" clearable />
          </div>
        </v-contextmenu-item>
        <v-contextmenu-item :hideOnClick="false">
          <div class="w-56 flex justify-between items-center">
            <span class="text-blue-300 font-bold">含义：</span>
            <el-input
              style="width: 70%"
              placeholder="变量含义"
              v-model="varRemark"
              clearable
            />
          </div>
        </v-contextmenu-item>
        <v-contextmenu-divider />
        <v-contextmenu-item :hideOnClick="false">
          <el-button
            class="w-full"
            type="primary"
            plain
            @click="confirmSaveVariable"
          >
            保 存
          </el-button>
        </v-contextmenu-item>
      </div>
    </v-contextmenu>
  </div>
</template>
<style lang="scss" scoped>
.msg-editor-tab {
  height: 100%;
}
:deep(.hideTableRow) {
  display: none;
}
</style>
