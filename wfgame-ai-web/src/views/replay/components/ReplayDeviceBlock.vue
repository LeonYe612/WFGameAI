<script setup lang="ts">
import { getDevice, listDevices, type DeviceItem } from "@/api/devices";
import { superRequest } from "@/utils/request";
import { RefreshLeft } from "@element-plus/icons-vue";
import {
    computed,
    defineProps,
    onBeforeUnmount,
    onMounted,
    ref,
    watch
} from "vue";

const props = withDefaults(
  defineProps<{
    deviceId: string;
    imgBase64?: string; // 图片base64
    disconnected?: boolean; // 断开状态
    errorMsg?: string; // 异常信息
    fitMode?: "contain" | "cover"; // 图片适配模式：等比全显/裁剪铺满
  }>(),
  {
    fitMode: "contain"
  }
);

const showDetail = ref(false);
const detailLoading = ref(false);
const deviceDetail = ref<DeviceItem | null>(null);
const deviceBlockRef = ref<HTMLElement | null>(null);
const headerWidth = ref<number>(0);
const initialWidth = ref<number>(320);
const blockWidth = ref<number>(320);
const aspectRatio = ref<string>("9 / 16");
let imgRatioLocked = false; // 一旦从设备或图片获取到比例，后续不再频繁修改
let resizeObserver: ResizeObserver | null = null;

onMounted(async () => {
  // 根据 deviceId 拉取设备详情，优先走精准详情接口，失败再用列表搜索+精确匹配
  detailLoading.value = true;
  try {
    await superRequest({
      apiFunc: getDevice,
      apiParams: String(props.deviceId),
      enableFailedMsg: false,
      enableErrorMsg: false,
      onSucceed: (data: any) => {
        deviceDetail.value = (data || null) as DeviceItem | null;
      }
    });
    // 若未取到，再回退使用列表搜索
    if (!deviceDetail.value) {
      await superRequest({
        apiFunc: listDevices,
        apiParams: { search: props.deviceId },
        enableFailedMsg: false,
        enableErrorMsg: false,
        onSucceed: (data: any) => {
          const arr = Array.isArray(data)
            ? data
            : Array.isArray(data?.results)
            ? data.results
            : [];
          const match =
            arr.find(
              (d: any) => String(d?.device_id) === String(props.deviceId)
            ) || null;
          deviceDetail.value = match as DeviceItem | null;
        }
      });
    }
  } catch (e) {
    deviceDetail.value = null;
  } finally {
    detailLoading.value = false;
  }
  // 同步标题宽度与可缩放窗口宽度（保留原有可缩放窗口）
  try {
    const el = deviceBlockRef.value;
    if (el && typeof ResizeObserver !== "undefined") {
      const w0 = Math.round(el.offsetWidth);
      headerWidth.value = w0;
      blockWidth.value = w0;
      initialWidth.value = w0;
      resizeObserver = new ResizeObserver(() => {
        // 统一以 offsetWidth（含边框）作为基准，确保与设备框外边一致
        const w = Math.round(el.offsetWidth);
        headerWidth.value = w;
        blockWidth.value = w;
      });
      resizeObserver.observe(el);
    } else if (el) {
      // 兜底：无 ResizeObserver 时，退化为 window.resize
      const update = () => {
        const w = Math.round(el.offsetWidth);
        headerWidth.value = w;
        blockWidth.value = w;
      };
      update();
      initialWidth.value = Math.round(el.offsetWidth);
      window.addEventListener("resize", update);
    }
  } catch (e) {
    // 忽略观测失败
  }
  // 初始化设置容器纵横比（优先使用设备分辨率）
  try {
    const w = Number((deviceDetail.value as any)?.width || 0);
    const h = Number((deviceDetail.value as any)?.height || 0);
    if (w > 0 && h > 0) {
      aspectRatio.value = `${w} / ${h}`;
      imgRatioLocked = true;
    }
  } catch (e) {
    // ignore
  }
});

function resetSize() {
  // 恢复到初始宽度，高度由 aspect-ratio 自动推导
  blockWidth.value = initialWidth.value;
}

onBeforeUnmount(() => {
  try {
    if (resizeObserver) resizeObserver.disconnect();
  } catch (e) {
    // ignore
  }
});

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

// 若设备未提供分辨率，则在首帧图片就绪后用图片天然尺寸设置容器纵横比
watch(
  () => imgSrc.value,
  src => {
    if (!src || imgRatioLocked) return;
    try {
      const img = new Image();
      img.onload = () => {
        if (img.naturalWidth > 0 && img.naturalHeight > 0) {
          aspectRatio.value = `${img.naturalWidth} / ${img.naturalHeight}`;
          imgRatioLocked = true;
        }
      };
      img.src = src;
    } catch (e) {
      // ignore
    }
  },
  { immediate: true }
);

// 设备友好名：优先 brand + model，其次 model，再次 name，最后 deviceId
const displayName = computed(() => {
  const d = deviceDetail.value as any;
  const brand = d?.brand || "";
  const model = d?.model || "";
  const name = d?.name || "";
  if (name) return name;
  if (brand && model) return `${brand} ${model}`;
  if (model) return model;
  return props.deviceId;
});
</script>
<template>
  <div class="device-block-outer">
    <div
      class="device-id-bar"
      :class="{ disconnected: isDisconnected }"
      :style="{ width: headerWidth ? headerWidth + 'px' : undefined }"
    >
      <span class="device-id">设备 {{ deviceId }}：{{ displayName }}</span>
      <div class="device-actions">
        <el-tooltip content="恢复初始尺寸" placement="top">
          <el-button
            class="device-reset-icon"
            :icon="RefreshLeft"
            circle
            size="default"
            type="success"
            plain
            @click="resetSize"
            aria-label="恢复初始尺寸"
          />
        </el-tooltip>
        <button class="device-detail-btn" @click="showDetail = true">
          详情
        </button>
      </div>
    </div>
    <div
      class="device-block"
      :class="{ disconnected: isDisconnected }"
      :style="{ aspectRatio, width: blockWidth + 'px' }"
      ref="deviceBlockRef"
    >
      <template v-if="isDisconnected">
        <div class="device-status-error">
          <svg
            class="disconnect-icon"
            viewBox="0 0 48 48"
            width="48"
            height="48"
            fill="none"
          >
            <circle
              cx="24"
              cy="24"
              r="22"
              stroke="#ff4d4f"
              stroke-width="4"
              fill="#fff0f0"
            />
            <path
              d="M16 32L32 16"
              stroke="#ff4d4f"
              stroke-width="4"
              stroke-linecap="round"
            />
            <path
              d="M16 16L32 32"
              stroke="#ff4d4f"
              stroke-width="4"
              stroke-linecap="round"
            />
          </svg>
          <div class="offline-text">
            <div class="offline-title">📱 设备离线</div>
            <div class="offline-desc">
              {{ props.errorMsg || "设备连接已断开，请检查网络连接" }}
            </div>
            <div class="offline-status">
              状态：离线
            </div>
          </div>
        </div>
      </template>
      <template v-else>
        <div class="device-img-wrap">
          <template v-if="props.imgBase64">
            <img
              :src="imgSrc"
              class="device-img"
              :style="{ objectFit: props.fitMode }"
            />
          </template>
          <template v-else>
            <div class="placeholder">等待画面...</div>
          </template>
          <!-- 错误消息浮层：仅在非断开状态且存在错误消息时显示 -->
          <transition name="fade">
            <div
              v-if="!isDisconnected && props.errorMsg"
              class="device-error-overlay"
              :title="props.errorMsg"
            >
              <div class="err-icon">⚠</div>
              <div class="err-text">{{ props.errorMsg }}</div>
            </div>
          </transition>
        </div>
      </template>
    </div>
    <el-dialog v-model="showDetail" title="设备详情" width="420px">
      <div style="min-height: 140px">
        <div v-if="detailLoading" style="padding: 12px 0; color: #64748b">
          加载中...
        </div>
        <template v-else>
          <p style="margin: 4px 0 10px 0; color: #334155">
            <b>{{ displayName }}</b>
          </p>
          <div class="kv">
            <span class="k">设备ID</span>
            <span class="v">{{ deviceId }}</span>
          </div>
          <div class="kv">
            <span class="k">品牌</span>
            <span class="v">{{ deviceDetail?.brand || "-" }}</span>
          </div>
          <div class="kv">
            <span class="k">型号</span>
            <span class="v">{{ deviceDetail?.model || "-" }}</span>
          </div>
          <div class="kv">
            <span class="k">Android</span>
            <span class="v">{{ deviceDetail?.android_version || "-" }}</span>
          </div>
          <div class="kv">
            <span class="k">IP</span>
            <span class="v">{{ deviceDetail?.ip_address || "-" }}</span>
          </div>
          <div class="kv">
            <span class="k">分辨率</span>
            <span class="v">
              {{
                (deviceDetail?.width || 0) + "x" + (deviceDetail?.height || 0)
              }}
            </span>
          </div>
          <div class="kv">
            <span class="k">状态</span>
            <span class="v">
              <span v-if="isDisconnected">离线</span>
              <span v-else>在线</span>
            </span>
          </div>
        </template>
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
  /* 宽度由 JS 观测到的 device-block 宽度动态设置 */
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0; /* 紧贴下方屏幕框体 */
  padding: 0 6px 0 10px;
  background: linear-gradient(90deg, #e0e7ff 60%, #f0fdfa 100%);
  border: 1.5px solid #bfcfff; /* 明确边界，与设备框一致 */
  border-bottom: 0; /* 与下方设备框拼接，避免双线 */
  border-radius: 10px 10px 0 0;
  min-height: 36px;
  transition: background 0.2s, border-color 0.2s;
}

.device-id-bar.disconnected {
  background: #ffeaea;
  border-color: #ff4d4f; /* 离线时边界与设备框一致 */
}

.device-id {
  font-size: 0.98rem; /* 字体略小一点 */
  color: #3a4a7c;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.device-id-chip {
  display: inline-block;
  padding: 1px 6px;
  margin: 0 4px 0 2px;
  border-radius: 6px;
  background: #fff7cc; /* 浅黄色底色 */
  color: #7a5c00;
  border: 1px solid #f6e6a0;
  font-weight: 600;
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

.device-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 细调图标按钮与标题栏风格的融合感 */
.device-reset-icon :deep(.el-icon) {
  color: #2f7a12;
  font-size: 18px; /* 稍微放大图标 */
}
.device-reset-icon.is-plain.is-success {
  border-color: #b7eb8f;
}
.device-reset-icon.is-plain.is-success:hover {
  background: #f6ffed;
  border-color: #95de64;
}

.device-block {
  border: 1.5px solid #bfcfff;
  border-radius: 0 0 18px 18px; /* 顶部与标题栏无缝衔接 */
  border-top: 0; /* 移除顶部边框避免双线 */
  padding: 0;
  margin-top: 0;
  padding-top: 0;
  background: #fff;
  width: 320px; /* 初始宽度，实际高度由 aspect-ratio 推导 */
  /* 去掉固定高度，避免破坏纵横比自适应 */
  min-width: 220px;
  /* 不再设置 min/max-height，让纵横比自由计算 */
  max-width: 800px;
  box-shadow: 0 4px 24px rgba(80, 120, 255, 0.1);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.2s;
  overflow: hidden; /* 放大时让内容跟随撑满，而不是出现滚动条导致看起来没变大 */
  resize: horizontal; /* 只允许横向拖拽，纵向由 aspect-ratio 联动，避免失真 */
  position: relative; /* 让内部图片容器绝对定位填满 */
}

.device-block.disconnected {
  border-color: #ff4d4f;
  box-shadow: 0 0 8px #ffb3b3;
}

.device-block > div {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.05rem;
  color: #4b5563;
}

.device-img-wrap {
  /* 使用正常文档流 + 弹性填充，避免绝对定位在部分布局下被覆盖导致看不到 */
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000; /* 黑色背景使画面在不同 aspect 下看起来一致 */
  position: relative;
}

.device-img {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(80, 120, 255, 0.08);
}

.device-error-overlay {
  position: absolute;
  left: 8px;
  bottom: 8px;
  max-width: calc(100% - 16px);
  background: rgba(255, 77, 79, 0.92);
  color: #fff;
  padding: 6px 10px 6px 8px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.3;
  display: flex;
  align-items: flex-start;
  gap: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(2px);
}
.device-error-overlay .err-icon {
  font-size: 14px;
  line-height: 14px;
  flex-shrink: 0;
  margin-top: 2px;
}
.device-error-overlay .err-text {
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  word-break: break-word;
}

.placeholder {
  color: #94a3b8;
  font-size: 0.9rem;
  letter-spacing: 0.5px;
}

.fade-enter-active, .fade-leave-active { transition: opacity .18s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.device-status-error {
  color: #ff4d4f;
  font-weight: bold;
  font-size: 1.1rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
  background: linear-gradient(135deg, #fff5f5 0%, #ffeaea 100%);
  border-radius: 12px;
  margin: 16px;
  border: 1px solid #ffcccc;
  box-shadow: 0 2px 8px rgba(255, 77, 79, 0.1);
}

.disconnect-icon {
  width: 48px;
  height: 48px;
  margin-bottom: 8px;
  display: block;
  filter: drop-shadow(0 1px 3px rgba(255, 77, 79, 0.3));
}

.offline-text {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.offline-title {
  font-size: 1.2rem;
  font-weight: 600;
  color: #ff4d4f;
  margin-bottom: 4px;
}

.offline-desc {
  font-size: 0.9rem;
  color: #666;
  line-height: 1.4;
  max-width: 200px;
  text-align: center;
  margin-bottom: 4px;
}

.offline-status {
  font-size: 0.85rem;
  color: #999;
  padding: 4px 8px;
  background: #f5f5f5;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}
.kv {
  display: flex;
  align-items: center;
  margin: 4px 0;
}
.kv .k {
  width: 86px;
  color: #64748b;
}
.kv .v {
  color: #1f2937;
}
</style>
