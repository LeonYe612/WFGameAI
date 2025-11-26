<template>
  <el-card
    shadow="always"
    class="result-card"
    :style="{ background: getCardColor(result.result_type) }"
  >
    <div class="card-content cursor-pointer">
      <div class="image-container">
        <el-image
          :title="mediaUrl(result.image_path)"
          style="width: 100%; height: 250px"
          :src="mediaUrl(result.image_path)"
          fit="scale-down"
          lazy
          @click="handleImageClick(result)"
        />
      </div>
      <div class="info-container">
        <h3 class="image-name" :title="getImgName(result.image_path)">
          {{ getImgName(result.image_path) }}
        </h3>

        <p class="info-item">
          <span :title="`ID:${result.id}`">识别结果:</span>
          <span
            class="text-primary"
            :title="getResultText(result)"
            @click="handleCopyText(getResultText(result))"
          >
            {{ getResultText(result) || "-" }}
          </span>
        </p>
        <p class="info-item">
          最大置信度:
          <span>
            {{ result.max_confidence || "-" }}
          </span>
        </p>
        <p class="info-item">
          分辨率:
          <span>
            {{ result.pic_resolution || "-" }}
          </span>
        </p>
        <p v-if="false" class="info-item">
          语言:
          <span>
            {{ result.languages || "-" }}
          </span>
        </p>
        <p v-if="false" class="info-item" :title="result.image_path">
          路径:
          <a :href="mediaUrl(result.image_path)" target="_blank">
            {{ result.image_path || "-" }}
          </a>
        </p>
        <p v-if="false" class="info-item" :title="result.image_path">
          哈希值:
          <span
            :title="result.image_hash"
            @click="handleCopyText(result.image_hash)"
          >
            {{ result.image_hash || "-" }}
          </span>
        </p>
        <el-radio-group
          :model-value="props.result.result_type"
          size="small"
          class="result-type-radios"
          @update:model-value="handleResultTypeChange"
        >
          <el-radio-button
            v-for="item in resultTypes"
            :key="item.value"
            :label="item.value"
            :style="{
              '--radio-bg-color': item.color,
              '--radio-text-color': '#303133'
            }"
          >
            {{ item.label }}
          </el-radio-button>
        </el-radio-group>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { type OcrResult, ocrResultApi } from "@/api/ocr";
import { ocrResultTypeEnum } from "@/utils/enums";
import { ref, computed } from "vue";
import { superRequest } from "@/utils/request";
import { mediaUrl } from "@/api/utils";
import { copyText } from "@/utils/utils";
import { ElMessageBox } from "element-plus";

type Emits = {
  (e: "view-image", result: OcrResult): void;
  (e: "update:result_type", value: string): void;
};

const emit = defineEmits<Emits>();

const props = defineProps<{
  result: OcrResult;
}>();

const currentResultType = ref(props.result.result_type);

const resultTypes = computed(() => {
  return Object.values(ocrResultTypeEnum).filter(item => item.value > 0);
});

const getCardColor = (_resultType: string) => {
  // const entry = getEnumEntry(ocrResultTypeEnum, resultType);
  // return entry ? entry.color : "#F2F2F2";
  return "#FFFFFF";
};

const getResultText = (result: OcrResult) => {
  if (!result.texts) return "";
  if (Array.isArray(result.texts)) {
    const texts = result.texts.map(s => s).join("");
    return texts;
  }
  return result.texts;
};

const handleCopyText = (text: string) => {
  if (!text) return;
  copyText(text);
};

const handleImageClick = (result: OcrResult) => {
  emit("view-image", result);
};

const getImgName = (imagePath: string) => {
  if (!imagePath) return "未知图片";
  const parts = imagePath.split("/");
  return parts[parts.length - 1];
};

const handleResultTypeChange = async (newType: string) => {
  const oldType = currentResultType.value;
  if (newType === oldType) return;

  let correctedTexts: string[] | undefined;

  // 当更新为非正确时，必须传递 corrected_texts
  if (
    newType == ocrResultTypeEnum.WRONG.value ||
    newType == ocrResultTypeEnum.MISSING.value
  ) {
    try {
      const { value } = await ElMessageBox.prompt(
        "请输入你看到的图片中正确的文本",
        "🧐人工矫正",
        {
          confirmButtonText: "确定",
          cancelButtonText: "取消",
          inputValue: getResultText(props.result),
          inputType: "textarea",
          inputValidator: val => {
            if (val === getResultText(props.result)) {
              return "当前输入的文本与识别结果相同";
            }
            return true;
          }
        }
      );
      correctedTexts = [value];
    } catch {
      return;
    }
  }

  // 先发送 emit 事件给父组件
  emit("update:result_type", newType);

  const params: any = {
    id: props.result.id,
    result_type: newType
  };

  if (correctedTexts) {
    params.corrected_texts = correctedTexts;
  }

  // 然后调用 API 更新
  superRequest({
    apiFunc: ocrResultApi.verify,
    apiParams: params,
    onSucceed: () => {
      currentResultType.value = newType;
    },
    onFailed: () => {
      // API 调用失败时，发送原来的值给父组件（回滚）
      emit("update:result_type", oldType);
    }
  });
};
</script>

<style lang="scss" scoped>
.result-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: background-color 0.3s;

  :deep(.el-card__body) {
    padding: 0;
    flex: 1;
  }
}

.card-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.image-container {
  flex-shrink: 0;
  padding: 6px;
  border-bottom: 1px solid #e4e7ed;
}

.info-container {
  padding: 14px;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.image-name {
  font-size: 16px;
  font-weight: bold;
  margin: 0 0 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.info-item {
  font-size: 12px;
  margin: 2px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: grey;
}

.result-type-radios {
  margin-top: auto;
  padding-top: 10px;
  margin-left: auto;
  margin-right: auto;
  :deep(.el-radio-button__inner) {
    background-color: #fff;
    color: #303133;
    border-color: #dcdfe6;
    box-shadow: none;
  }

  :deep(.el-radio-button.is-active .el-radio-button__inner) {
    background-color: var(--radio-bg-color, #409eff);
    border-color: var(--radio-bg-color, #409eff);
    color: #fff;
    box-shadow: -1px 0 0 0 var(--radio-bg-color, #409eff);
  }

  :deep(.el-radio-button:first-child .el-radio-button__inner) {
    border-left: 1px solid #dcdfe6;
  }
}
</style>
