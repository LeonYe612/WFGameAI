<!-- 此组件弹出用例列表用于选择用例 -->
<script lang="ts" setup>
import { message } from "@/utils/message";
import { ref, computed, nextTick } from "vue";
import { listCase } from "@/api/testcase";
import { superRequest } from "@/utils/request";
import ComponentPager from "@/components/RePager/index.vue";
import TestcaseQuery from "./query.vue";
import CatalogTreeTableSelector from "@/views/testcase/list/components/catalogSelector.vue";

defineOptions({
  name: "TestcaseSelector"
});

const emit = defineEmits(["complete"]);
const dialogVisible = ref(false);
const title = ref(`请选择测试用例：`);
const queryForm = {
  page: 1,
  size: 20,
  keyword: "",
  env: null,
  catalog_id: null
};
const queryFormRef = ref(queryForm);
const testcaseTable = ref();
const catalogSelectorRef = ref();
const caseQueryRef = ref();
const loading = ref(false);
const dataList = ref([]);
const dataTotal = ref(0);

const fetchData = async () => {
  superRequest({
    apiFunc: listCase,
    apiParams: queryForm,
    onBeforeRequest: () => {
      loading.value = true;
    },
    onSucceed: data => {
      data.list.forEach(item => {
        item.selectedVersion = item.version;
      });
      dataList.value = data.list;
      dataTotal.value = data.total;
    },
    onCompleted: () => {
      loading.value = false;
    }
  });
};

const getVersionOptions = computed(() => {
  return version => {
    const versionOptions = [];
    for (let i = 1; i <= version; i++) {
      versionOptions.push({
        label: `第 ${i} 版`,
        value: i
      });
    }
    return versionOptions;
  };
});

const onSelectorChanged = catalog => {
  queryFormRef.value.catalog_id = catalog?.id;
  fetchData();
};

const show = (env: number, clearSelection = true) => {
  dialogVisible.value = true;
  if (clearSelection) {
    testcaseTable.value?.clearSelection();
  }
  queryFormRef.value.env = env;
  nextTick(() => {
    catalogSelectorRef.value?.fetchDataWithMemoryCurrent();
  });
  // fetchData();
};

const cancel = () => {
  dialogVisible.value = false;
};

const onQueryReset = () => {
  testcaseTable.value?.clearSelection();
};

const confirm = () => {
  const rows = testcaseTable.value.getSelectionRows();
  if (rows.length === 0) {
    message("尚未选择任何用例", { type: "error" });
    return;
  }
  emit("complete", rows);
  dialogVisible.value = false;
};

defineExpose({ show });
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    width="72vw"
    :draggable="true"
    align-center
  >
    <el-container class="main-content" style="height: 65vh">
      <el-aside width="25%" class="p-5 pr-0">
        <el-card
          class="h-full flex flex-col"
          body-class="flex-1 overflow-hidden"
          shadow="never"
        >
          <template #header>
            <h3 class="text-info text-center">测试用例</h3>
          </template>
          <CatalogTreeTableSelector
            class="h-full"
            ref="catalogSelectorRef"
            @changed="onSelectorChanged"
          />
        </el-card>
      </el-aside>
      <el-main class="pl-0 h-full">
        <div class="border border-gray-300 rounded h-full">
          <el-container class="h-full">
            <el-header>
              <!-- 查询条件 -->
              <TestcaseQuery
                :query-form="queryForm"
                @fetch-data="fetchData"
                @reset="onQueryReset"
                ref="caseQueryRef"
              />
            </el-header>
            <el-main>
              <!-- 表格 -->
              <el-table
                ref="testcaseTable"
                v-loading="loading"
                :data="dataList"
                row-key="id"
                height="100%"
                stripe
                fit
                :cell-style="{ textAlign: 'center' }"
                :header-cell-style="{
                  textAlign: 'center',
                  fontWeight: 'bolder'
                }"
              >
                <el-table-column
                  type="selection"
                  width="120"
                  reserve-selection
                />
                <el-table-column label="ID" prop="id" width="120" />
                <el-table-column label="名称" prop="name" />
                <el-table-column label="版本" prop="version">
                  <template #default="{ row }">
                    <el-select
                      size="large"
                      v-model="row.selectedVersion"
                      placeholder="版本选择"
                      style="width: 110px; text-align: center"
                    >
                      <el-option
                        v-for="item in getVersionOptions(row.version)"
                        :key="item.value"
                        :label="item.label"
                        :value="item.value"
                      />
                    </el-select>
                  </template>
                </el-table-column>
              </el-table>
            </el-main>
            <el-footer>
              <!-- 分页组件 -->
              <ComponentPager
                :query-form="queryForm"
                :total="dataTotal"
                @fetch-data="fetchData"
              />
            </el-footer>
          </el-container>
        </div>
      </el-main>
    </el-container>

    <template #footer>
      <el-button @click="cancel" size="large">取 消</el-button>
      <el-button type="primary" @click="confirm" size="large"> 确定 </el-button>
    </template>
  </el-dialog>
</template>
