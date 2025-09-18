<script setup lang="ts">
import { ref } from "vue";
defineOptions({
  name: "ProtoContentDisplayer"
});
const contents = ref([]);
const dialogVisible = ref(false);
const title = ref("Proto原始内容");

const show = (protoItem: any) => {
  dialogVisible.value = true;
  title.value = `【${protoItem.proto_id}】${protoItem.proto_name}-${protoItem.proto_message}`;
  contents.value = protoItem.proto_contents;
};

defineExpose({
  show
});
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    width="32vw"
    :draggable="true"
    align-center
    :modal="false"
  >
    <div class="w-full p-2" style="height: 56vh">
      <el-scrollbar class="h-full">
        <p
          class="p-2 bg-yellow-100 mt-2 rounded-lg font-thin"
          v-for="(content, idx) in contents"
          :key="idx"
          style="white-space: pre-wrap; line-height: 26px"
        >
          {{ content }}
        </p>
      </el-scrollbar>
    </div>
  </el-dialog>
</template>

<style scoped></style>
