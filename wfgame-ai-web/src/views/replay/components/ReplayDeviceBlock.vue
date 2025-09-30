<script setup lang="ts">
import { defineProps, ref, watch, computed } from "vue";

const props = defineProps<{
  deviceId: string;
  imgBase64?: string; // 新增：图片base64
  disconnected?: boolean; // 新增：断开状态
  errorMsg?: string; // 新增：异常信息
}>();

const showDetail = ref(false);

// 断开时高亮或提示
const isDisconnected = ref(false);
watch(
  () => props.disconnected,
  val => {
    isDisconnected.value = !!val;
  },
  { immediate: true }
);

// 兼容前缀和无前缀的 base64
const imgSrc = computed(() => {
  if (!props.imgBase64) return "";
  return props.imgBase64.startsWith("data:image/")
    ? props.imgBase64
    : `data:image/png;base64,${props.imgBase64}`;
});
</script>
<template>
  <div class="device-block-outer">
    <div class="device-id-bar" :class="{ disconnected: isDisconnected }">
      <span class="device-id">设备ID: {{ deviceId }}</span>
      <button class="device-detail-btn" @click="showDetail = true">详情</button>
    </div>
    <div class="device-block resizable" :class="{ disconnected: isDisconnected }">
      <template v-if="isDisconnected">
        <div class="device-status-error">
          <svg class="disconnect-icon" viewBox="0 0 48 48" width="48" height="48" fill="none">
            <circle cx="24" cy="24" r="22" stroke="#ff4d4f" stroke-width="4" fill="#fff0f0" />
            <path d="M16 32L32 16" stroke="#ff4d4f" stroke-width="4" stroke-linecap="round" />
            <path d="M16 16L32 32" stroke="#ff4d4f" stroke-width="4" stroke-linecap="round" />
          </svg>
          设备已断开{{ props.errorMsg ? "：" + props.errorMsg : "" }}
        </div>
      </template>
      <template v-else-if="props.imgBase64">
        <img :src="imgSrc" class="device-img" />
      </template>
      <template v-else>
        <div>设备信息展示区</div>
      </template>
    </div>
    <el-dialog v-model="showDetail" title="设备详情" width="400px">
      <div style="min-height: 120px">
        <p>
          这里是设备 <b>{{ deviceId }}</b> 的详情内容。
        </p>
        <p>
          假内容：<br />
          设备状态：<span v-if="isDisconnected">离线</span><span v-else>在线</span><br />
          IP：192.168.1.100<br />
          型号：Xiaomi 12<br />
          分辨率：2400x1080<br />
          （后续可自定义填充）
        </p>
      </div>
      <template #footer>
        <el-button @click="showDetail = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<style scoped>
.device-block-outer {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 18px;
}

.device-id-bar {
  width: 320px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  padding: 0 6px 0 10px;
  background: linear-gradient(90deg, #e0e7ff 60%, #f0fdfa 100%);
  border-radius: 10px 10px 0 0;
  min-height: 36px;
  transition: background 0.2s;
}

.device-id-bar.disconnected {
  background: #ffeaea;
}

.device-id {
  font-size: 1.05rem;
  color: #3a4a7c;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.device-detail-btn {
  background: #f4f7ff;
  border: 1px solid #bfcfff;
  border-radius: 6px;
  color: #3a4a7c;
  font-size: 0.98rem;
  padding: 2px 14px;
  cursor: pointer;
  margin-left: 6px;
  transition: background 0.15s, border 0.15s;
}

.device-detail-btn:hover {
  background: #e0e7ff;
  border-color: #7a8cff;
}

.device-block {
  border: 1.5px solid #bfcfff;
  border-radius: 18px;
  padding: 0;
  background: #fff;
  width: 320px;
  height: 640px;
  min-width: 220px;
  min-height: 400px;
  max-width: 800px;
  max-height: 1200px;
  box-shadow: 0 4px 24px rgba(80, 120, 255, 0.1);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.2s;
  overflow: auto;
  resize: both;
}

.device-block.disconnected {
  border-color: #ff4d4f;
  box-shadow: 0 0 8px #ffb3b3;
}

.device-block>div,
.device-block>img {
  flex: 1;
  width: 90%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.05rem;
  color: #4b5563;
}

.device-img {
  max-width: 95%;
  max-height: 95%;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(80, 120, 255, 0.08);
}

.device-status-error {
  color: #ff4d4f;
  font-weight: bold;
  font-size: 1.1rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.disconnect-icon {
  width: 48px;
  height: 48px;
  margin-bottom: 2px;
  display: block;
}
</style>
