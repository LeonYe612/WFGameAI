<script lang="ts" setup>
import { computed, ref, watch } from "vue";
import { superRequest } from "@/utils/request";
import { listMineTeam } from "@/api/team";
import { categoryApi } from "@/api/scripts";
import { useTeamStore } from "@/store/modules/team";
import { message } from "@/utils/message";

const teamStore = useTeamStore();

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: "请选择目标团队和目录"
  }
});

defineOptions({
  name: "CrossTeamCategorySelector"
});

const emit = defineEmits(["confirm", "update:modelValue", "cancel"]);

const dialogVisible = computed({
  get: () => props.modelValue,
  set: val => emit("update:modelValue", val)
});

const teams = ref<any>([]);
const targetTeamId = ref<number | null>(null);
const categories = ref<any>([]);
const targetCategoryId = ref<number | null>(null);

// 查询可拷贝团队目录选项
const fetchTeams = async () => {
  await superRequest({
    apiFunc: listMineTeam,
    onSucceed: data => {
      teams.value = data;
      // 默认选择当前团队
      const currentTeamId = teamStore?.teamId;
      if (currentTeamId) {
        targetTeamId.value = currentTeamId;
        fetchCategories();
      }
    }
  });
};

const fetchCategories = async () => {
  await superRequest({
    apiFunc: categoryApi.tree,
    apiParams: { team_id: targetTeamId.value },
    onSucceed: data => {
      categories.value = data;
    }
  });
};

const reset = () => {
  teams.value = [];
  categories.value = [];
  targetTeamId.value = null;
  targetCategoryId.value = null;
};

const onTargetTeamIdChange = () => {
  targetCategoryId.value = null;
  if (targetTeamId.value) {
    fetchCategories();
  } else {
    categories.value = [];
  }
};

watch(
  () => props.modelValue,
  newVal => {
    if (newVal) {
      reset();
      fetchTeams();
    }
  }
);

const onConfirm = () => {
  if (!targetTeamId.value) {
    message("请选择目标团队", { type: "error" });
    return;
  }
  if (!targetCategoryId.value) {
    message("请选择目标目录", { type: "error" });
    return;
  }
  emit("confirm", {
    targetTeamId: targetTeamId.value,
    targetCategoryId: targetCategoryId.value
  });
  dialogVisible.value = false;
};

const onCancel = () => {
  emit("cancel");
  dialogVisible.value = false;
};
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="props.title"
    width="500px"
    :draggable="true"
    center
  >
    <el-form label-width="100px" size="large" status-icon>
      <el-row>
        <el-form-item label="目标团队">
          <el-tree-select
            v-model="targetTeamId"
            check-strictly
            clearable
            :data="teams"
            default-expand-all
            highlight-current
            :props="{
              children: 'children',
              label: 'name',
              value: 'id'
            }"
            :render-after-expand="false"
            style="width: 255px"
            @change="onTargetTeamIdChange"
          />
        </el-form-item>
      </el-row>
      <el-row v-if="targetTeamId">
        <el-form-item label="目标目录">
          <el-tree-select
            v-model="targetCategoryId"
            check-strictly
            clearable
            :data="categories"
            default-expand-all
            highlight-current
            :props="{
              children: 'children',
              label: 'name',
              value: 'id'
            }"
            :render-after-expand="false"
            style="width: 255px"
          />
        </el-form-item>
      </el-row>
    </el-form>

    <template #footer>
      <el-button @click="onCancel" size="large" class="px-8">取消</el-button>
      <el-button class="px-8" type="primary" @click="onConfirm" size="large">
        确定
      </el-button>
    </template>
  </el-dialog>
</template>
