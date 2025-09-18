<script setup lang="ts">
import {
  Document,
  Setting,
  VideoPlay,
  Upload,
  Refresh
} from "@element-plus/icons-vue";

defineOptions({
  name: "ScriptsHeader"
});

const emit = defineEmits(["debug", "record", "import", "settings", "refresh"]);

const handleDebug = () => {
  emit("debug");
};

const handleRecord = () => {
  emit("record");
};

const handleImport = () => {
  emit("import");
};

const handleSettings = () => {
  emit("settings");
};

const handleRefresh = () => {
  emit("refresh");
};
</script>

<template>
  <div class="flex items-center justify-between mb-6">
    <div>
      <h3 class="text-info flex items-center text-xl font-bold">
        <el-icon size="24" class="mr-2">
          <Document />
        </el-icon>
        脚本管理
      </h3>
      <p class="text-gray-500 mt-1">管理和执行测试脚本</p>
    </div>
    <div class="flex items-center space-x-2">
      <el-button :icon="Document" size="large" type="info" @click="handleDebug">
        调试脚本
      </el-button>
      <el-button
        :icon="VideoPlay"
        size="large"
        type="warning"
        @click="handleRecord"
      >
        录制脚本
      </el-button>
      <el-button
        :icon="Upload"
        size="large"
        type="success"
        @click="handleImport"
      >
        导入脚本
      </el-button>
      <el-button
        :icon="Setting"
        size="large"
        type="primary"
        @click="handleSettings"
      >
        设置
      </el-button>
      <el-button
        :icon="Refresh"
        size="large"
        type="primary"
        @click="handleRefresh"
      >
        刷新列表
      </el-button>
    </div>
  </div>
</template>
