<!-- 此组件弹出协议列表用于选择协议 -->
<script lang="ts" setup>
import { message } from "@/utils/message";
import { ref, onMounted } from "vue";
import { listProto } from "@/api/testcase";
import { superRequest } from "@/utils/request";
import ComponentPager from "@/components/RePager/index.vue";
import ProtoQuery from "./query.vue";
import { envEnum, protoTypeEnum } from "@/utils/enums";

const props = defineProps({
  env: {
    type: Number,
    default: envEnum.TEST
  },
  branch: {
    type: String,
    default: ""
  },
  protoType: {
    type: String,
    default: protoTypeEnum.REQUEST.value
  },
  envDisabled: {
    type: Boolean,
    default: true
  },
  protoTypeDisabled: {
    type: Boolean,
    default: true
  }
});

defineOptions({
  name: "ProtoSelector"
});

const emit = defineEmits(["complete"]);
const dialogVisible = ref(false);
const title = ref(`请选择Proto协议:`);
const queryForm = {
  page: 1,
  size: 20,
  keyword: "",
  env: props.env,
  ref: props.branch || "",
  proto_type: props.protoType
};
const queryFormRef = ref(queryForm);

const protoTableRef = ref();
const protoQueryRef = ref();
const loading = ref(false);
const detailColumnVisible = ref(false);
const dataList = ref([]);
const dataTotal = ref(0);

const fetchData = async () => {
  await superRequest({
    apiFunc: listProto,
    apiParams: queryForm,
    onBeforeRequest: () => {
      loading.value = true;
    },
    onSucceed: data => {
      dataList.value = data.list;
      dataTotal.value = data.total;
    },
    onCompleted: () => {
      loading.value = false;
      protoTableRef.value?.scrollTo({ top: 0 });
    }
  });
};

onMounted(() => {
  fetchData();
});

const show = (clearSelection = true) => {
  dialogVisible.value = true;
  if (clearSelection && protoTableRef.value) {
    protoTableRef.value.clearSelection();
  }
  queryFormRef.value.proto_type = props.protoType;
  queryFormRef.value.env = props.env;
  queryFormRef.value.keyword = "";
  protoQueryRef.value?.fetchBranchOptions();
  fetchData();
};

const cancel = () => {
  dialogVisible.value = false;
};

const handleShowDetail = val => {
  detailColumnVisible.value = val;
};

const reset = () => {
  protoTableRef.value.clearSelection();
};

const confirm = () => {
  const rows = protoTableRef.value.getSelectionRows();
  if (rows.length === 0) {
    message("尚未选择任何协议", { type: "error" });
    return;
  }
  emit("complete", rows);
  dialogVisible.value = false;
};

const quickImportGm = () => {
  // 自行拼接 rows, 长度为1，id 为 0
  const rows = [
    {
      id: 0
    }
  ];
  emit("complete", rows);
  dialogVisible.value = false;
};

// 判断该行是否可选
const isSelectable = row => {
  const selectedRowsCount =
    protoTableRef?.value?.getSelectionRows().length || 0;
  const selectedColor = "#cee5ff";
  const disabledColor = "#f5f7fa";
  const normalColor = "";

  let result = false;
  // [请求协议] 最多选择一行
  if (props.protoType === "request") {
    // 除了当前选中行，其他行都不可选
    if (selectedRowsCount === 1) {
      const selectedRow = protoTableRef?.value?.getSelectionRows()[0];
      result = row.id === selectedRow.id;
      if (result) {
        row.bgColor = selectedColor;
      } else {
        row.bgColor = disabledColor;
      }
    } else if (selectedRowsCount === 0) {
      row.bgColor = normalColor;
      result = true;
    } else {
      row.bgColor = disabledColor;
      result = false;
    }
  } else {
    // [响应协议] 可以选择多行
    result = true;
    const selectedRows = protoTableRef?.value?.getSelectionRows();
    if (selectedRows.length > 0 && selectedRows.indexOf(row) > -1) {
      row.bgColor = selectedColor;
    } else {
      row.bgColor = normalColor;
    }
  }
  return result;
};

const handleRowClick = row => {
  if (isSelectable(row)) {
    // 在切换前，想快速判断 row 当前是否为选中/未选中状态 ?
    protoTableRef?.value?.toggleRowSelection(row);
  } else {
    message("每个步骤中的【请求类型】协议只能选择一个！", { type: "warning" });
  }
};

const rowStyle = item => {
  return { backgroundColor: item.row.bgColor };
};

defineExpose({ show });
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    width="80vw"
    :draggable="true"
    align-center
  >
    <!-- 查询条件 -->
    <ProtoQuery
      :query-form="queryForm"
      :env-disabled="props.envDisabled"
      :proto-type-disabled="props.protoTypeDisabled"
      @fetch-data="fetchData"
      @reset="reset"
      @show-detail="handleShowDetail"
      ref="protoQueryRef"
    />
    <!-- 表格 -->
    <el-table
      ref="protoTableRef"
      v-loading="loading"
      :data="dataList"
      row-key="id"
      max-height="60vh"
      empty-text="未查询到数据，请先尝试进行协议同步"
      height="60vh"
      fit
      @row-click="handleRowClick"
      :cell-style="{ textAlign: 'left' }"
      :header-cell-style="{
        textAlign: 'left',
        fontWeight: 'bolder'
      }"
      :row-style="rowStyle"
    >
      <el-table-column
        type="selection"
        width="120"
        reserve-selection
        :selectable="isSelectable"
      />
      <el-table-column label="协议号" prop="proto_id" width="150" />
      <el-table-column label="类型" prop="proto_name" width="200">
        <template #default="{ row }">
          <el-tag
            v-if="row.proto_type == protoTypeEnum.REQUEST.value"
            size="large"
            type="warning"
            effect="plain"
          >
            <span class="text-sm font-bold">请求-Req</span>
          </el-tag>
          <el-tag
            v-if="row.proto_type == protoTypeEnum.RESPONSE.value"
            size="large"
            type="success"
            effect="plain"
          >
            <span class="text-sm font-bold">响应-Resp</span>
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="名称" prop="proto_name">
        <template #default="{ row }">
          <span v-if="row.proto_name.includes('📝')">
            <span>
              {{ row.proto_name.split("📝")[0] }}
            </span>
            <el-tag class="bounce" size="large" style="background-color: rgb(64, 158, 255)">
              <span class="text-sm font-bold" style="color: white">
                📝{{ row.proto_name.split("📝")[1] }}
              </span>
            </el-tag>
          </span>
          <span v-else>
            {{ row.proto_name }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="消息" prop="proto_message">
        <template #default="{ row }">
          <span v-if="row.proto_message.includes('📝')">
            <el-tag size="large">
              <span class="text-sm font-bold">
                {{ row.proto_message.split("📝")[0] }}
              </span>
            </el-tag>
            <el-tag class="bounce" size="large" style="background-color: rgb(64, 158, 255)">
              <span class="text-sm font-bold" style="color: white">
                📝{{ row.proto_message.split("📝")[1] }}
              </span>
            </el-tag>
          </span>
          <el-tag v-else size="large">
            <span class="text-sm font-bold">
              {{ row.proto_message }}
            </span>
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column
        v-if="detailColumnVisible"
        label="详情"
        prop="proto_content"
      >
        <template #default="{ row }">
          <div
            style="white-space: pre-line !important"
            class="text-sm text-gray-600 font-thin p-3 bg-yellow-100/80 rounded-md"
          >
            {{ row.proto_content }}
          </div>
        </template>
      </el-table-column>
    </el-table>
    <!-- 分页组件 -->
    <ComponentPager
      :query-form="queryForm"
      :total="dataTotal"
      @fetch-data="fetchData"
    />
    <template #footer>
      <el-button
        v-if="props.protoType === protoTypeEnum.REQUEST.value"
        class="float-left"
        type="success"
        @click="quickImportGm"
        size="large"
        plain
      >
        GM 请求快捷导入
      </el-button>
      <el-button @click="cancel" size="large">取 消</el-button>
      <el-button type="primary" @click="confirm" size="large"> 确定</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.bounce {
  animation: bounceAnimation 1.5s 1;
}

@keyframes bounceAnimation {
  0%,
  20%,
  50%,
  80%,
  100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-25px);
  }
  60% {
    transform: translateY(-15px);
  }
}

</style>
