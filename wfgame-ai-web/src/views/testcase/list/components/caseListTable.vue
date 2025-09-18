<script setup lang="ts">
import {
  CaretRight,
  DataLine,
  Edit,
  CopyDocument,
  Delete,
  Search,
  Switch,
  DocumentCopy,
  Download
} from "@element-plus/icons-vue";
import FileIcon from "@/assets/svg/file.svg?component";
import ComponentPager from "@/components/RePager/index.vue";
import { useTeamGlobalState } from "@/views/team/mine/utils/teamStoreStateHook";
import { useCaseListTable } from "@/views/testcase/list/utils/caseListTablehook";
import { useCaseCommonHook } from "@/views/testcase/list/utils/caseCommonHook";
import { Refresh, CirclePlusFilled } from "@element-plus/icons-vue";
import { TimeDefault } from "@/utils/time";
import ActiveTeamInfo from "@/views/common/display/activeTeamInfo.vue";
import CaseMoveDialog from "@/views/testcase/list/components/caseMoveDialog.vue";
import CaseMoveToTeamDialog from "@/views/testcase/list/components/caseMoveToTeamDialog.vue";
import { ref } from "vue";
import { envEnum, caseTypeEnum, sortedEnum } from "@/utils/enums";
import { perms } from "@/utils/permsCode";
import { hasAuth } from "@/router/utils";
import { useRenderIcon } from "@/components/ReIcon/src/hooks";
import DebugIcon from "@iconify-icons/codicon/debug";
import DebugConfirmer from "@/views/testcase/components/debugConfirmer.vue";
import PlanConfirmer from "@/views/testcase/components/planConfirmer.vue";
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { useTeamStore } from "@/store/modules/team";
import FireJsonInputDialog from "@/views/testcase/detail/components/stepDetailV2/fireJsonInputDialog.vue";

const testcaseStore = useTestcaseStoreHook();
const teamStore = useTeamStore();
defineOptions({
  name: "CaselistTable"
});

const emit = defineEmits(["reset"]);
const tableRef = ref();
const CaseMoveDialogRef = ref();
const CaseCopyToTeamDialogRef = ref();
const fireJsonShow = ref(false);
// 查询条件
const queryForm = {
  page: 1,
  size: 20,
  keyword: "",
  catalog_id: null,
  target_team_id: null,
  env: null,
  type: 0
};

const envOptions = [
  {
    label: "全部环境",
    value: null
  },
  {
    label: "测试环境",
    value: envEnum.TEST
  },
  {
    label: "开发环境",
    value: envEnum.DEV
  }
];
const query = ref(queryForm);

const {
  dataList,
  dataTotal,
  loading,
  delLoadings,
  delLoading,
  copyLoadings,
  exportLoading,
  getCatalogPath,
  selectionRows,
  selectionRowsCount,
  clearSelection,
  fetchData,
  setCatalogPath,
  handleCreate,
  handleDebug,
  handleExecute,
  handleReport,
  handleEdit,
  handleCopy,
  handleDelete,
  handleExport,
  handleDeleteAll
} = useCaseListTable({
  queryForm,
  tableRef
});
const { typeIconRender } = useCaseCommonHook();
const { initWatchTeamId } = useTeamGlobalState();
initWatchTeamId(fetchData);

const onQueryChanged = (value: any, key: string) => {
  query.value[key] = value;
  fetchData();
};

// 【重置按钮】点击事件
const handleResetClick = () => {
  query.value.page = 1;
  query.value.size = 20;
  query.value.keyword = "";
  // query.value.catalog_id = null;
  query.value.env = null;
  query.value.type = caseTypeEnum.ALL.value;
  if (query.value.catalog_id) {
    // 如果当前重置时选择了目录，则需要重置目录选择器
    // 目录选择器变更时，会自动 fetchData
    console.log("重置目录选择器");
    emit("reset");
  } else {
    fetchData();
  }
};

// 【移动用例】点击事件
const handleMoveClick = () => {
  const caseIds = selectionRows.value.map(item => {
    return item.id;
  });
  CaseMoveDialogRef.value?.show(queryForm.catalog_id, caseIds);
};

// 【跨团队拷贝用例】点击事件
const handleCopyToTeamClick = () => {
  const caseIds = selectionRows.value.map(item => {
    return item.id;
  });
  CaseCopyToTeamDialogRef.value?.show(queryForm.target_team_id, caseIds);
};
const onCaseMoveSucceed = () => {
  clearSelection();
  fetchData();
};
// =========== 纸老虎手动导入模块 ===========
// 显示输入弹窗
const handleGenerate = () => {
  fireJsonShow.value = true;
};

defineExpose({
  onQueryChanged,
  setCatalogPath
});
</script>

<template>
  <el-card class="testcase-card flex flex-col" shadow="never">
    <!-- Header -->
    <template #header>
      <ActiveTeamInfo>
        <el-row class="items-center justify-between">
          <div class="h-full flex-1 flex items-center">
            <el-divider direction="vertical" />
            <el-icon size="24" class="mr-2">
              <FileIcon />
            </el-icon>
            <div class="flex-1">
              <div class="w-full text-amber-400 overflow-hidden">
                <div
                  class="whitespace-nowrap overflow-ellipsis overflow-hidden flex items-center"
                >
                  {{ getCatalogPath }}
                </div>
              </div>
            </div>
          </div>
          <div class="flex">
            <div class="w-32 mr-1">
              <el-select
                size="large"
                v-model="query.env"
                placeholder="选择环境"
                @change="onQueryChanged($event, 'env')"
              >
                <el-option
                  v-for="item in envOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </div>
            <div class="w-32 mr-1">
              <el-select
                size="large"
                v-model="query.type"
                placeholder="选择类型"
                @change="onQueryChanged($event, 'type')"
              >
                <el-option
                  v-for="item in sortedEnum(caseTypeEnum)"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </div>
            <div class="w-72 mr-2">
              <el-input
                v-model="query.keyword"
                size="large"
                placeholder="请输入关键字搜索"
                :prefix-icon="Search"
                clearable
                @change="onQueryChanged($event, 'keyword')"
              />
            </div>
            <div>
              <el-button
                :icon="Refresh"
                size="large"
                style="width: 120px"
                @click="handleResetClick"
              >
                重置查询
              </el-button>
              <el-button
                v-if="hasAuth(perms.testcase.list.writable)"
                :icon="CirclePlusFilled"
                size="large"
                type="primary"
                style="width: 120px"
                @click="handleCreate"
              >
                新建用例
              </el-button>
              <el-button
                v-if="
                  hasAuth(perms.testcase.list.writable) &&
                  teamStore.teamFullNames.includes('纸老虎')
                "
                :icon="CirclePlusFilled"
                size="large"
                type="success"
                style="width: 120px"
                @click="handleGenerate"
              >
                生成用例
              </el-button>
              <FireJsonInputDialog
                v-model:show="fireJsonShow"
                @reset="handleResetClick"
              />
            </div>
          </div>
        </el-row>
      </ActiveTeamInfo>
    </template>
    <div>
      <!-- Table -->
      <!-- 表格 -->
      <el-table
        ref="tableRef"
        v-loading="loading"
        max-height="calc(100vh - 270px)"
        height="calc(100vh - 270px)"
        :data="dataList"
        row-key="id"
        stripe
        fit
        :header-cell-style="{
          textAlign: 'center',
          fontWeight: 'bolder'
        }"
      >
        <el-table-column type="selection" reserve-selection align="center" />
        <el-table-column label="ID" prop="id" width="50" align="center" />
        <el-table-column label="名称" align="left">
          <template #default="{ row }">
            <div class="flex items-center">
              <el-icon size="26" class="mr-1">
                <component :is="typeIconRender(row.type)" />
              </el-icon>
              <span class="text-base"> {{ row.name }} </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="环境" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              v-if="row.env === envEnum.TEST"
              type="success"
              effect="light"
              >测试环境
            </el-tag>
            <el-tag
              v-else-if="row.env === envEnum.DEV"
              type="warning"
              effect="light"
              >开发环境
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建信息" width="200" align="center">
          <template #default="{ row }">
            <div class="flex flex-col">
              <span class="text-base">{{ row.created_name }}</span>
              <span class="text-sm font-light text-gray-400 mt-1">{{
                TimeDefault(row.created_at, "YYYY-MM-DD HH:mm:ss")
              }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          label="最后编辑"
          width="200"
          prop="created_at"
          align="center"
        >
          <template #default="{ row }">
            <div class="flex flex-col">
              <span class="text-base">{{ row.updated_name }}</span>
              <span class="text-sm font-light text-gray-400 mt-1">{{
                TimeDefault(row.updated_at, "YYYY-MM-DD HH:mm:ss")
              }}</span>
            </div>
          </template>
        </el-table-column>
        <!-- <el-table-column label="用例步骤" prop="steps_total" /> -->
        <!-- <el-table-column label="运行次数" prop="execute_total" /> -->
        <el-table-column
          label="版本号"
          width="150"
          prop="version"
          align="center"
        >
          <template #default="{ row }">
            <span class="text-base"> 第 {{ row.version }} 版</span>
          </template>
        </el-table-column>
        <el-table-column
          fixed="right"
          label="操作"
          width="300px"
          align="center"
        >
          <template #default="{ row }">
            <el-button
              v-if="hasAuth(perms.testcase.list.writable)"
              title="创建计划"
              :icon="CaretRight"
              type="primary"
              circle
              @click="handleExecute(row)"
            />
            <el-button
              v-if="hasAuth(perms.testcase.list.writable)"
              title="调试用例"
              :icon="useRenderIcon(DebugIcon)"
              type="success"
              plain
              circle
              @click="handleDebug(row)"
            />
            <el-button
              v-if="hasAuth(perms.testcase.list.readable)"
              title="查看报告"
              :icon="DataLine"
              type="warning"
              plain
              circle
              @click="handleReport(row)"
            />
            <el-button
              v-if="
                hasAuth(perms.testcase.list.readable) ||
                hasAuth(perms.testcase.list.writable)
              "
              title="编辑用例"
              :icon="Edit"
              type="primary"
              plain
              circle
              @click="handleEdit(row)"
            />
            <el-button
              v-if="hasAuth(perms.testcase.list.writable)"
              title="复制用例"
              :loading="copyLoadings[row.id]"
              :icon="CopyDocument"
              type="info"
              plain
              circle
              @click="handleCopy(row)"
            />
            <el-popconfirm
              title="是否确认删除?"
              v-if="hasAuth(perms.testcase.list.writable)"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button
                  title="删除用例"
                  :loading="delLoadings[row.id]"
                  :icon="Delete"
                  type="danger"
                  plain
                  circle
                />
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页组件 -->
      <ComponentPager
        :query-form="queryForm"
        :total="dataTotal"
        @fetch-data="fetchData"
      >
        <template #left>
          <div class="flex w-full">
            <div class="flex items-center w-1/4">
              <!-- 按钮或其他内容，占比 25% -->
              <el-button
                v-if="hasAuth(perms.testcase.list.writable)"
                title="将已勾选的用例移动到指定目录下(支持跨页勾选)"
                :icon="Switch"
                plain
                size="large"
                :disabled="!selectionRowsCount"
                @click="handleMoveClick"
              >
                <span class="mr-1"> 移动 </span>
              </el-button>
            </div>
            <div class="flex items-center w-1/5 ml-2">
              <!-- 按钮或其他内容，占比 25% -->
              <el-button
                v-if="hasAuth(perms.testcase.list.writable)"
                title="将已勾选的用例拷贝到指定团队的临时tmp文件夹下(只能在同一个项目操作)"
                :icon="DocumentCopy"
                plain
                size="large"
                :disabled="!selectionRowsCount"
                @click="handleCopyToTeamClick"
              >
                <span class="mr-1"> 拷贝 </span>
              </el-button>
            </div>
            <div class="flex items-center w-1/5 ml-2">
              <el-button
                v-if="hasAuth(perms.testcase.list.writable)"
                :loading="exportLoading"
                title="将用例数据导出下载为离线用例数据"
                :icon="Download"
                plain
                size="large"
                :disabled="!selectionRowsCount"
                @click="handleExport"
              >
                <span class="mr-1"> 导出 </span>
              </el-button>
            </div>
            <div class="flex items-center w-1/5 ml-2">
              <el-button
                v-if="hasAuth(perms.testcase.list.writable)"
                :loading="delLoading"
                title="批量删除选中的所有用例"
                :icon="Delete"
                plain
                size="large"
                :disabled="!selectionRowsCount"
                @click="handleDeleteAll"
              >
                <span class="mr-1"> 删除 </span>
              </el-button>
            </div>
            <div class="flex items-center w-1/2" style="margin-left: 10px">
              <!-- 文本或其他内容，占比 50% -->
              <span v-if="selectionRowsCount">
                (已选<b class="text-primary mx-1">{{ selectionRowsCount }}</b
                >)
              </span>
            </div>
          </div>
        </template>
      </ComponentPager>
    </div>

    <!-- 移动用例对话框 -->
    <CaseMoveDialog
      ref="CaseMoveDialogRef"
      :title="`将 ${selectionRowsCount} 个用例移动到此目录下`"
      @succeed="onCaseMoveSucceed"
    />
    <CaseMoveToTeamDialog
      ref="CaseCopyToTeamDialogRef"
      :title="`将 ${selectionRowsCount} 个用例拷贝到目标团队下（tmp临时目录）`"
      @succeed="onCaseMoveSucceed"
    />
    <!-- 用例调试配置 -->
    <DebugConfirmer v-model="testcaseStore.components.showDebugConfirmer" />
    <!-- 执行计划确认 -->
    <PlanConfirmer v-model="testcaseStore.components.showPlanConfirmer" />
  </el-card>
</template>
<style scoped lang="scss">
.testcase-card :deep() .el-card__body {
  height: 100%;
  flex: 1;
  padding: 0 20px;
}
</style>
