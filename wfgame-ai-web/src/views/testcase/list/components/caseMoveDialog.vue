<script lang="ts" setup>
import { ref } from "vue";
import { listCatalog, moveCase } from "@/api/testcase";
import { message } from "@/utils/message";
import { superRequest } from "@/utils/request";

const props = defineProps({
  title: {
    type: String,
    default: "移动用例"
  }
});

defineOptions({
  name: "CaseMoveDialog"
});

const emit = defineEmits(["succeed"]);
const catalogId = ref<number | null>(null);
const caseIds = ref([]);
const modalVisible = ref(false);
const submitLoading = ref(false);
const treeData = ref<any>();

// 查询目录选项
const fetchTreeSelectOptions = async () => {
  await superRequest({
    apiFunc: listCatalog,
    onSucceed: data => {
      treeData.value = data;
    }
  });
};

const show = (catalog_id = null, case_ids = []) => {
  // a. 未传入catalogId时, 显示为空
  modalVisible.value = true;
  fetchTreeSelectOptions();
  catalogId.value = catalog_id;
  caseIds.value = case_ids;
};

const close = () => {
  catalogId.value = null;
  caseIds.value = [];
  modalVisible.value = false;
};

const submit = async () => {
  if (!catalogId.value) {
    message("请选择目标目录", { type: "error" });
    return;
  }
  if (!caseIds.value || caseIds.value.length === 0) {
    message("请先勾选用例", { type: "error" });
    return;
  }
  await superRequest({
    apiFunc: moveCase,
    apiParams: {
      catalog_id: catalogId.value,
      case_ids: caseIds.value
    },
    enableSucceedMsg: true,
    onBeforeRequest: () => {
      submitLoading.value = true;
    },
    onSucceed: () => {
      close();
      emit("succeed");
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
        <el-form-item label="目标目录">
          <el-tree-select
            v-model="catalogId"
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
