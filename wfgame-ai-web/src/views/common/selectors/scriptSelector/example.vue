<!-- 🐝使用示例: 脚本 Script 选择器 -->
<script setup lang="ts">
import { ref } from "vue";
import ScriptSelector from "@/views/common/selectors/scriptSelector/index.vue";
import type { ScriptItem } from "@/api/scripts";
const showScriptSelector = ref(true);
const onConfirm = (selection: ScriptItem[]) => {
  console.log("已选脚本：", selection);
  showScriptSelector.value = false;
};
</script>

<template>
  <div>
    <ScriptSelector v-model="showScriptSelector" @confirm="onConfirm" />
  </div>
</template>
<style></style>
