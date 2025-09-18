<script setup lang="ts">
import {
  SemiSelect,
  Key,
  CirclePlus,
  Promotion
} from "@element-plus/icons-vue";
import { listMember, manageMember, copyMember } from "@/api/team";
import { ref } from "vue";
import { superRequest } from "@/utils/request";
import TeamMembersAssign from "./teamMembersAssign.vue";
import UserSelector from "@/views/common/selectors/userSelector/index.vue";
import TeamSelector from "@/views/common/selectors/teamSelector/index.vue";
import { useTeamGlobalState } from "../utils/teamStoreStateHook";
import ActiveTeamInfo from "@/views/common/display/activeTeamInfo.vue";
import { perms } from "@/utils/permsCode";
import { hasAuth } from "@/router/utils";

defineOptions({
  name: "TeamMembers"
});

const dataList = ref([]);
const loading = ref(false);

const teamMembersAssign = ref();
const userSelector = ref();
const teamSelector = ref();

async function fetchData() {
  await superRequest({
    apiFunc: listMember,
    onBeforeRequest: () => {
      loading.value = true;
    },
    onSucceed: data => {
      dataList.value = data;
    },
    onCompleted: () => {
      loading.value = false;
    }
  });
}

const handleInviteUsers = () => {
  userSelector.value.show();
};

const handleCopyTeam = () => {
  teamSelector.value.show();
};

const { initWatchTeamId } = useTeamGlobalState();
initWatchTeamId(fetchData);

const getTagType = (roleCode: string) => {
  switch (roleCode) {
    case "admin":
      return "warning";
    case "editor":
      return "success";
    case "disable":
      return "danger";
    default:
      return "info";
  }
};

const handleAssign = (row: any) => {
  teamMembersAssign.value.showAssign(row);
};

async function handleRemove(row: any) {
  const data = {
    operation: "REMOVE",
    users: [row.username]
  };
  await superRequest({
    apiFunc: manageMember,
    apiParams: data,
    enableSucceedMsg: true,
    succeedMsgContent: "删除成功！",
    onSucceed: () => {
      fetchData();
    }
  });
}

async function handleUserSelectorComplete(rows: Array<any>) {
  const data = {
    operation: "ADD",
    users: rows.map(item => item.username)
  };
  await superRequest({
    apiFunc: manageMember,
    apiParams: data,
    enableSucceedMsg: true,
    succeedMsgContent: `成功添加『${rows.length}』位成员！`,
    onSucceed: () => {
      fetchData();
    }
  });
}

async function handleTeamSelectorComplete(row: any) {
  await superRequest({
    apiFunc: copyMember,
    apiParams: { team_id: row.id },
    enableSucceedMsg: true,
    succeedMsgContent: `成功将『${row.name}』中的成员同步至此团队下！`,
    onSucceed: () => {
      fetchData();
    }
  });
}
</script>

<template>
  <el-container class="p-2">
    <el-header class="flex items-center justify-center">
      <el-row class="w-5/6 mx-auto">
        <ActiveTeamInfo>
          <div class="float-right" v-if="hasAuth(perms.myteam.manage.writable)">
            <el-button
              class="ml-7"
              :icon="Promotion"
              size="large"
              @click="handleCopyTeam"
              style="width: 120px"
            >
              导入团队
            </el-button>
            <el-button
              :icon="CirclePlus"
              size="large"
              type="primary"
              @click="handleInviteUsers"
              style="width: 120px"
            >
              添加成员
            </el-button>
          </div>
        </ActiveTeamInfo>
      </el-row>
    </el-header>
    <el-main>
      <el-table
        v-loading="loading"
        :data="dataList"
        row-key="id"
        style="width: 83.3%"
        class="mx-auto"
      >
        <el-table-column label="序号" show-overflow-tooltip>
          <template #default="scope">
            <div style="display: flex; align-items: center">
              <el-icon><timer /></el-icon>
              <span>{{ scope.$index + 1 }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          label="成员"
          prop="chinese_name"
          show-overflow-tooltip
        />
        <el-table-column label="角色" prop="role" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="w-32 flex items-center justify-between">
              <el-tag :type="getTagType(row.role_code)">
                {{ row.role_name }}
              </el-tag>
              <el-button
                v-if="hasAuth(perms.myteam.manage.writable)"
                title="分配角色"
                :icon="Key"
                circle
                plain
                type="primary"
                @click="handleAssign(row)"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="账号" prop="username" show-overflow-tooltip />
        <el-table-column label="手机号" prop="phone" show-overflow-tooltip />
        <el-table-column
          fixed="right"
          label="操作"
          width="180"
          align="center"
          v-if="hasAuth(perms.myteam.manage.writable)"
        >
          <template #default="{ row }">
            <el-popconfirm title="移除此成员?" @confirm="handleRemove(row)">
              <template #reference>
                <el-button
                  title="移除成员"
                  :icon="SemiSelect"
                  circle
                  plain
                  type="danger"
                />
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-main>
  </el-container>
  <TeamMembersAssign
    v-if="hasAuth(perms.myteam.manage.writable)"
    ref="teamMembersAssign"
    @fetch-data="fetchData"
  />
  <UserSelector
    v-if="hasAuth(perms.myteam.manage.writable)"
    ref="userSelector"
    @complete="handleUserSelectorComplete"
  />
  <TeamSelector
    v-if="hasAuth(perms.myteam.manage.writable)"
    ref="teamSelector"
    @complete="handleTeamSelectorComplete"
  />
</template>
