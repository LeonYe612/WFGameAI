<script setup lang="ts">
import { ref, computed } from "vue";
import { TrendCharts, Histogram } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import type { DataSource, DataAnalysis } from "@/api/data";
import { ANALYSIS_TYPES } from "../utils/types";

defineOptions({
  name: "DataAnalysisPanel"
});

const props = defineProps<{
  dataSources: DataSource[];
  analysisResults: DataAnalysis[];
  loading: boolean;
}>();

const emit = defineEmits(["analyze"]);

const selectedSourceId = ref("");
const selectedAnalysisType = ref("");

// 可用的数据源（只显示已连接的）
const availableDataSources = computed(() => {
  return props.dataSources.filter(source => source.status === "connected");
});

// 执行分析
const handleAnalyze = () => {
  if (!selectedSourceId.value || !selectedAnalysisType.value) {
    ElMessage.warning("请选择数据源和分析类型");
    return;
  }

  emit("analyze", selectedSourceId.value, selectedAnalysisType.value);
};

// 获取分析类型显示名称
const getAnalysisTypeName = (type: string) => {
  const analysis = ANALYSIS_TYPES.find(item => item.value === type);
  return analysis ? analysis.label : type;
};

// 格式化分析结果
const formatAnalysisResult = (result: any) => {
  if (typeof result === "string") {
    return result;
  }

  if (typeof result === "object") {
    return JSON.stringify(result, null, 2);
  }

  return String(result);
};
</script>

<template>
  <div class="space-y-4">
    <!-- 分析配置 -->
    <el-card shadow="never" class="border">
      <template #header>
        <div class="flex items-center">
          <el-icon class="mr-2">
            <TrendCharts />
          </el-icon>
          <span class="font-medium">数据分析</span>
        </div>
      </template>

      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            选择数据源
          </label>
          <el-select
            v-model="selectedSourceId"
            placeholder="请选择要分析的数据源"
            style="width: 100%"
          >
            <el-option
              v-for="source in availableDataSources"
              :key="source.id"
              :label="`${source.name} (${source.recordCount}条)`"
              :value="source.id"
            />
          </el-select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            分析类型
          </label>
          <el-select
            v-model="selectedAnalysisType"
            placeholder="请选择分析类型"
            style="width: 100%"
          >
            <el-option
              v-for="analysis in ANALYSIS_TYPES"
              :key="analysis.value"
              :label="analysis.label"
              :value="analysis.value"
            >
              <div>
                <div>{{ analysis.label }}</div>
                <div class="text-xs text-gray-500">
                  {{ analysis.description }}
                </div>
              </div>
            </el-option>
          </el-select>
        </div>

        <div class="flex justify-end">
          <el-button
            type="primary"
            :icon="Histogram"
            :loading="loading"
            :disabled="!selectedSourceId || !selectedAnalysisType"
            @click="handleAnalyze"
          >
            开始分析
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 分析结果 -->
    <el-card v-if="analysisResults.length > 0" shadow="never" class="border">
      <template #header>
        <span class="font-medium">分析结果</span>
      </template>

      <div class="space-y-4">
        <div
          v-for="result in analysisResults"
          :key="result.id"
          class="p-4 bg-gray-50 rounded-lg"
        >
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center">
              <el-tag type="primary" size="small">
                {{ getAnalysisTypeName(result.analysisType) }}
              </el-tag>
            </div>
            <div class="text-xs text-gray-500">
              {{ result.createdAt }}
            </div>
          </div>

          <div class="text-sm">
            <pre
              class="bg-white p-3 rounded border text-xs overflow-auto max-h-60"
              >{{ formatAnalysisResult(result.result) }}</pre
            >
          </div>
        </div>
      </div>
    </el-card>

    <!-- 空状态 -->
    <el-empty
      v-if="availableDataSources.length === 0"
      description="暂无可用的数据源进行分析，请先创建并连接数据源"
      class="py-12"
    />

    <el-empty
      v-if="availableDataSources.length > 0 && analysisResults.length === 0"
      description="暂无分析结果，请选择数据源和分析类型开始分析"
      class="py-8"
    />
  </div>
</template>
