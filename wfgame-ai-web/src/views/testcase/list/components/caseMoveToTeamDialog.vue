<script lang="ts" setup>
import { ref } from "vue";
import { reuseCaseToTeam } from "@/api/testcase";
import { message } from "@/utils/message";
import { superRequest } from "@/utils/request";
import { listMineActiveTeam } from "@/api/team";
import { useTeamGlobalState } from "@/views/team/mine/utils/teamStoreStateHook";

const props = defineProps({
  title: {
    type: String,
    default: "拷贝用例"
  }
});

defineOptions({
  name: "CaseMoveToTeamDialog"
});

const emit = defineEmits(["succeed"]);
const targetTeamId = ref<number | null>(null);
const idsArray = ref([]);
const modalVisible = ref(false);
const submitLoading = ref(false);
const treeData = ref<any>();
const { switchTeam } = useTeamGlobalState();

// 查询可拷贝团队目录选项
const fetchTreeSelectOptions = async () => {
  await superRequest({
    apiFunc: listMineActiveTeam,
    onSucceed: data => {
      treeData.value = data;
    }
  });
};

const show = (target_team_id = null, ids_array = []) => {
  // a. 未传入targetTeamId时, 显示为空
  modalVisible.value = true;
  fetchTreeSelectOptions();
  targetTeamId.value = target_team_id;
  idsArray.value = ids_array;
};

const close = () => {
  targetTeamId.value = null;
  idsArray.value = [];
  modalVisible.value = false;
};

const submit = async () => {
  if (!targetTeamId.value) {
    message("请选择目标团队", { type: "error" });
    return;
  }
  if (!idsArray.value || idsArray.value.length === 0) {
    message("请先勾选用例", { type: "error" });
    return;
  }
  await superRequest({
    apiFunc: reuseCaseToTeam,
    apiParams: {
      id: targetTeamId.value,
      ids_array: idsArray.value
    },
    enableSucceedMsg: true,
    onBeforeRequest: () => {
      submitLoading.value = true;
    },
    onSucceed: () => {
      // 先切换到拷贝的团队下，再清理环境
      emit("succeed");
      switchTeam(targetTeamId.value);

      close();
    },
    onCompleted: () => {
      submitLoading.value = false;
    }
  });
};

defineExpose({
  show,
  close,
  submit
});
</script>

<template>
  <el-dialog
    v-model="modalVisible"
    :title="props.title"
    width="500px"
    :before-close="close"
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
            :data="treeData"
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
      <el-button @click="close" size="large" class="px-8">取消</el-button>
      <el-button
        class="px-8"
        type="primary"
        @click="submit"
        size="large"
        :loading="submitLoading"
      >
        确定
      </el-button>
    </template>
  </el-dialog>
</template>
