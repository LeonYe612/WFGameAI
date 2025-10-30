<template>
  <el-drawer
    v-model="drawerVisible"
    title="设备日志"
    direction="rtl"
    size="25%"
  >
    <div v-infinite-scroll="loadMore" class="log-container">
      <el-timeline class="log-timeline">
        <el-timeline-item
          v-for="log in logs"
          :key="log.id"
          :timestamp="TimeDefault(log.created_at)"
          :type="getLogType(log.level)"
        >
          {{ log.message }}
        </el-timeline-item>
      </el-timeline>
      <div class="log-footer">
        <p v-if="loading">加载中...</p>
        <p v-if="noMore">没有更多了</p>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { getDeviceLogs } from "@/api/devices";
import type { DeviceLogItem } from "@/api/devices";
import { TimeDefault } from "@/utils/time";

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  deviceId: {
    type: Number,
    default: null
  }
});

const emit = defineEmits(["update:modelValue"]);

const drawerVisible = ref(props.modelValue);
const logs = ref<DeviceLogItem[]>([]);
const loading = ref(false);
const noMore = ref(false);
const page = ref(1);
const pageSize = 20;

watch(
  () => props.modelValue,
  val => {
    drawerVisible.value = val;
  }
);

watch(drawerVisible, val => {
  emit("update:modelValue", val);
  if (val && props.deviceId) {
    resetAndLoad();
  }
});

watch(
  () => props.deviceId,
  (newVal, oldVal) => {
    if (newVal !== oldVal && drawerVisible.value) {
      resetAndLoad();
    }
  }
);

const resetAndLoad = () => {
  logs.value = [];
  page.value = 1;
  noMore.value = false;
  loadLogs();
};

const loadLogs = async () => {
  if (loading.value || noMore.value || !props.deviceId) return;
  loading.value = true;
  try {
    const { data } = await getDeviceLogs({
      device: props.deviceId,
      page: page.value,
      size: pageSize
    });
    if (data.items.length > 0) {
      logs.value.push(...data.items);
      page.value++;
    }
    if (logs.value.length >= data.total) {
      noMore.value = true;
    }
  } catch (error) {
    console.error("Failed to load device logs:", error);
  } finally {
    loading.value = false;
  }
};

const loadMore = () => {
  if (!noMore.value) {
    loadLogs();
  }
};

const getLogType = (level: string) => {
  switch (level) {
    case "error":
      return "danger";
    case "warning":
      return "warning";
    case "info":
      return "primary";
    case "debug":
      return "info";
    default:
      return "info";
  }
};
</script>

<style scoped>
.log-container {
  height: 100%;
  overflow: auto;
}
.log-timeline {
  padding: 20px;
}
.log-footer {
  text-align: center;
  color: #999;
  font-size: 14px;
  padding: 10px 0;
}

/* Custom scrollbar style */
.log-container::-webkit-scrollbar {
  width: 6px;
}

.log-container::-webkit-scrollbar-track {
  background: transparent;
}

.log-container::-webkit-scrollbar-thumb {
  background-color: rgba(144, 147, 153, 0.3);
  border-radius: 3px;
  transition: background-color 0.3s;
}

.log-container::-webkit-scrollbar-thumb:hover {
  background-color: rgba(144, 147, 153, 0.5);
}
</style>
