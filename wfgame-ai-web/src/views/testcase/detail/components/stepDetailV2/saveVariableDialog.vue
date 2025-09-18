<script setup lang="ts">
import { ref, computed } from "vue";
import { message } from "@/utils/message";
import { variable } from "./hooks/types";
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { protoGenreEnum } from "@/utils/enums";

defineOptions({ name: "saveVariableDialog" });

const testcaseStore = useTestcaseStoreHook();

const dialogTitle = ref("🎯 新增自定义变量");
const dialogVisible = ref(false);
const loading = ref(false);
const variableList = ref([] as variable[]);
const namePrefix = ref("");
const remarkPrefix = ref("");

const reset = (done: () => void) => {
  done();
};

const cancel = () => {
  dialogVisible.value = false;
};

const batchEdit = () => {
  // 如果填写名称前缀，则校验名称前缀是否合法
  if (namePrefix.value) {
    if (!validVarName(namePrefix.value)) {
      message("变量名前缀不合法，请检查！", { type: "error" });
      return;
    }
  }

  for (let i = 0; i < variableList.value.length; i++) {
    if (namePrefix.value) {
      variableList.value[i].name = `${namePrefix.value}${i}`;
    }
    if (remarkPrefix.value) {
      variableList.value[i].remark = `${remarkPrefix.value}${i}`;
    }
  }
};

/**
 * 点击确认按钮 => 保存自定义变量
 */
const confirm = () => {
  // 防止连击
  loading.value = true;
  setTimeout(() => {
    loading.value = false;
  }, 1000);
  const repeat = {};
  for (let i = 0; i < variableList.value.length; i++) {
    const variable = variableList.value[i];
    // a. 校验变量名是否合法
    if (!validVarName(variable.name)) {
      message(`[${variable.name}] 为非法的变量名，请修改！`, { type: "error" });
      return;
    }
    // b. 校验本次待保存的变量名是否存在重复的变量名
    if (repeat[variable.name]) {
      message(`[${variable.name}] 命名重复，请修改！`, { type: "error" });
      return;
    }
    // c. 保存变量
    if (!testcaseStore.currentProto) {
      message(`未找到当前协议[currentProto]，请修改！`, { type: "error" });
      return;
    }
    if (!testcaseStore.currentProto?.variables) {
      testcaseStore.currentProto.variables = {};
    }
    const newVar = {
      name: variable.name,
      remark: variable.remark,
      location: variable.location,
      value: variable.value,
      type: variable.type,
      key: variable.key
    };
    testcaseStore.currentProto.variables[variable.name] = newVar;
    repeat[variable.name] = true; // 避免重复添加
  }
  testcaseStore.saveStep({
    onSucceed: () => {
      message(`自定义变量保存成功!`, { type: "success" });
    }
  });
  dialogVisible.value = false;
};

const formatLocation = computed(() => {
  return (location: string) => {
    return location.replace(/\//g, ".").replace(/\.(\d+)/g, "[$1]");
  };
});

const validVarName = (name: string) => {
  const pattern = /^[a-zA-Z_][a-zA-Z0-9_]*$/;
  return pattern.test(name);
};
// ====================== 外部方法 ==========================
/**
 * @description: 打开自定义变量弹窗
 * @param treeNodeList  Tree的Node节点列表
 * @return {*}
 */
const show = (treeNodeList: any[]) => {
  // step0. 只有 Recv 节点才能保存为自定义变量
  if (testcaseStore.currentProtoType !== protoGenreEnum.RECV.value) {
    message("只有响应协议中的参数可以被保存为自定义变量！", { type: "error" });
    return;
  }

  if (!treeNodeList) {
    message("未指定自定义变量的节点！", { type: "error" });
    return;
  }
  // step1.尝试构造表格数据
  // 并进行预校验: 允许保存为自定义变量的Node条件：为基础类型 & 叶子节点 & 可以生成 location
  variableList.value = [];
  let varName = treeNodeList[0].data.field;
  let varIndex = -1;
  for (const node of treeNodeList) {
    const type = node.data?.type;
    if (!testcaseStore.isProto3BasicType(type)) {
      message(`[${node.data.field}]参数非基础类型，无法保存为自定义变量！`, {
        type: "error"
      });
      return;
    }
    if (!node.isLeaf) {
      message(`[${node.data.field}]参数非叶子节点，无法保存为自定义变量！`, {
        type: "error"
      });
      return;
    }
    const location = testcaseStore.getNodeLocation(node);
    if (!location) {
      message(`[${node.data.field}]参数解析位置信息Location失败！`, {
        type: "error"
      });
      return;
    }
    // 初始化的时候自动命名(相同field追加Index后缀treeNodeList)
    let name = node.data.field;
    if (name === varName) {
      varIndex++;
    } else {
      varIndex = 0;
      varName = node.data.field;
    }
    name = `${name}${varIndex}`;

    variableList.value.push({
      name: name,
      remark: node.data.remark?.trim(),
      location: location,
      value: null,
      type: node.data.type,
      key: testcaseStore.uniqueId(),
      treeNode: node
    });
  }
  namePrefix.value = "";
  remarkPrefix.value = "";
  dialogVisible.value = true;
};
defineExpose({ show });
</script>

<template>
  <el-dialog
    :title="dialogTitle"
    v-model="dialogVisible"
    :close-on-click-modal="false"
    width="60vw"
    :draggable="true"
    align-center
    :before-close="reset"
    fit
  >
    <div class="w-full">
      <el-table :data="variableList" style="width: 100%" max-height="50vh">
        <el-table-column align="center" label="序号" type="index" width="60" />
        <el-table-column align="center" label="变量名" width="240">
          <template #default="{ row }">
            <el-input
              size="large"
              style="width: 100%"
              v-model="row.name"
              placeholder="请输入自定义变量名"
              clearable
            />
          </template>
        </el-table-column>
        <el-table-column align="center" label="变量含义" width="240">
          <template #default="{ row }">
            <el-input
              size="large"
              style="width: 100%"
              v-model="row.remark"
              placeholder="请输入变量含义"
              clearable
            />
          </template>
        </el-table-column>
        <el-table-column align="center" label="类型" width="100">
          <template #default="{ row }">
            <el-tag effect="plain" circle type="warning">
              <span class="text-base"
                ><i>{{ row.type }}</i></span
              >
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column align="center" label="路径描述">
          <template #default="{ row }">
            <span class="text-base text-gray-700 font-mono font-semibold">
              <i>{{ formatLocation(row.location) }}</i>
            </span>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <template #footer>
      <div class="w-full flex items-center">
        <div class="p-2 w-full flex justify-start items-center">
          <el-input
            style="width: 200px"
            v-model="namePrefix"
            placeholder="输入变量名前缀"
            clearable
            size="large"
          />
          <el-divider direction="vertical" />
          <el-input
            style="width: 200px"
            v-model="remarkPrefix"
            placeholder="输入含义前缀"
            clearable
            size="large"
          />
          <el-divider direction="vertical" />
          <el-button @click="batchEdit" type="success" size="large" plain>
            批量命名
          </el-button>
        </div>
        <el-button class="ml-auto" @click="cancel" size="large">
          取 消
        </el-button>
        <el-button
          :loading="loading"
          type="primary"
          @click="confirm"
          size="large"
        >
          确定
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>
<style scoped>
:deep() .el-input__inner {
  font-weight: 500;
  font-size: 16px;
}
</style>
