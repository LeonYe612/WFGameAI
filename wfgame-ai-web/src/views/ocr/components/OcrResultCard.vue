<template>
  <el-card
    shadow="always"
    class="result-card"
    :style="{ background: getCardColor(result.result_type) }"
  >
    <div class="card-content">
      <div class="image-container">
        <el-image
          class="cursor-pointer"
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
        <p class="info-item text-gray">
          分辨率: {{ result.pic_resolution || "-" }}
        </p>
        <p class="info-item text-gray">语言: {{ result.languages || "-" }}</p>
        <p class="info-item text-gray" :title="result.image_path">
          路径: {{ result.image_path || "-" }}
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
  return Object.values(ocrResultTypeEnum).filter(item => item.value !== "");
});

const getCardColor = (_resultType: string) => {
  // const entry = getEnumEntry(ocrResultTypeEnum, resultType);
  // return entry ? entry.color : "#F2F2F2";
  return "#FFFFFF";
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
  try {
    // 先发送 emit 事件给父组件
    emit("update:result_type", newType);

    // 然后调用 API 更新
    await superRequest({
      apiFunc: ocrResultApi.update,
      apiParams: {
        ids: { [props.result.id]: newType }
      },
      onSucceed: () => {
        currentResultType.value = newType;
      }
    });
  } catch (error) {
    // API 调用失败时，发送原来的值给父组件（回滚）
    emit("update:result_type", props.result.result_type);
  }
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
}

.text-gray {
  color: #999;
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
