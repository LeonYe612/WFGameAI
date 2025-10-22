<script setup lang="ts">
import {
  CaretRight,
  Edit,
  Search,
  InfoFilled,
  ArrowDown
} from "@element-plus/icons-vue";
import FileIcon from "@/assets/svg/file.svg?component";
import ComponentPager from "@/components/RePager/index.vue";
import { useTeamGlobalState } from "@/views/team/hooks/teamStoreStateHook";
import { useScriptListTable } from "@/views/scripts/list/utils/scriptListTablehook";
import { useIconHook } from "@/views/common/hooks/iconHook";
import { Refresh, CirclePlusFilled } from "@element-plus/icons-vue";
import ActiveTeamInfo from "@/views/common/display/activeTeamInfo.vue";
import ScriptMoveDialog from "@/views/scripts/list/components/scriptMoveDialog.vue";
import AcrossTeamCategorySelector from "@/views/scripts/list/components/crossTeamCategorySelector.vue";
import DebugIcon from "@iconify-icons/codicon/debug";
import { useRenderIcon } from "@/components/ReIcon/src/hooks";
import { computed, ref } from "vue";
import { perms } from "@/utils/permsCode";
import { hasAuth } from "@/router/utils";
import { useScriptStoreHook } from "@/store/modules/script";
import { scriptTypeEnum, sortedEnum, includeInLogEnum } from "@/utils/enums";

import ScriptEditor from "@/views/common/editor/scriptEditor/index.vue";
import { TaskRunType } from "@/views/tasks/utils/enums";
const ScriptEditorRef = ref<InstanceType<typeof ScriptEditor> | null>(null);

const props = defineProps({
  // 是否开启只读模式
  readonly: {
    type: Boolean,
    default: false
  },
  // 选择模式: single-单选, multiple-多选, none-不允许选择
  selectMode: {
    type: String as () => "single" | "multiple" | "none",
    default: "multiple"
  },
  // 显示模式: detail-详细, brief-简洁
  displayMode: {
    type: String as () => "detail" | "brief",
    default: "detail"
  }
});

const isDetailMode = computed(() => props.displayMode === "detail");

const _scriptStore = useScriptStoreHook();

defineOptions({
  name: "ScriptlistTable"
});

const emit = defineEmits(["reset", "single-selection-change"]);
const tableRef = ref();
const ScriptMoveDialogRef = ref();

// 查询条件
const queryForm = {
  page: 1,
  size: 20,
  keyword: "",
  type: "",
  category: null,
  version: "",
  is_active: null,
  include_in_log: null
};

const resetQueryForm = () => {
  queryForm.page = 1;
  queryForm.size = 20;
  queryForm.keyword = "";
  queryForm.type = "";
  queryForm.version = "";
  queryForm.is_active = null;
  queryForm.include_in_log = null;
};

const query = ref(queryForm);

const {
  dataList,
  dataTotal,
  loading,
  getCatalogPath,
  selectionRows,
  selectionRowsCount,
  clearSelection,
  fetchData,
  setCatalogPath,
  handleCreate,
  handleExecute,
  handleCopy,
  handleConfirmDelete,
  // handleDebug,
  // handleEdit,
  // handleDelete,
  handleBatchDelete,
  handleBatchCopy,
  handleSwitchLog,
  handleToggleRowSelection
} = useScriptListTable({
  queryForm,
  tableRef
});

const handleRowClick = (row: any) => {
  if (props.selectMode === "none") {
    return;
  }
  if (props.selectMode === "single") {
    tableRef.value?.setCurrentRow(row);
    emit("single-selection-change", row);
    return;
  }
  if (props.selectMode === "multiple") {
    handleToggleRowSelection(row);
  }
};

const handleEditNew = (row: any, mode: any) => {
  ScriptEditorRef.value?.edit(row.id, mode);
};

const { scriptTypeIcon } = useIconHook();
const { initWatchTeamId } = useTeamGlobalState();
initWatchTeamId(fetchData);

const onQueryChanged = (value: any, key: string) => {
  query.value[key] = value;
  fetchData();
};

// 【重置按钮】点击事件
const handleResetClick = () => {
  resetQueryForm();
  clearSelection();
  if (query.value.category) {
    // 如果当前重置时选择了目录，则需要重置目录选择器
    // 目录选择器变更时，会自动 fetchData
    emit("reset");
  } else {
    fetchData();
  }
};

// 【更多操作相关】
const handleMoreOperation = (command: string, row: any) => {
  if (command === "copy") {
    handleCopy(row);
    return;
  }
  if (command === "edit") {
    handleEditNew(row, "_blank");
    return;
  }
  if (command === "delete") {
    handleConfirmDelete(row);
    return;
  }
};

// 【批量操作相关】
const selectedIds = computed(() => {
  return selectionRows.value.map(item => item.id);
});

const handleBatchCommand = (command: string) => {
  if (command === "delete") {
    handleBatchDelete();
    return;
  }
  if (command === "move") {
    ScriptMoveDialogRef.value?.show(queryForm.category, selectedIds.value);
    return;
  }
  if (command === "copy") {
    AcrossTeamCategorySelectorVisible.value = true;
    return;
  }
};

// 【批量拷贝脚本（可跨团队）】
const AcrossTeamCategorySelectorVisible = ref(false);

const onCaseMoveSucceed = () => {
  clearSelection();
  fetchData();
};

defineExpose({
  selectionRows,
  onQueryChanged,
  setCatalogPath,
  clearSelection
});
</script>

<template>
  <el-card class="testcase-card flex flex-col cursor-pointer" shadow="never">
    <!-- Header -->
    <template #header>
      <ActiveTeamInfo :show-team-info="isDetailMode">
        <el-row class="items-center justify-between">
          <!-- 当前目录 -->
          <div class="h-full flex-1 flex items-center" v-if="isDetailMode">
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
            <div class="w-32 mr-1" v-if="isDetailMode">
              <el-select
                size="large"
                v-model="query.type"
                placeholder="脚本类型"
                clearable
                @change="onQueryChanged($event, 'type')"
              >
                <el-option
                  v-for="item in sortedEnum(scriptTypeEnum)"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </div>
            <div class="w-32 mr-1" v-if="isDetailMode">
              <el-select
                size="large"
                v-model="query.include_in_log"
                placeholder="启用日志"
                clearable
                @change="onQueryChanged($event, 'include_in_log')"
              >
                <el-option
                  v-for="item in sortedEnum(includeInLogEnum)"
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
                v-if="!props.readonly && hasAuth(perms.script.list.edit)"
                :icon="CirclePlusFilled"
                size="large"
                type="primary"
                style="width: 120px"
                @click="handleCreate"
              >
                新建脚本
              </el-button>
            </div>
          </div>
        </el-row>
      </ActiveTeamInfo>
    </template>
    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="dataList"
      row-key="id"
      stripe
      fit
      :header-cell-style="{
        textAlign: 'center',
        fontWeight: 'bolder'
      }"
      :highlight-current-row="props.selectMode === 'single'"
      @row-click="handleRowClick"
    >
      <el-table-column
        v-if="props.selectMode === 'multiple'"
        type="selection"
        reserve-selection
        align="center"
      />
      <el-table-column label="ID" prop="id" width="50" align="center" />
      <el-table-column label="名称" align="left">
        <template #default="{ row }">
          <div class="flex items-center">
            <el-icon size="26" class="mr-2">
              <component :is="scriptTypeIcon(row.type)" />
            </el-icon>
            <span class="text-base"> {{ row.name }} </span>
          </div>
        </template>
      </el-table-column>
      <!-- <el-table-column label="运行次数" prop="execute_total" /> -->
      <el-table-column width="120" align="center">
        <template #header>
          <div class="flex items-center justify-center">
            <el-popover
              placement="bottom"
              trigger="hover"
              width="220"
              content="启用日志的脚本会在测试报告中显示执行记录"
              effect="dark"
            >
              <template #reference>
                <el-icon class="mr-1">
                  <InfoFilled />
                </el-icon>
              </template>
            </el-popover>
            <span>启用日志</span>
          </div>
        </template>
        <template #default="{ row }">
          <div @click.stop>
            <el-switch
              v-if="!props.readonly && hasAuth(perms.script.list.edit)"
              v-model="row.include_in_log"
              :disabled="!hasAuth(perms.script.list.edit)"
              @change="handleSwitchLog(row)"
            />
            <span v-else>{{ row.include_in_log ? "✅" : "-" }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column
        label="步骤数"
        align="center"
        width="100"
        prop="steps_count"
      />
      <el-table-column
        v-if="false"
        label="版本号"
        width="150"
        prop="version"
        align="center"
      >
        <template #default="{ row }">
          <span class="text-base">{{ row.version }}</span>
        </template>
      </el-table-column>
      <el-table-column
        v-if="isDetailMode"
        label="创建信息"
        width="200"
        align="center"
      >
        <template #default="{ row }">
          <div class="flex flex-col">
            <span class="text-base">{{ row.creator_name }}</span>
            <span class="text-sm font-light text-gray-400 mt-1">
              {{ row.created_at }}
            </span>
          </div>
        </template>
      </el-table-column>
      <el-table-column
        v-if="isDetailMode"
        label="最后编辑"
        width="200"
        prop="created_at"
        align="center"
      >
        <template #default="{ row }">
          <div class="flex flex-col">
            <span class="text-base">{{ row.updater_name }}</span>
            <span class="text-sm font-light text-gray-400 mt-1">{{
              row.updated_at
            }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column
        fixed="right"
        label="操作"
        width="220px"
        align="center"
        v-if="!props.readonly"
      >
        <template #default="{ row }">
          <div @click.stop v-if="hasAuth(perms.script.list.edit)">
            <el-button
              title="调试脚本"
              :icon="useRenderIcon(DebugIcon)"
              type="warning"
              plain
              circle
              @click="handleExecute(row, TaskRunType.DEBUG)"
            />
            <el-button
              title="运行脚本"
              :icon="CaretRight"
              type="success"
              plain
              circle
              @click="handleExecute(row, TaskRunType.SINGLE)"
            />
            <el-button
              title="编辑脚本"
              :icon="Edit"
              type="primary"
              plain
              circle
              @click="handleEditNew(row, '_dialog')"
            />
            <el-dropdown @command="handleMoreOperation($event, row)">
              <el-button
                class="ml-3"
                :icon="ArrowDown"
                type="info"
                plain
                circle
              />
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="edit">
                    在新窗口编辑
                  </el-dropdown-item>
                  <el-dropdown-item command="copy">
                    复制当前脚本
                  </el-dropdown-item>
                  <el-dropdown-item command="delete">
                    删除当前脚本
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
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
            <el-dropdown
              @command="handleBatchCommand"
              :disabled="!selectionRowsCount"
            >
              <el-button
                v-if="!props.readonly && hasAuth(perms.script.list.edit)"
                type="primary"
                :disabled="!selectionRowsCount"
              >
                批量操作
                <el-icon class="el-icon--right">
                  <arrow-down />
                </el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="move">移动目录</el-dropdown-item>
                  <el-dropdown-item command="copy">批量拷贝</el-dropdown-item>
                  <el-dropdown-item command="delete">删除脚本</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <div
            v-if="!props.readonly"
            class="flex items-center w-1/2"
            style="margin-left: 10px"
          >
            <!-- 文本或其他内容，占比 50% -->
            <span v-if="selectionRowsCount">
              (已选
              <b class="text-primary mx-1"> {{ selectionRowsCount }} </b>)
            </span>
          </div>
        </div>
      </template>
    </ComponentPager>

    <!-- 移动用例对话框 -->
    <ScriptMoveDialog
      ref="ScriptMoveDialogRef"
      :title="`将 ${selectionRowsCount} 个用例移动到此目录下`"
      @succeed="onCaseMoveSucceed"
    />
    <AcrossTeamCategorySelector
      v-model="AcrossTeamCategorySelectorVisible"
      @confirm="handleBatchCopy"
    />
    <!-- 脚本编辑组件 -->
    <ScriptEditor ref="ScriptEditorRef" @save="fetchData" />
  </el-card>
</template>
<style scoped lang="scss">
.testcase-card :deep() .el-card__body {
  padding: 0 10px;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  .el-table {
    flex: 1;
    min-height: 0;
    .el-table__body tr.current-row > td {
      background: #589cfd !important;
      color: #fff;
      font-weight: bolder;
    }
  }
}
</style>
