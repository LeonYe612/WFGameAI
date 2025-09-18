<script setup lang="ts">
import { ref } from "vue";
import {
  Connection,
  Loading,
  CircleCheck,
  CircleClose
} from "@element-plus/icons-vue";
import { checkUsbConnection } from "@/api/devices";
import type { UsbCheckResult } from "@/api/devices";
import { superRequest } from "@/utils/request";
import { message } from "@/utils/message";

defineOptions({
  name: "UsbCheckDialog"
});

const dialogVisible = ref(false);
const loading = ref(false);
const checkResult = ref<UsbCheckResult | null>(null);

const showDialog = () => {
  checkResult.value = null;
  dialogVisible.value = true;

  // 自动执行USB检查
  performCheck();
};

const performCheck = async () => {
  await superRequest({
    apiFunc: checkUsbConnection,
    enableSucceedMsg: true,
    succeedMsgContent: "USB连接检查完成！",
    onBeforeRequest: () => {
      loading.value = true;
    },
    onSucceed: (data: UsbCheckResult) => {
      checkResult.value = data;
    },
    onFailed: () => {
      message("USB连接检查失败", { type: "error" });
    },
    onCompleted: () => {
      loading.value = false;
    }
  });
};

const closeDialog = () => {
  dialogVisible.value = false;
  checkResult.value = null;
};

const getDeviceStatusIcon = (status: string) => {
  return status === "connected" ? CircleCheck : CircleClose;
};

const getDeviceStatusType = (status: string) => {
  return status === "connected" ? "success" : "danger";
};

const getDeviceStatusText = (status: string) => {
  const statusMap = {
    connected: "已连接",
    disconnected: "未连接",
    unauthorized: "未授权",
    offline: "离线"
  };
  return statusMap[status] || status;
};

defineExpose({
  showDialog
});
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    title="USB连接检查"
    width="600px"
    :draggable="true"
    @close="closeDialog"
  >
    <div v-loading="loading" class="usb-check-content">
      <div v-if="!loading && checkResult" class="space-y-4">
        <!-- 检查结果概要 -->
        <el-card shadow="never" class="border">
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center">
                <el-icon class="mr-2">
                  <Connection />
                </el-icon>
                <span class="font-medium">检查结果</span>
              </div>
              <el-tag
                :type="checkResult.success ? 'success' : 'danger'"
                size="large"
              >
                {{ checkResult.success ? "检查成功" : "检查失败" }}
              </el-tag>
            </div>
          </template>

          <div v-if="checkResult.message" class="mb-4">
            <el-alert
              :title="checkResult.message"
              :type="checkResult.success ? 'success' : 'error'"
              show-icon
              :closable="false"
            />
          </div>

          <div class="text-sm text-gray-600">
            <p>检查时间: {{ new Date().toLocaleString() }}</p>
            <p>发现设备: {{ checkResult.devices?.length || 0 }} 台</p>
          </div>
        </el-card>

        <!-- 设备详情列表 -->
        <el-card
          shadow="never"
          class="border"
          v-if="checkResult.devices?.length > 0"
        >
          <template #header>
            <span class="font-medium">设备详情</span>
          </template>

          <div class="space-y-3">
            <div
              v-for="(device, index) in checkResult.devices"
              :key="index"
              class="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
            >
              <div class="flex items-center space-x-3">
                <el-icon
                  :class="`text-${getDeviceStatusType(device.status)}`"
                  size="20"
                >
                  <component :is="getDeviceStatusIcon(device.status)" />
                </el-icon>

                <div>
                  <div class="font-medium">{{ device.device_id }}</div>
                  <div v-if="device.message" class="text-sm text-gray-500">
                    {{ device.message }}
                  </div>
                </div>
              </div>

              <el-tag :type="getDeviceStatusType(device.status)" size="small">
                {{ getDeviceStatusText(device.status) }}
              </el-tag>
            </div>
          </div>
        </el-card>

        <!-- 无设备提示 -->
        <el-empty
          v-if="checkResult.devices?.length === 0"
          description="未发现USB连接的设备"
          class="py-8"
        />
      </div>

      <div v-if="loading" class="text-center py-12">
        <el-icon class="animate-spin text-4xl text-primary mb-4">
          <Loading />
        </el-icon>
        <p class="text-gray-500">正在检查USB连接...</p>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end space-x-2">
        <el-button @click="closeDialog">关闭</el-button>
        <el-button
          type="primary"
          :icon="Connection"
          :loading="loading"
          @click="performCheck"
        >
          重新检查
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.usb-check-content {
  min-height: 200px;
}

.text-success {
  color: var(--el-color-success);
}

.text-danger {
  color: var(--el-color-danger);
}
</style>
