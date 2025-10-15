<script lang="ts" setup>
import { ref } from "vue";
import { categoryApi, scriptApi } from "@/api/scripts";
import { message } from "@/utils/message";
import { superRequest } from "@/utils/request";

const props = defineProps({
  title: {
    type: String,
    default: "📁 移动至其他目录"
  }
});

defineOptions({
  name: "ScriptMoveDialog"
});

const emit = defineEmits(["succeed"]);
const categoryId = ref<number | null>(null);
const scriptIds = ref([]);
const modalVisible = ref(false);
const submitLoading = ref(false);
const treeData = ref<any>();

// 查询目录选项
const fetchTreeSelectOptions = async () => {
  await superRequest({
    apiFunc: categoryApi.tree,
    onSucceed: data => {
      treeData.value = data;
    }
  });
};

const show = (category_id = null, script_ids = []) => {
  // a. 未传入categoryId时, 显示为空
  modalVisible.value = true;
  fetchTreeSelectOptions();
  categoryId.value = category_id;
  scriptIds.value = script_ids;
};

const close = () => {
  categoryId.value = null;
  scriptIds.value = [];
  modalVisible.value = false;
};

const submit = async () => {
  if (!categoryId.value) {
    message("请选择目标目录", { type: "error" });
    return;
  }
  if (!scriptIds.value || scriptIds.value.length === 0) {
    message("请先勾选用例", { type: "error" });
    return;
  }
  await superRequest({
    apiFunc: scriptApi.move,
    apiParams: {
      category_id: categoryId.value,
      script_ids: scriptIds.value
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
            v-model="categoryId"
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
