<script setup lang="ts">
import { ref } from "vue";
import { Document, Loading } from "@element-plus/icons-vue";
import { generateDeviceReport } from "@/api/devices";
import type { DeviceItem, DeviceReport } from "@/api/devices";
import { superRequest } from "@/utils/request";
import { message } from "@/utils/message";

defineOptions({
  name: "DeviceReportDialog"
});

const dialogVisible = ref(false);
const loading = ref(false);
const selectedDevice = ref<DeviceItem | null>(null);
const reportData = ref<DeviceReport | null>(null);

const showDialog = (device?: DeviceItem) => {
  selectedDevice.value = device || null;
  reportData.value = null;
  dialogVisible.value = true;

  // 自动生成报告
  generateReport();
};

const generateReport = async () => {
  await superRequest({
    apiFunc: generateDeviceReport,
    apiParams: selectedDevice.value?.device_id,
    enableSucceedMsg: true,
    succeedMsgContent: "设备报告生成成功！",
    onBeforeRequest: () => {
      loading.value = true;
    },
    onSucceed: (data: DeviceReport) => {
      reportData.value = data;
    },
    onFailed: () => {
      message("生成设备报告失败", { type: "error" });
    },
    onCompleted: () => {
      loading.value = false;
    }
  });
};

const closeDialog = () => {
  dialogVisible.value = false;
  selectedDevice.value = null;
  reportData.value = null;
};

defineExpose({
  showDialog
});
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="
      selectedDevice ? `${selectedDevice.device_id} 设备报告` : '全设备报告'
    "
    width="800px"
    :draggable="true"
    @close="closeDialog"
  >
    <div v-loading="loading" class="device-report-content">
      <div v-if="!loading && reportData" class="space-y-4">
        <!-- 报告头部信息 -->
        <el-card shadow="never" class="border">
          <template #header>
            <div class="flex items-center">
              <el-icon class="mr-2">
                <Document />
              </el-icon>
              <span class="font-medium">报告信息</span>
            </div>
          </template>

          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span class="text-gray-500">设备ID: </span>
              <el-tag type="info">{{ reportData.device_id }}</el-tag>
            </div>
            <div>
              <span class="text-gray-500">生成时间: </span>
              <span>{{ reportData.generated_at }}</span>
            </div>
            <div v-if="selectedDevice">
              <span class="text-gray-500">设备品牌: </span>
              <span>{{ selectedDevice.brand || "-" }}</span>
            </div>
            <div v-if="selectedDevice">
              <span class="text-gray-500">设备型号: </span>
              <span>{{ selectedDevice.model || "-" }}</span>
            </div>
          </div>
        </el-card>

        <!-- 报告内容 -->
        <el-card shadow="never" class="border">
          <template #header>
            <span class="font-medium">报告详情</span>
          </template>

          <div class="report-data">
            <pre
              class="bg-gray-50 p-4 rounded-lg text-sm overflow-auto max-h-96"
              >{{
                typeof reportData.report_data === "string"
                  ? reportData.report_data
                  : JSON.stringify(reportData.report_data, null, 2)
              }}</pre
            >
          </div>
        </el-card>
      </div>

      <div v-if="loading" class="text-center py-12">
        <el-icon class="animate-spin text-4xl text-primary mb-4">
          <Loading />
        </el-icon>
        <p class="text-gray-500">正在生成设备报告...</p>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end space-x-2">
        <el-button @click="closeDialog">关闭</el-button>
        <el-button
          type="primary"
          :icon="Document"
          :loading="loading"
          @click="generateReport"
        >
          重新生成
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.device-report-content {
  min-height: 200px;
}

.report-data pre {
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
  max-height: 400px;
  overflow-y: auto;
}
</style>
