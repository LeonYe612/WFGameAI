<script setup lang="ts">
import { ref, onUnmounted, provide } from "vue";
import { connectSocket } from "@/views/replay/utils/socket";

// 全局唯一socket，room=global
const socketIO = ref<any>(null);

function initSocketIO(room: { room: string }, options: any) {
  if (socketIO.value) return socketIO.value;
  socketIO.value = connectSocket(room, options);
  return socketIO.value;
}

// 提供全局socket实例
provide("socketIO", socketIO);

// 初始化全局socket，room参数为global
initSocketIO(
  { room: "global" },
  {
    onConnect: () => {
      console.log("[global] 已连接");
    },
    onDisconnect: () => {
      console.log("[global] 已断开");
    },
    onError: err => {
      console.warn("[global] 异常", err);
    },
    onReplay: () => { },
    onSysMsg: (msg, payload) => {
      // 全局广播消息
      console.log("[global] sysMsg", msg, payload);
    }
  }
);

onUnmounted(() => {
  if (socketIO.value) socketIO.value.disconnect();
});
</script>
<template>
  <!-- 该组件无需渲染内容，仅提供全局socket -->
  <div style="display: none" />
</template>
