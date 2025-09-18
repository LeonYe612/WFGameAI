<script setup lang="ts">
import { useSysTeamManagement } from "./utils/hook";
import {
  EditPen,
  Delete,
  CirclePlus,
  ZoomIn,
  ZoomOut,
  Refresh
} from "@element-plus/icons-vue";
import FileIcon from "@/assets/svg/file.svg?component";
import TeamIcon from "@/assets/svg/team.svg?component";
import SysTeamManagementEdit from "./components/edit.vue";
import { ref, onMounted } from "vue";
import { useTeamGlobalState } from "@/views/team/mine/utils/teamStoreStateHook";
import { useRouter } from "vue-router";

defineOptions({
  name: "SysTeamManagement"
});

const router = useRouter();
const editRef = ref();
const teamTableRef = ref();

const {
  dataList,
  loading,
  defaultExpandAll,
  handleEdit,
  handleEditChild,
  handleDelete,
  fetchData,
  toggleTableExpansion
} = useSysTeamManagement({ editRef, teamTableRef });
const { switchTeam } = useTeamGlobalState();

const jump = (teamId: number) => {
  switchTeam(teamId);
  router.push({ name: "MineTeamManagement" });
};

onMounted(() => {
  fetchData();
});
</script>

<template>
  <div class="main-content">
    <el-card shadow="always" class="pb-10">
      <!-- Header -->
      <template #header>
        <div class="flex items-center">
          <h3 class="text-info">团队管理</h3>
          <div class="mx-5"><el-divider direction="vertical" /></div>
          <div>
            <el-button
              :icon="CirclePlus"
              size="large"
              type="primary"
              @click="handleEdit($event)"
            >
              添加团队
            </el-button>
          </div>
        </div>
      </template>
      <el-table
        :loading="loading"
        :data="dataList"
        :default-expand-all="defaultExpandAll"
        row-key="id"
        :tree-props="{ children: 'children' }"
        ref="teamTableRef"
        class="mx-auto"
        style="width: 50%"
        table-layout="auto"
      >
        <el-table-column label="名称" width="200" prop="meta.title">
          <template #header>
            <div class="flex items-center">
              <span>名称</span>
              <el-button-group class="ml-2">
                <el-button
                  title="展开所有"
                  type="default"
                  plain
                  size="small"
                  :icon="ZoomIn"
                  @click="toggleTableExpansion(true)"
                />
                <el-button
                  title="合并所有"
                  type="default"
                  plain
                  size="small"
                  :icon="ZoomOut"
                  @click="toggleTableExpansion(false)"
                />
                <el-button
                  title="刷新数据"
                  type="default"
                  plain
                  size="small"
                  :icon="Refresh"
                  @click="fetchData"
                />
              </el-button-group>
            </div>
          </template>
          <template #default="{ row }">
            <div class="inline-flex items-center align-middle justify-start">
              <el-icon :size="22">
                <FileIcon v-if="row.genre == 1" />
                <TeamIcon v-if="row.genre == 2" />
              </el-icon>
              <el-icon />
              <span v-if="row.genre == 1">{{ row.name }}</span>
              <span
                v-else
                class="text-blue-400 cursor-pointer"
                @click="jump(row.id)"
                >{{ row.name }}</span
              >
            </div>
          </template>
        </el-table-column>

        <el-table-column align="center" label="类型" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.genre == 1" type="warning" effect="plain"
              >目录</el-tag
            >
            <el-tag v-if="row.genre == 2" effect="plain">团队</el-tag>
          </template>
        </el-table-column>
        <el-table-column align="center" label="排序" prop="queue" width="140" />
        <el-table-column align="center" fixed="right" label="操作" width="200">
          <template #default="{ row }">
            <div class="flex justify-end items-center">
              <el-button
                circle
                plain
                type="warning"
                title="添加下级"
                @click="handleEditChild(row)"
                v-show="row.genre == 1"
              >
                <IconifyIconOnline icon="ci:arrow-sub-down-left" />
              </el-button>
              <el-button
                title="编辑"
                :icon="EditPen"
                circle
                plain
                type="primary"
                @click="handleEdit(row)"
              />
              <el-popconfirm title="是否确认删除?" @confirm="handleDelete(row)">
                <template #reference>
                  <el-button
                    title="删除"
                    :icon="Delete"
                    circle
                    plain
                    type="danger"
                  />
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <SysTeamManagementEdit ref="editRef" @fetch-data="fetchData" />
    </el-card>
  </div>
</template>
