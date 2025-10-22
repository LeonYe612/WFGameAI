<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useRoute } from "vue-router";
import { connectSocket } from "../utils/socket";
import { listDevices } from "@/api/devices";

import { defineProps } from "vue";
const props = defineProps<{ taskId: string; deviceIds: string[] }>();
const taskId = props.taskId;
import ReplayDeviceBlock from "./ReplayDeviceBlock.vue";

const devices = ref<any[]>(
  props.deviceIds?.map(id => ({ device_id: id })) || []
);
const taskSocketIO = ref<any>(null); // 主房间socket
const deviceSocketIO = ref<Record<string, any>>({}); // 设备通道sockets
// 设备状态：{ [deviceId]: { connected, imgBase64, errorMsg, recordText } }
const deviceStates = ref<Record<string, any>>({});

onMounted(async () => {
  // 1. 建立主通道（room为taskId字符串），传递 options，便于区分主通道业务
  taskSocketIO.value = connectSocket(
    { room: String(taskId) },
    {
      onConnect: () => {
        console.log("[主通道] 已连接");
      },
      onDisconnect: () => {
        console.log("[主通道] 已断开");
      },
      onError: err => {
        console.warn("[主通道] 异常", err);
      },
      onReplay: imgBase64 => {
        // 主通道收到 replay 事件
        console.log("[主通道] 收到replay事件", imgBase64);
      },
      onSysMsg: (msg, payload) => {
        // 监听主通道设备信息
        if (payload && payload.event === "device_info" && payload.data) {
          const data = payload.data;
          const idx = devices.value.findIndex(
            d => d.device_id === data.device_id
          );
          if (idx > -1) {
            devices.value[idx] = { ...devices.value[idx], ...data };
          } else {
            devices.value.push(data);
          }
        }
      }
    }
  );

  // 如果未传deviceIds，则自动请求设备列表，否则直接用props.deviceIds
  if (!props.deviceIds || props.deviceIds.length === 0) {
    try {
      const res = await listDevices({ task_id: taskId });
      // 兼容返回数组或对象
      if (Array.isArray(res)) {
        devices.value = res;
      } else if (res && Array.isArray((res as any).devices)) {
        devices.value = (res as any).devices;
      } else {
        devices.value = [];
      }
    } catch (err) {
      devices.value = [];
      console.error("获取设备列表失败", err);
    }
  } else {
    devices.value = props.deviceIds.map(id => ({ device_id: id }));
  }

  // 2. 为每个设备建立独立socket通道
  devices.value.forEach(device => {
    // 每个设备都独立 socket 和 options
    deviceStates.value[device.device_id] = {
      connected: false,
      imgBase64: "",
      errorMsg: "",
      recordText: ""
    };
    const devSocket = connectSocket(
      { room: device.device_id },
      {
        onConnect: () => {
          Object.assign(deviceStates.value[device.device_id], {
            connected: true,
            errorMsg: ""
          });
          console.log(`[设备 ${device.device_id}] 已连接`);
        },
        onDisconnect: () => {
          Object.assign(deviceStates.value[device.device_id], {
            connected: false,
            errorMsg: "连接断开"
          });
          console.log(`[设备 ${device.device_id}] 已断开`);
        },
        onError: err => {
          Object.assign(deviceStates.value[device.device_id], {
            connected: false,
            errorMsg: err && err.message ? err.message : "连接异常"
          });
          console.warn(`[设备 ${device.device_id}] 异常`, err);
        },
        onReplay: imgBase64 => {
          console.log(`[设备 ${device.device_id}] 收到replay事件`, imgBase64);
          Object.assign(deviceStates.value[device.device_id], {
            imgBase64,
            recordText: "无数据"
          });
        },
        onSysMsg: (msg, payload) => {
          if (payload && payload.event === "record" && payload.data) {
            Object.assign(deviceStates.value[device.device_id], {
              recordText: payload.data.text || "",
              imgBase64: ""
            });
            console.log(
              `[设备 ${device.device_id}] 收到record事件`,
              payload.data.text
            );
          }
        }
      }
    );
    deviceSocketIO.value[device.device_id] = devSocket;
  });
});

// 离开时断开所有socket
onUnmounted(() => {
  if (taskSocketIO.value) taskSocketIO.value.disconnect();
  Object.values(deviceSocketIO.value).forEach(s => s && s.disconnect());
});
</script>

<template>
  <div class="replay-main">
    <h2>云真机设备信息</h2>
    <div class="device-list">
      <ReplayDeviceBlock v-for="device in devices" :key="device.device_id" :deviceId="device.device_id"
                         :imgBase64="deviceStates[device.device_id]?.imgBase64"
                         :disconnected="!deviceStates[device.device_id]?.connected" :errorMsg="deviceStates[device.device_id]?.errorMsg">
        <template #default>
          <template v-if="deviceStates[device.device_id]?.recordText">
            <div class="device-record-text">
              {{ deviceStates[device.device_id].recordText }}
            </div>
          </template>
        </template>
      </ReplayDeviceBlock>
    </div>
  </div>
</template>

<style scoped>
.replay-main {
  padding: 24px;
}

.device-list {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.device-record-text {
  color: #1e293b;
  font-size: 1.1rem;
  padding: 12px 8px;
  background: #f5f7fa;
  border-radius: 8px;
  margin: 12px 0;
  word-break: break-all;
  text-align: center;
}
</style>
