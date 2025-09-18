<script lang="ts" setup>
import { message } from "@/utils/message";
import { ref, computed, triggerRef } from "vue";
import {
  listVariables,
  editVariable,
  deleteVariable,
  listVariableRef
} from "@/api/testcase";
import { superRequest } from "@/utils/request";
import { Minus, Search, MagicStick } from "@element-plus/icons-vue";
import { cloneDeep } from "@pureadmin/utils";
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { ElMessageBox } from "element-plus";
const testcaseStore = useTestcaseStoreHook();

defineOptions({
  name: "VariablesEditor"
});

const dialogVisible = ref(false);
const title = ref("📝 自定义变量");

/** table 变量 */
const tableRef = ref(null);
const tableLoading = ref(false);
const tableData = ref([]);
const query = {
  case_base_id: 0,
  version: 1,
  step_id: 0
};
const queryRef = ref(query);
const deleteLoading = ref({});
const editStateRows = ref({});
const keyword = ref("");
const typeFilter = ref("");
const showLocationCol = ref(false);
// show方法传递进来的protoInfo和protoDataItem
const protoInfo = ref(null);
const protoDataItem = ref(null);

// 利用computed 前端过滤row.name 或 row.remark 中包含 keyword 的行
const filteredTableData = computed(() => {
  if (!keyword.value && !typeFilter.value) {
    return tableData.value;
  }
  const filterData = cloneDeep(tableData.value).filter(row => {
    if (row.type === "step") {
      row.children = row.children.filter(child => {
        // a. 不过滤类型，只过滤关键字
        if (!typeFilter.value) {
          return (
            child.name.includes(keyword.value.toLocaleLowerCase()) ||
            child.remark.includes(keyword.value.toLocaleLowerCase())
          );
        }
        // b. 过滤类型和关键字
        return (
          (child.name.includes(keyword.value.toLocaleLowerCase()) ||
            child.remark.includes(keyword.value.toLocaleLowerCase())) &&
          child.type === typeFilter.value
        );
      });
      return row.children?.length > 0;
    }
  });
  return filterData;
});

const getRowStyle = (data: { row: any; rowIndex: number }) => {
  if (data.row.key == protoDataItem.value?.refer_key) {
    return {
      backgroundColor: "#fff6ea"
    };
  }
};

const formatLocation = computed(() => {
  return (location: string) => {
    return location.replace(/\//g, ".").replace(/\.(\d+)/g, "[$1]");
  };
});

// 查询变量列表
const fetcTableData = () => {
  superRequest({
    apiFunc: listVariables,
    apiParams: queryRef.value,
    enableSucceedMsg: false,
    onBeforeRequest: () => {
      tableLoading.value = true;
    },
    onSucceed: data => {
      tableData.value = data || [];
      triggerRef(tableData);
    },
    onCompleted: () => {
      tableLoading.value = false;
    }
  });
};

// row类型为step合并整行显示
const arraySpanMethod = ({ row, columnIndex }) => {
  if (columnIndex == 1 && row.type === "step") {
    return [1, 5];
  }
};

const handleRowClick = row => {
  if (row.type === "step") {
    tableRef.value?.toggleRowExpansion(row);
    return;
  }
};

const handleCancelEditState = () => {
  // 其他行点击的时候，恢复只读模式和值
  Object.keys(editStateRows.value).forEach(key => {
    const item = editStateRows.value[key];
    if (item.enableNameEdit) {
      item.enableNameEdit = false;
      if (item.nameCopy) {
        item.name = item.nameCopy;
      }
    }
    if (item.enableRemarkEdit) {
      item.enableRemarkEdit = false;
      if (item.remarkCopy) {
        item.remark = item.remarkCopy;
      }
    }
    delete editStateRows.value[key];
  });
};

const handleCellDblclick = (row, column) => {
  if (row.type === "step") return;
  if (column.label === "变量名") {
    row.enableNameEdit = true;
    row.nameCopy = row.name;
    editStateRows.value[row.key] = row;
  }
  if (column.label === "含义") {
    row.enableRemarkEdit = true;
    row.remarkCopy = row.remark;
    editStateRows.value[row.key] = row;
  }
};

const handleEdit = (value, row, type: string) => {
  let prop = "";
  if (type === "name") {
    prop = "enableNameEdit";
  }
  if (type === "remark") {
    prop = "enableRemarkEdit";
  }

  // step1. 校验是否为合法变量名
  const pattern = /^[a-zA-Z_][a-zA-Z0-9_]*$/;
  const isValid = pattern.test(row.name);
  if (!isValid) {
    return message("请输入合法的变量名", { type: "warning" });
  }

  // step2. 发送请求保存
  superRequest({
    apiFunc: editVariable,
    apiParams: {
      step_id: row.step_id,
      key: row.key,
      new_name: row.name,
      new_remark: row.remark
    },
    enableSucceedMsg: true,
    succeedMsgContent: "变量修改成功！",
    onSucceed: () => {
      row[prop] = false;
      fetcTableData();
      // step3. 如果修改变量名成功, 判断当前currentStep中是否引用了此变量
      // 如果引用了，前端需要同步刷新显示新的变量名
      if (type !== "name") return;
      testcaseStore.tryUpdateCurrentStepReferFields(row.key, row.name);
    }
  });
};

const handleDeleteVariable = row => {
  gentleDeleteVariable(
    queryRef.value.case_base_id,
    queryRef.value.version,
    row.step_id,
    row.key
  );
};

const handleReferVariable = variable => {
  // step1. 比对当前变量和 protoDataItem 的类型是否一致
  if (variable.type !== protoDataItem.value.type) {
    return message(
      `自定义变量类型(${variable.type})与目标类型(${protoDataItem.value.type})不一致！`,
      { type: "warning" }
    );
  }

  // step2. 记录引用信息至 protoInfo.references 中
  if (!protoInfo.value?.references) {
    protoInfo.value.references = {};
  }

  const locationStr = testcaseStore.findDescriptionPathString(
    protoInfo.value.proto_data,
    protoDataItem.value.key,
    ""
  );

  protoInfo.value.references[locationStr] = variable.key;

  // step3. 需要同步修改 protoDataItem 的 refer_name 和 refer_key 属性，用于前端展示
  protoDataItem.value.refer_name = variable.name;
  protoDataItem.value.refer_key = variable.key;
  dialogVisible.value = false;

  testcaseStore.saveStep();
};

// ====================== 暴露给外部的方法 ===========================
/**
 * 查询指定变量的引用情况
 * @param stepId 步骤id
 * @param key 变量key
 * @param innerCall 是否是内部调用(此方法一并暴露给外部使用)
 */
const queryVariableRef = (
  case_base_id: number,
  version: number,
  stepId: number,
  key: string
) => {
  // step1. 删除前先查询此变量是否存在引用
  superRequest({
    apiFunc: listVariableRef,
    apiParams: {
      case_base_id: case_base_id,
      version: version,
      step_id: stepId,
      key: key
    },
    enableSucceedMsg: false,
    onSucceed: refs => {
      let content = "";
      const refCount = refs?.length || 0;
      if (!refCount) {
        content = "该变量目前没有被任何参数引用！";
      } else {
        content = `此变量目前被 ${refCount} 个参数引用：<br>`;
        refs.forEach(item => {
          content += `◾ Proto-[${item.proto_message}]: ${item.location}<br>`;
        });
      }
      // 二次弹窗确认提示：让用户自己判断是否继续删除
      ElMessageBox.confirm(content, "变量引用", {
        showCancelButton: false,
        showConfirmButton: false,
        cancelButtonText: "删除",
        confirmButtonText: "确定",
        dangerouslyUseHTMLString: true,
        type: "info"
      })
        .then(() => {
          // confirm
        })
        .catch(() => {
          // cancel
        });
    }
  });
};

/**
 * 温和模式删除变量: 删除前会尝试查询自定义变量是否存在引用并给出提示，让用户选择是否删除
 * @param stepId 步骤id
 * @param key 变量key
 * @param innerCall 是否是内部调用(此方法一并暴露给外部使用)
 */
const gentleDeleteVariable = (
  case_base_id: number,
  version: number,
  stepId: number,
  key: string,
  innerCall = true,
  afterDeleteCallback?: Function
) => {
  // step1. 删除前先查询此变量是否存在引用
  superRequest({
    apiFunc: listVariableRef,
    apiParams: {
      case_base_id: case_base_id,
      version: version,
      step_id: stepId,
      key: key
    },
    enableSucceedMsg: false,
    onBeforeRequest: () => {
      if (innerCall) {
        deleteLoading.value[key] = true;
      }
    },
    onSucceed: refs => {
      const refCount = refs?.length || 0;
      let tip = "";
      if (refCount > 0) {
        tip = `当前变量有 <b style='color: orange'>${refCount}</b> 处引用，删除变量将同步删除所有引用，请谨慎删除！`;
      } else {
        tip = `当前变量有 <b style='color: orange'>${refCount}</b> 处引用，可以放心删除！`;
      }
      // 二次弹窗确认提示：让用户自己判断是否继续删除
      ElMessageBox.confirm(tip, "友情提示", {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
        dangerouslyUseHTMLString: true
      })
        .then(() => {
          forceDeleteVariable(stepId, key, innerCall, afterDeleteCallback);
        })
        .catch(() => {
          if (innerCall) {
            delete deleteLoading.value[key];
          }
        });
    }
  });
};

/**
 * 暴力删除变量: 不查询变量引用状态，直接删除自定义变量及其所有引用
 * @param stepId 步骤id
 * @param key 变量key
 * @param innerCall 是否是内部调用(此方法一并暴露给外部使用)
 */

const forceDeleteVariable = (
  stepId: number,
  key: string,
  innerCall = true,
  callback: Function = () => {}
) => {
  superRequest({
    apiFunc: deleteVariable,
    apiParams: {
      step_id: stepId,
      key: key
    },
    enableSucceedMsg: true,
    succeedMsgContent: "变量删除成功！",
    onBeforeRequest: () => {
      if (innerCall) {
        deleteLoading.value[key] = true;
      }
    },
    onSucceed: () => {
      testcaseStore.tryDeleteCurrentStepVariable(key);
      if (innerCall) {
        fetcTableData();
      }
      typeof callback === "function" && callback();
    },
    onCompleted: () => {
      if (innerCall) {
        delete deleteLoading.value[key];
      }
      // 如果删除变量成功, 判断当前currentStep中是否引用了此变量
      // 如果引用了，前端需要同步刷新显示
      testcaseStore.tryUpdateCurrentProtoReferFields(key, "", true);
    }
  });
};

/**
 * 打开自定义变量弹窗
 * @param params
 */
const show = (params: {
  case_base_id: number;
  version: number;
  step_id: number;
  // 引用变量时需要传递进来引用的proto对应 & protoDataItem对象
  protoInfo?: any;
  protoDataItem?: any;
}) => {
  typeFilter.value = "";
  if (params.protoInfo) {
    protoInfo.value = params.protoInfo;
  }
  if (params.protoDataItem) {
    typeFilter.value = params.protoDataItem.type;
    protoDataItem.value = params.protoDataItem;
  }
  dialogVisible.value = true;
  queryRef.value.case_base_id = params.case_base_id;
  queryRef.value.version = params.version;
  queryRef.value.step_id = params.step_id;
  keyword.value = "";
  fetcTableData();
};
defineExpose({
  show,
  gentleDeleteVariable,
  forceDeleteVariable,
  queryVariableRef
});
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    :draggable="true"
    align-center
    @click="handleCancelEditState"
    :width="'65vw'"
  >
    <!-- 操作栏 -->
    <div class="w-full bg-slate-100 h-26 p-2 rounded-lg mb-2 flex items-center">
      <!-- 搜索框 -->
      <div class="w-1/2">
        <el-input
          v-model="keyword"
          size="large"
          placeholder="请输入变量名或含义"
          :prefix-icon="Search"
          clearable
        />
      </div>
      <el-divider direction="vertical" />
      <span class="text-base mx-2 text-gray-500 dark:text-white">
        显示详情：
      </span>
      <el-switch
        class="ml-2"
        style="zoom: 1.2"
        v-model="showLocationCol"
        inline-prompt
        inactive-color="#a6a6a6"
      />
    </div>
    <!-- 表格 -->
    <el-table
      border
      width="100%"
      ref="tableRef"
      :loading="tableLoading"
      :data="filteredTableData"
      row-key="key"
      max-height="65h"
      height="65vh"
      empty-text="暂未定义变量"
      :header-cell-style="{
        fontWeight: 'bolder'
      }"
      :row-style="getRowStyle"
      :cell-style="{ padding: '8px 0' }"
      default-expand-all
      :span-method="arraySpanMethod"
      @row-click="handleRowClick"
      @cell-dblclick="handleCellDblclick"
    >
      <el-table-column lable width="34" />
      <el-table-column label="变量名" width="240" align="left">
        <template #default="{ row }">
          <!-- 步骤名 -->
          <div v-if="row.type == 'step'" class="inline-flex items-center">
            <el-tag size="large" effect="light" circle>
              <span class="text-base font-bold"
                ><i>Step {{ row.location }}</i></span
              >
            </el-tag>
            <span class="text-lg font-bold ml-3 text-primary">
              <i>{{ row.name }}</i>
            </span>
          </div>
          <!-- 变量名 -->
          <div v-else class="inline-flex items-center">
            <!-- 编辑 -->
            <el-input
              v-if="row.enableNameEdit"
              class="text-primary font-bold"
              size="large"
              v-model="row.name"
              clearable
              @click.stop
              @change="handleEdit($event, row, 'name')"
            />
            <!-- 只读 -->
            <span v-else class="text-base font-bold text-black font-serif">{{
              row.name
            }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="含义">
        <template #default="{ row }">
          <div
            v-if="row.type !== 'step'"
            class="w-full inline-flex items-center"
          >
            <!-- 编辑 -->
            <el-input
              v-if="row.enableRemarkEdit"
              class="text-primary font-bold"
              size="large"
              v-model="row.remark"
              clearable
              @click.stop
              @change="handleEdit($event, row, 'remark')"
            />
            <!-- 只读 -->
            <span v-else class="text-base font-bold text-gray-500 font-serif">
              {{ row.remark }}
            </span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="引用地址" v-if="showLocationCol" width="440">
        <template #default="{ row }">
          <div v-if="row.type !== 'step'" class="inline-flex flex-col">
            <div>
              <el-tag plain class="w-14" round>Proto</el-tag>
              <span class="text-sm font-bold ml-2 text-primary">
                {{ `${row.proto_message} (ProtoId:${row.proto_id})` }}
              </span>
            </div>
            <div class="mt-1">
              <el-tag type="info" plain class="w-14" round>Param</el-tag>
              <span class="text-sm font-light ml-1 text-gray-500">
                {{ formatLocation(row.location) }}
              </span>
            </div>
            <div class="mt-1">
              <el-tag type="warning" plain class="w-14" round>Key</el-tag>
              <span class="text-sm font-light ml-1 text-orange-300">
                {{ row.key }}
              </span>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          <div
            v-if="row.type !== 'step'"
            class="w-full inline-flex items-center"
          >
            <el-tag effect="plain" circle type="warning">
              <span class="text-base"
                ><i>{{ row.type }}</i></span
              >
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button
            title="删除变量"
            :icon="Minus"
            :loading="deleteLoading[row.key] || false"
            v-if="row.type !== 'step' && !query.step_id"
            type="danger"
            plain
            circle
            @click="handleDeleteVariable(row)"
          />
          <el-button
            title="引用变量"
            :icon="MagicStick"
            :loading="deleteLoading[row.key] || false"
            v-if="row.type !== 'step' && query.step_id"
            type="success"
            plain
            round
            @click="handleReferVariable(row)"
            >引 用</el-button
          >
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>
</template>
