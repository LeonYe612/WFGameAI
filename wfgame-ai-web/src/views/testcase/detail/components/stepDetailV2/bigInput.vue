<script setup lang="ts">
import { ref } from "vue";

const dialogTitle = ref("编辑框");
const dialogVisible = ref(false);
// 打开 Dialog 传入 protoDataItem 的指针，可以让大窗口中的值改变后 同步到 protoDataItem
let p: any;
const text = ref("");
const show = (pointer: any, title: string) => {
  p = pointer;
  text.value = p.value;
  if (title) {
    dialogTitle.value = title;
  }
  dialogVisible.value = true;
};
const change = () => {
  p.value = text.value;
};
const clearP = (done: () => void) => {
  p = null;
  done();
};
// const cancel = () => {
//   dialogVisible.value = false;
//   clearP();
// };
defineExpose({ show });
</script>

<template>
  <el-dialog
    :title="dialogTitle"
    v-model="dialogVisible"
    width="50vw"
    :draggable="true"
    align-center
    :before-close="clearP"
  >
    <div class="w-full h-[50vh] overflow-auto">
      <el-input
        class="text-base font-medium"
        v-model="text"
        style="width: 100%; height: 100%"
        :autosize="{ minRows: 15, maxRows: 30 }"
        type="textarea"
        placeholder="请输入"
        @change="change"
      />
    </div>
    <!-- <template #footer>
      <el-button @click="cancel" size="large">取 消</el-button>
      <el-button type="primary" @click="confirm" size="large"> 确定 </el-button>
    </template> -->
  </el-dialog>
</template>
<style scoped>
:deep() .el-textarea__inner {
  font-size: 20px;
  font-weight: 500;
}
</style>
