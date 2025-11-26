<script setup lang="ts">
import { listDevices } from "@/api/devices";
import { replayApi } from "@/api/scripts";
import { computed, defineProps, onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import { connectSocket } from "../utils/socket";
import ReplayDeviceBlock from "./ReplayDeviceBlock.vue";
const props = defineProps<{ taskId?: string; deviceIds?: string[] }>();
const route = useRoute();
// 任务ID优先使用传入的 prop，其次使用路由 query/params 的 task_id
const taskIdComputed = computed(() => {
  return (
    props.taskId ||
    (route.query?.task_id as string | undefined) ||
    (route.params?.task_id as string | undefined) ||
    ""
  );
});

const devices = ref<any[]>(
  props.deviceIds?.map(id => ({ device_id: id })) || []
);
const taskSocketIO = ref<any>(null); // 主房间socket
const deviceSocketIO = ref<Record<string, any>>({}); // 设备通道sockets
// 设备状态：{ [deviceId]: { connected, imgBase64, errorMsg, recordText } }
const deviceStates = ref<Record<string, any>>({});

const getDeviceState = (device: any) => {
  const pk = device.id ? String(device.id) : null;
  const serial = device.device_id ? String(device.device_id) : null;
  const s1 = pk ? deviceStates.value[pk] : undefined;
  const s2 = serial ? deviceStates.value[serial] : undefined;
  return { ...(s2 || {}), ...(s1 || {}) };
};

onMounted(async () => {
  const taskId = taskIdComputed.value;
  if (!taskId) {
    /* no-op */
  }
  // 主房间连接（任务级 step 事件）
  if (taskId) {
    taskSocketIO.value = connectSocket(
      { room: `replay_task_${String(taskId)}` },
      {
        onConnect: () => {},
        onDisconnect: () => {},
        onError: (err: any) => {
          // 处理任务房间收到的设备错误（如离线）
          try {
            const payload = (err && err.data) ? err.data : err;
            console.log("TaskSocket onError:", payload);
            if (payload && typeof payload === "object") {
              const serial = String(payload.device || "").trim();
              const msg = String(payload.message || "").trim();
              const reason = String(payload.reason || "");

              if (serial && msg) {
                // 查找对应的 deviceKey
                let targetKey: string | null = null;
                for (const d of devices.value) {
                  const pk = (d as any).id;
                  const did = String((d as any).device_id || "");
                  if (did === serial) {
                    targetKey = pk ? String(pk) : did;
                    break;
                  }
                }

                if (targetKey) {
                  const isOffline = reason === "device_not_connected" || msg.includes("未连接");
                  console.log(`Updating device ${targetKey} error: ${msg}, offline: ${isOffline}`);
                  deviceStates.value[targetKey] = {
                    ...(deviceStates.value[targetKey] || {}),
                    errorMsg: msg,
                    // 如果明确是离线错误，则标记为断开
                    ...(isOffline ? { connected: false } : {})
                  };
                } else {
                  // 找不到设备时，尝试以序列号为 key 存储状态（以便后续匹配）
                  console.warn(`Device ${serial} not found in list, storing under serial`);
                  const isOffline = reason === "device_not_connected" || msg.includes("未连接");
                  deviceStates.value[serial] = {
                    ...(deviceStates.value[serial] || {}),
                    errorMsg: msg,
                    ...(isOffline ? { connected: false } : {})
                  };
                }
              }
            }
          } catch (e) {
            console.error("TaskSocket onError exception:", e);
          }
        },
        onFrame: () => {
          /* 主通道不处理 frame */
        },
        onStep: _step => {},
        onSysMsg: (msg, payload) => {
          try {
            const evt = payload?.event || payload?.msg || msg;
            if (evt === "task_error") {
              const serial = String(
                payload?.device || payload?.data?.device || ""
              ).trim();
              const err = String(
                payload?.error_message ||
                  payload?.message ||
                  payload?.data?.error_message ||
                  payload?.data?.message ||
                  ""
              ).trim();
              if (serial && err) {
                // 在 devices 列表中根据 device_id 或 id 匹配对应条目
                let targetKey: string | null = null;
                for (const d of devices.value) {
                  const pk = (d as any).id;
                  const did = String((d as any).device_id || "");
                  if (did === serial) {
                    targetKey = pk ? String(pk) : did;
                    break;
                  }
                }
                if (targetKey) {
                  deviceStates.value[targetKey] = {
                    ...(deviceStates.value[targetKey] || {}),
                    errorMsg: err
                  };
                } else {
                  // Fallback to serial key
                  deviceStates.value[serial] = {
                    ...(deviceStates.value[serial] || {}),
                    errorMsg: err
                  };
                }
              }
            } else if (evt === "devices_resolved") {
              // 离线/在线设备结果由后端解析后下发
              const found = Array.isArray(payload?.found_devices)
                ? payload.found_devices.map((x: any) => String(x))
                : Array.isArray(payload?.data?.found_devices)
                ? payload.data.found_devices.map((x: any) => String(x))
                : [];
              const offline = Array.isArray(payload?.offline_devices)
                ? payload.offline_devices.map((x: any) => String(x))
                : Array.isArray(payload?.data?.offline_devices)
                ? payload.data.offline_devices.map((x: any) => String(x))
                : [];

              // 确保离线设备也在列表中渲染
              // offline.forEach((serial: string) => {
                 // 仅更新已存在设备的状态，不再自动追加新设备（避免 ID/Serial 不匹配导致重复）
              // });
              // 更新每个设备块的连接与错误状态
              const markState = (
                key: string,
                connected: boolean,
                err: string
              ) => {
                deviceStates.value[key] = {
                  ...(deviceStates.value[key] || {}),
                  connected,
                  errorMsg: err
                };
              };
              devices.value.forEach(d => {
                const key = String((d as any).id ?? d.device_id);
                const serial = String((d as any).device_id ?? (d as any).id);
                if (offline.includes(serial)) {
                  markState(key, false, "设备未连接");
                } else if (found.includes(serial)) {
                  // 已找到：如果此前标记为断开，清空错误
                  markState(key, true, deviceStates.value[key]?.errorMsg || "");
                }
              });
            } else if (evt === "device_status") {
              // 任务房间也会收到设备状态（统一入口）
              const dev = String(
                payload?.device || payload?.data?.device || ""
              );
              const status = String(
                payload?.status || payload?.data?.status || ""
              ).toLowerCase();
              const message = String(
                payload?.message || payload?.data?.message || ""
              );
              if (dev) {
                // 查找对应的 deviceKey (优先使用 ID)
                let targetKey = dev;
                for (const d of devices.value) {
                  const pk = String((d as any).id ?? "");
                  const did = String((d as any).device_id ?? "");
                  if (did === dev || pk === dev) {
                    targetKey = pk || did;
                    break;
                  }
                }
                const key = targetKey;
                const offlineMsg =
                  message ||
                  (status === "unauthorized" ? "设备未授权" : "设备未连接");
                if (status === "online") {
                  deviceStates.value[key] = {
                    ...(deviceStates.value[key] || {}),
                    connected: true,
                    errorMsg: deviceStates.value[key]?.errorMsg || ""
                  };

                } else {
                  deviceStates.value[key] = {
                    ...(deviceStates.value[key] || {}),
                    connected: false,
                    errorMsg: offlineMsg
                  };

                }
              }
            }
          } catch (e) {
            /* ignore */
          }
        }
      }
    );
  }

  // 初次获取设备列表（若未传入）
  if (!props.deviceIds || props.deviceIds.length === 0) {
    try {
      const res: any = await listDevices({ task_id: taskId });
      const raw = Array.isArray(res)
        ? res
        : Array.isArray(res?.devices)
        ? res.devices
        : Array.isArray(res?.data?.devices)
        ? res.data.devices
        : Array.isArray(res?.results)
        ? res.results
        : [];
      devices.value = raw;
    } catch (e) {
      devices.value = [];
    }
  } else {
    devices.value = props.deviceIds.map(id => ({ device_id: id }));
  }

  // 处理从 URL 传递过来的初始离线设备（用于捕获启动瞬间的离线事件）
  const initialOffline = route.query.initial_offline;
  const offlineList = new Set<string>();

  if (initialOffline && typeof initialOffline === 'string') {
    initialOffline.split(',').map(s => s.trim()).filter(Boolean).forEach(s => offlineList.add(s));
  }

  // 尝试从 LocalStorage 读取离线设备（解决 URL 长度限制或时序问题）
  try {
    const key = `replay_offline_${taskId}`;
    const lsOffline = JSON.parse(localStorage.getItem(key) || '[]');
    if (Array.isArray(lsOffline)) {
      lsOffline.forEach(s => offlineList.add(String(s)));
    }
    // 读取后不立即清除，保留几秒以防刷新
    setTimeout(() => localStorage.removeItem(key), 5000);
  } catch (e) { /* ignore */ }

  offlineList.forEach(serial => {
    // 确保设备在列表中
    // 仅更新已存在设备的状态，不再自动追加新设备

    // 标记为离线
    let targetKey: string | null = null;
    for (const d of devices.value) {
      const pk = (d as any).id;
      const did = String((d as any).device_id || "");
      if (did === serial) {
        targetKey = pk ? String(pk) : did;
        break;
      }
    }
    if (targetKey) {
      console.log(`Applying initial offline state for ${targetKey}`);
      deviceStates.value[targetKey] = {
        ...(deviceStates.value[targetKey] || {}),
        connected: false,
        errorMsg: "设备未连接(启动时检测)"
      };
    }
  });

  // 监听 storage 事件，以捕获窗口打开后才写入的离线事件
  const onStorage = (e: StorageEvent) => {
    if (e.key === `replay_offline_${taskId}` && e.newValue) {
      try {
        const newOffline = JSON.parse(e.newValue);
        if (Array.isArray(newOffline)) {
          newOffline.forEach(serial => {
             // 复用标记逻辑
             let targetKey: string | null = null;
             for (const d of devices.value) {
               const pk = (d as any).id;
               const did = String((d as any).device_id || "");
               if (did === serial) {
                 targetKey = pk ? String(pk) : did;
                 break;
               }
             }
             if (targetKey) {
               deviceStates.value[targetKey] = {
                 ...(deviceStates.value[targetKey] || {}),
                 connected: false,
                 errorMsg: "设备未连接(启动时检测)"
               };
             }
          });
        }
      } catch (_) { /* ignore */ }
    }
  };
  window.addEventListener('storage', onStorage);
  onUnmounted(() => window.removeEventListener('storage', onStorage));

  // 同步快照状态（用于回显离线/错误信息）
  try {
    const snapRes: any = await replayApi.snapshot({ task_id: taskId });
    const snapDevices = snapRes?.data?.devices || snapRes?.devices || [];
    snapDevices.forEach((d: any) => {
      const serial = String(d.device || d.device_id || "").trim();
      const err = String(d.error_message || "").trim();
      const status = String(d.status || "").toLowerCase();

      if (serial && (err || status === 'offline')) {
        let targetKey: string | null = null;
        for (const dev of devices.value) {
          const pk = (dev as any).id;
          const did = String((dev as any).device_id || "");
          if (did === serial) {
            targetKey = pk ? String(pk) : did;
            break;
          }
        }
        if (targetKey) {
          deviceStates.value[targetKey] = {
            ...(deviceStates.value[targetKey] || {}),
            errorMsg: err || (status === 'offline' ? '设备已离线' : ''),
            connected: false // 若存在错误信息或离线，默认视为异常
          };
        }
      }
    });
  } catch (e) {
    console.error("Snapshot sync failed", e);
  }

  const attach = (device: any) => {
    const devKey = String(device.id ?? device.device_id);
    const serial = device.device_id;

    // 若为新设备且存在对应的序列号状态（如早期报错），则继承状态
    if (!deviceStates.value[devKey] && device.id && serial && deviceStates.value[serial]) {
      const s = deviceStates.value[serial];
      deviceStates.value[devKey] = {
        connected: s.connected ?? false,
        imgBase64: s.imgBase64 ?? "",
        errorMsg: s.errorMsg ?? "",
        recordText: s.recordText ?? ""
      };
    }

    if (deviceSocketIO.value[devKey]) return; // 已连接
    deviceStates.value[devKey] = deviceStates.value[devKey] || {
      connected: false,
      imgBase64: "",
      errorMsg: "",
      recordText: ""
    };
    const sock = connectSocket(
      { room: `device_${devKey}` },
      {
        onConnect: () => {
          Object.assign(deviceStates.value[devKey], {
            connected: true,
            // 保留 errorMsg（若存在步骤错误）不自动清空，以免瞬间消失；仅断开时清空图片
            imgBase64: deviceStates.value[devKey].imgBase64
          });
        },
        onDisconnect: () => {
          Object.assign(deviceStates.value[devKey], {
            connected: false,
            errorMsg: deviceStates.value[devKey]?.errorMsg || "连接断开"
          });
        },
        onError: err => {
          const payload = (err && err.data) ? err.data : err;
          const msg = payload?.message || (typeof payload === "string" ? payload : "连接异常");
          console.log(`DeviceSocket ${devKey} onError:`, msg);
          deviceStates.value[devKey] = {
            ...(deviceStates.value[devKey] || {}),
            connected: false,
            errorMsg: msg
          };
        },
        onSysMsg: (msg, payload) => {
          try {
            const evt = payload?.event || payload?.msg || msg;
            if (evt === "record" && payload?.data) {
              Object.assign(deviceStates.value[devKey], {
                recordText: payload.data.text || "",
                imgBase64: ""
              });
            }
            // device_error 已改为 onError 处理
            // device_status 已改为单独 status 事件（预留）
          } catch (e) {
            /* ignore */
          }
        }
      }
    );
    // 显式监听 frame 事件（服务端发送 SocketResponse 包装：{event, data, ...}）
    try {
      sock.on("frame", (payload: any) => {
        let base64 = "";
        if (typeof payload === "string") {
          base64 = payload;
        } else if (payload && typeof payload === "object") {
          const d = (payload as any).data;
          if (typeof d === "string") {
            base64 = d;
          } else if (
            d &&
            typeof d === "object" &&
            typeof (d as any).base64 === "string"
          ) {
            base64 = (d as any).base64;
          } else {
            base64 = "";
          }
        }
        if (typeof base64 === "string" && base64.length > 0) {
          Object.assign(deviceStates.value[devKey], {
            imgBase64: base64,
            recordText: ""
          });
        }
      });
      // 预留 status 事件
      sock.on("status", (_payload: any) => {
        // TODO: 处理设备状态变更
      });
    } catch (e) {
      /* ignore bind error */
    }
    deviceSocketIO.value[devKey] = sock;
  };

  devices.value.forEach(d => attach(d));

  // 3s 后重新拉设备，若拿到 pk 则升级连接（断开序列号房间，改连 pk 房间）
  setTimeout(async () => {
    try {
      const res2: any = await listDevices({ task_id: taskId });
      const arr: any[] = Array.isArray(res2) ? res2 : res2?.devices || [];
      arr.forEach(dev => {
        if (
          dev.id &&
          deviceSocketIO.value[dev.device_id] &&
          !deviceSocketIO.value[String(dev.id)]
        ) {
          try {
            deviceSocketIO.value[dev.device_id].disconnect();
          } catch (e) {
            /* ignore */
          }
          delete deviceSocketIO.value[dev.device_id];
          attach(dev);
        }
      });
    } catch (e) {
      /* ignore */
    }
  }, 3000);
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
      <ReplayDeviceBlock
        v-for="device in devices"
        :key="(device as any).id ?? device.device_id"
        :deviceId="(device as any).id ?? device.device_id"
        :imgBase64="getDeviceState(device)?.imgBase64"
        :disconnected="!getDeviceState(device)?.connected"
        :errorMsg="getDeviceState(device)?.errorMsg"
      >
        <template #default>
          <template
            v-if="getDeviceState(device)?.recordText"
          >
            <div class="device-record-text">
              {{ getDeviceState(device).recordText }}
            </div>
          </template>
        </template>
      </ReplayDeviceBlock>
    </div>
  </div>
</template>

<style scoped>
.replay-main {
  padding: 12px 24px 24px 24px; /* 顶部更靠上 */
}

.replay-main h2 {
  font-size: 18px; /* 统一字号 */
  font-weight: 600;
  margin: 0 0 10px 0; /* 往上贴一点并与下方保持适度间距 */
  color: #1e293b; /* 统一颜色 */
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
