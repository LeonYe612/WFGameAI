<script setup lang="ts">
import { CirclePlus, Promotion } from "@element-plus/icons-vue";
import { useTeamGlobalState } from "../utils/teamStoreStateHook";
import { ref } from "vue";
import RoleTable from "@/views/sys/role/components/roleTable.vue";
import ActiveTeamInfo from "@/views/common/display/activeTeamInfo.vue";
import { perms } from "@/utils/permsCode";
import { hasAuth } from "@/router/utils";

defineOptions({
  name: "TeamRoles"
});

const { initWatchTeamId } = useTeamGlobalState();
initWatchTeamId(() => {
  roleTableRef.value?.fetchData();
});
const roleTableRef = ref();
const handleEdit = event => {
  roleTableRef.value.handleEdit(event);
};
</script>

<template>
  <el-container class="p-2">
    <el-header class="flex items-center justify-center">
      <el-row class="w-5/6 mx-auto">
        <ActiveTeamInfo>
          <div class="float-right">
            <el-button
              v-if="false"
              class="ml-7"
              :icon="Promotion"
              size="large"
              style="width: 120px"
            >
              同步角色
            </el-button>
            <el-button
              v-if="hasAuth(perms.myteam.manage.writable)"
              :icon="CirclePlus"
              size="large"
              type="primary"
              @click="handleEdit"
              style="width: 120px"
            >
              添加角色
            </el-button>
          </div>
        </ActiveTeamInfo>
      </el-row>
    </el-header>
    <el-main>
      <div class="w-5/6 mx-auto">
        <RoleTable
          ref="roleTableRef"
          :writable="hasAuth(perms.myteam.manage.writable)"
          :is-global="false"
        />
      </div>
    </el-main>
  </el-container>
</template>
