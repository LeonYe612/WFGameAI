<script setup lang="ts">
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { View } from "@element-plus/icons-vue";
import JsonIcon from "@/assets/svg/json.svg?component";
import { protoGenreEnum } from "@/utils/enums";
import { ref } from "vue";
import JsonProtoParser from "./JsonProtoParser.vue";
const testcaseStore = useTestcaseStoreHook();

defineOptions({
  name: "ProtoOperateBar"
});

const props = defineProps({
  proto: {
    type: Object,
    default: () => {
      return {};
    }
  }
});

// 浏览当前协议文本内容
const handleViewProtoContent = (protoItem: any) => {
  testcaseStore.components.protoContentDisplayerRef?.show(protoItem);
};

const jsonParserVisible = ref(false);
const handleOpenJsonParser = () => {
  jsonParserVisible.value = true;
};
</script>

<template>
  <div
    class="mb-2 flex items-center justify-between p-2 rounded-md dark:bg-transparent"
    :class="{
      'bg-orange-100':
        testcaseStore.currentProtoType === protoGenreEnum.SEND.value,
      'bg-cyan-100':
        testcaseStore.currentProtoType === protoGenreEnum.RECV.value
    }"
  >
    <el-tag class="ml-2 font-mono" type="" size="large">
      <span class="font-bold text-base"> ID: {{ props.proto?.proto_id }} </span>
    </el-tag>
    <div class="flex justify-center items-center ml-3">
      <el-tooltip
        :content="props.proto?.proto_name"
        effect="light"
        placement="top"
      >
        <IconifyIconOnline icon="material-symbols:help-outline" />
      </el-tooltip>
    </div>
    <div class="flex-1 items-center justify-start truncate px-1">
      <span class="text-base font-semibold font-serif text-gray-700">
        {{ props.proto?.proto_message }}
      </span>
    </div>
    <div>
      <el-switch
        v-show="false"
        style="zoom: 1.2"
        v-model="testcaseStore.shareState.simpleMode"
        inline-prompt
        inactive-color="#a6a6a6"
        active-text="精简模式"
        inactive-text="完整模式"
      />
      <el-button-group class="ml-4">
        <el-button
          title="查看原始协议文本"
          class="ml-2"
          plain
          :icon="View"
          @click="handleViewProtoContent(props.proto)"
        />
        <el-button
          v-if="
            testcaseStore.currentProtoType === protoGenreEnum.RECV.value || true
          "
          title="将json文本填充到协议参数中"
          class="ml-2"
          plain
          @click="handleOpenJsonParser"
        >
          <el-icon size="22">
            <JsonIcon />
          </el-icon>
        </el-button>
      </el-button-group>
    </div>
    <JsonProtoParser v-model:show="jsonParserVisible" :proto="props.proto" />
  </div>
</template>

<style scoped></style>
