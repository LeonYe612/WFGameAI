<template>
  <div v-if="visible" class="ocr-verifyer-container">
    <el-image-viewer
      v-if="results.length > 0"
      :url-list="urlList"
      :initial-index="currentIndex"
      @close="handleClose"
      @switch="handleSwitch"
      hide-on-click-modal
    />

    <!-- 自定义覆盖层 -->
    <Teleport to="body">
      <div class="verify-overlay" v-if="visible && currentResult">
        <!-- 顶部信息栏 -->
        <div class="top-bar">
          <div class="image-info">
            <span>{{ currentResult.image_path }}</span>
          </div>
          <div class="ocr-text-panel">
            <h3>识别文本</h3>
            <div class="text-content">
              {{ getResultText(currentResult) || "（无识别文本）" }}
            </div>
          </div>
        </div>

        <!-- 底部操作栏 -->
        <div class="bottom-bar">
          <div class="progress-bar">
            <el-progress
              :percentage="progressPercentage"
              :format="progressFormat"
              :stroke-width="15"
              text-inside
              striped
              striped-flow
            />
          </div>

          <div class="actions">
            <el-button
              type="success"
              size="large"
              @click="handleVerify(ocrResultTypeEnum.RIGHT.value)"
            >
              正确 (Enter)
            </el-button>
            <el-button
              type="danger"
              size="large"
              @click="handleVerify(ocrResultTypeEnum.WRONG.value)"
            >
              误检
            </el-button>
            <el-button
              type="warning"
              size="large"
              @click="handleVerify(ocrResultTypeEnum.MISSING.value)"
            >
              漏检
            </el-button>
          </div>
        </div>
      </div>

      <div
        v-if="visible && loading && results.length === 0"
        class="loading-mask"
      >
        <el-icon class="is-loading"><Loading /></el-icon> 加载中...
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from "vue";
import { ElImageViewer, ElMessage, ElMessageBox } from "element-plus";
import { Loading } from "@element-plus/icons-vue";
import {
  type OcrResult,
  ocrTaskApi,
  ocrResultApi,
  type TaskGetDetailsParams
} from "@/api/ocr";
import { ocrResultTypeEnum } from "@/utils/enums";
import { mediaUrl } from "@/api/utils";

const props = defineProps<{
  taskId: string;
  visible: boolean;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "refresh"): void;
}>();

const loading = ref(false);
const results = ref<OcrResult[]>([]);
const currentIndex = ref(0);
const pagination = ref({
  currentPage: 1,
  pageSize: 25,
  total: 0
});

const initialTotal = ref(0);
const verifiedCount = ref(0);

// 计算属性
const urlList = computed(() =>
  results.value.map(item => mediaUrl(item.image_path))
);
const currentResult = computed(() => results.value[currentIndex.value]);
const progressPercentage = computed(() => {
  if (initialTotal.value === 0) return 0;
  return Math.min(
    Math.round((verifiedCount.value / initialTotal.value) * 100),
    100
  );
});

const progressFormat = () => {
  return `已校验 ${verifiedCount.value} / 总待校验 ${initialTotal.value}`;
};

// 方法
const getResultText = (result: OcrResult) => {
  if (!result.texts) return "";
  if (Array.isArray(result.texts)) {
    return result.texts.join("");
  }
  return result.texts;
};

const fetchResults = async (append = false) => {
  if (loading.value) return;
  loading.value = true;

  try {
    // 始终请求第一页，因为已审核的会从列表中消失（在后端视角）
    // 但为了避免重复，我们需要在前端去重
    const params: TaskGetDetailsParams = {
      id: props.taskId,
      result_type: ocrResultTypeEnum.UNCHECK.value, // 0
      page: 1,
      page_size: pagination.value.pageSize
    };

    const res = await ocrTaskApi.getDetails(params);
    if (res.code === 0) {
      const { results: newResults, total } = res.data;

      // 如果是第一次加载，设置初始总数
      if (!append && initialTotal.value === 0) {
        initialTotal.value = total;
      }

      if (append) {
        // 去重追加
        const existingIds = new Set(results.value.map(r => r.id));
        const uniqueNewResults = newResults.filter(r => !existingIds.has(r.id));
        if (uniqueNewResults.length > 0) {
          results.value = [...results.value, ...uniqueNewResults];
        } else if (total === 0) {
          ElMessage.success("所有图片已审核完毕！");
          // handleClose(); // 可选：自动关闭
        }
      } else {
        results.value = newResults;
        if (newResults.length === 0 && total === 0) {
          ElMessage.info("当前没有待审核的图片");
          handleClose();
        }
      }

      pagination.value.total = total;
    }
  } catch (error) {
    console.error(error);
    ElMessage.error("获取数据失败");
  } finally {
    loading.value = false;
  }
};

const handleSwitch = (index: number) => {
  currentIndex.value = index;

  // 当题目切换至分页后的倒数第2题的时候，自动追加下一页数据
  if (index >= results.value.length - 2) {
    fetchResults(true);
  }
};

const handleVerify = async (type: number) => {
  if (!currentResult.value) return;

  const result = currentResult.value;
  let correctedTexts: string[] | undefined;

  if (
    type === ocrResultTypeEnum.WRONG.value ||
    type === ocrResultTypeEnum.MISSING.value
  ) {
    try {
      const { value } = await ElMessageBox.prompt(
        "请输入你看到的图片中正确的文本",
        "🧐人工矫正",
        {
          confirmButtonText: "确定",
          cancelButtonText: "取消",
          inputValue: getResultText(result),
          inputType: "textarea",
          inputValidator: val => {
            if (val === getResultText(result)) {
              return "当前输入的文本与识别结果相同";
            }
            if (!val || val.trim() === "") {
              return "内容不能为空";
            }
            return true;
          }
        }
      );
      correctedTexts = [value];
    } catch {
      return; // 取消操作
    }
  }

  // 调用 API
  try {
    const params: any = {
      id: result.id,
      result_type: type
    };
    if (correctedTexts) {
      params.corrected_texts = correctedTexts;
    }

    await ocrResultApi.verify(params);

    verifiedCount.value++;

    // 自动翻页
    if (currentIndex.value < results.value.length - 1) {
      // 模拟键盘右键事件触发 el-image-viewer 切换
      document.dispatchEvent(
        new KeyboardEvent("keydown", { key: "ArrowRight" })
      );
    } else {
      // 尝试加载更多
      await fetchResults(true);
      // 如果加载到了新数据，再次尝试翻页
      if (currentIndex.value < results.value.length - 1) {
        document.dispatchEvent(
          new KeyboardEvent("keydown", { key: "ArrowRight" })
        );
      } else {
        ElMessage.success("本批次审核完成");
      }
    }
  } catch (e) {
    console.error(e);
    ElMessage.error("操作失败");
  }
};

const handleClose = () => {
  emit("update:visible", false);
  emit("refresh");
};

// 监听 visible 变化，初始化数据
watch(
  () => props.visible,
  val => {
    debugger;
    if (val) {
      results.value = [];
      currentIndex.value = 0;
      pagination.value.currentPage = 1;
      initialTotal.value = 0;
      verifiedCount.value = 0;
      fetchResults();

      window.addEventListener("keydown", handleKeydown);
    } else {
      window.removeEventListener("keydown", handleKeydown);
    }
  }
);

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === "Enter") {
    // 避免在输入框中按回车触发
    const target = e.target as HTMLElement;
    if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") return;

    handleVerify(ocrResultTypeEnum.RIGHT.value);
  }
};

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeydown);
});
</script>

<style scoped>
.ocr-verifyer-container {
  /* 这里的样式其实不重要，因为 el-image-viewer 是 teleport 的 */
}

.verify-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 3000; /* 确保在 el-image-viewer 之上 */
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 20px;
  box-sizing: border-box;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  pointer-events: auto;
}

.image-info {
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  padding: 5px 10px;
  border-radius: 4px;
  height: fit-content;
}

.ocr-text-panel {
  background: rgba(255, 255, 255, 0.9);
  padding: 15px;
  border-radius: 8px;
  width: 300px;
  max-height: 400px;
  overflow-y: auto;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.ocr-text-panel h3 {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 16px;
  font-weight: bold;
}

.text-content {
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 14px;
  line-height: 1.5;
}

.bottom-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  pointer-events: auto;
  background: rgba(0, 0, 0, 0.5);
  padding: 20px;
  border-radius: 8px;
  align-self: center;
  width: 600px;
}

.progress-bar {
  width: 100%;
  margin-bottom: 10px;
}

.actions {
  display: flex;
  gap: 20px;
}

.loading-mask {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  z-index: 3001;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #fff;
  font-size: 20px;
}
</style>
