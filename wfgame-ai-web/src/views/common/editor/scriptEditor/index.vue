<script setup lang="ts">
import { ref } from "vue";
import ScriptDetail from "@/views/scripts/detail/index.vue";
import { useNavigate } from "@/views/common/utils/navHook";
const { navigateToScriptDetail } = useNavigate();

const props = defineProps({
  mode: {
    type: String as () => "_dialog" | "_blank" | "_self",
    default: "_dialog"
  },
  blank: {
    type: Boolean,
    default: false
  }
});

const scriptId = ref<number>(0);
const title = ref("✏️ 编辑脚本");

const dialogVisible = ref(false);
const edit = (
  id?: number,
  mode: "_dialog" | "_blank" | "_self" = props.mode
) => {
  title.value = id ? `✏️ 编辑脚本 ID:${id}` : "新建脚本";
  if (mode === "_dialog") {
    scriptId.value = id || 0;
    dialogVisible.value = true;
  } else if (mode === "_blank") {
    navigateToScriptDetail(id, true);
  } else {
    navigateToScriptDetail(id, false);
  }
};

const onDialogClose = () => {
  scriptId.value = 0;
};

const emit = defineEmits<{
  save: [];
}>();
const onSave = () => {
  // 这里可以添加保存后的逻辑，比如关闭对话框等
  dialogVisible.value = false;
  emit("save");
};

defineExpose({
  edit
});
</script>
<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    width="90vw"
    align-center
    @close="onDialogClose"
  >
    <ScriptDetail :id="scriptId" @save="onSave" />
  </el-dialog>
</template>
