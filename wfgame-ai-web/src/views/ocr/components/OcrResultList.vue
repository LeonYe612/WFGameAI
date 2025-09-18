<template>
  <div class="flex-full flex-col">
    <!-- 筛选器 -->
    <el-card class="filter-card">
      <el-form :model="filterData" inline>
        <el-form-item label="">
          <el-input
            v-model="filterData.keyword"
            placeholder="输入关键字查找"
            :prefix-icon="Search"
            clearable
            style="width: 300px"
            @change="handleSearch"
          />
        </el-form-item>
        <el-form-item label="结果类型">
          <el-radio-group
            v-model="filterData.result_type"
            @change="fetchResults"
          >
            <el-radio-button
              v-for="item in sortedEnum(ocrResultTypeEnum)"
              :key="item.value"
              :label="item.value"
            >
              <span>{{ item.label }}</span>
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="匹配状态">
          <el-radio-group v-model="filterData.has_match" @change="fetchResults">
            <el-radio-button
              v-for="item in sortedEnum(ocrIsMatchEnum)"
              :key="item.value"
              :label="item.value"
            >
              <span>{{ item.label }}</span>
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button :icon="Search" type="primary" @click="handleSearch" plain>
            搜索
          </el-button>
          <el-button :icon="RefreshLeft" @click="handleReset"> 重置 </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据卡片 -->
    <el-card
      class="table-card"
      body-style="display: flex; flex-direction: column; flex: 1; overflow: hidden;"
    >
      <div
        class="card-list-container"
        v-loading="loading"
        element-loading-text="正在加载..."
      >
        <el-scrollbar>
          <!-- 图片预览 -->
          <el-image-viewer
            ref="imageViewer"
            v-if="showPreview"
            :url-list="viewerSrcList"
            show-progress
            hide-on-click-modal
            :initial-index="viewerIndex"
            @close="showPreview = false"
          />
          <div v-if="results.length > 0" class="card-grid">
            <el-row :gutter="16">
              <el-col
                class="mb-4"
                v-for="item in results"
                :key="item.id"
                :xs="24"
                :sm="12"
                :md="8"
                :lg="6"
                :xl="4"
              >
                <OcrResultCard :result="item" @view-image="handleViewImage" />
              </el-col>
            </el-row>
          </div>
          <el-empty v-else description="暂无数据" />
        </el-scrollbar>
      </div>

      <!-- 分页栏 -->
      <div class="pagination-wrapper">
        <el-pagination
          :current-page="pagination.currentPage"
          :page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[24, 36, 48, 60]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
          background
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from "vue";
import {
  type OcrResult,
  ocrTaskApi,
  type TaskGetDetailsParams
} from "@/api/ocr";
import { Search, RefreshLeft } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { superRequest } from "@/utils/request";
import OcrResultCard from "./OcrResultCard.vue";
import { ocrResultTypeEnum, ocrIsMatchEnum, sortedEnum } from "@/utils/enums";

const props = defineProps<{
  taskId: string;
}>();

const loading = ref(false);
const results = ref<OcrResult[]>([]);
const filterData = reactive<Partial<TaskGetDetailsParams>>({
  has_match: null,
  result_type: "",
  keyword: ""
});
const pagination = reactive({
  currentPage: 1,
  pageSize: 24,
  total: 0
});

const getImageUrl = (imagePath: string) => {
  return `http://172.20.19.90:8000/media/${imagePath}`;
};

const showPreview = ref(false);
const imageViewer = ref(null);
const viewerIndex = ref(0);
const viewerSrcList = computed(() =>
  results.value.map(item => getImageUrl(item.image_path))
);

const handleViewImage = (result: OcrResult) => {
  const index = results.value.findIndex(item => item.id === result.id);
  if (index !== -1) {
    viewerIndex.value = index;
    showPreview.value = true;
  }
};

const fetchResults = async () => {
  if (!props.taskId) return;
  loading.value = true;
  try {
    const params: TaskGetDetailsParams = {
      id: props.taskId,
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      ...filterData
    };
    const res = await superRequest({
      apiFunc: ocrTaskApi.getDetails,
      apiParams: params
    });
    results.value = res?.data?.results || [];
    pagination.total = res?.data?.total || 0;
  } catch (error) {
    ElMessage.error("获取结果列表失败");
    console.error(error);
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  pagination.currentPage = 1;
  fetchResults();
};

const handleReset = () => {
  filterData.has_match = null;
  filterData.result_type = "";
  filterData.keyword = "";
  handleSearch();
};

const handleSizeChange = (size: number) => {
  pagination.pageSize = size;
  pagination.currentPage = 1; // 回到第一页
  fetchResults();
};

const handlePageChange = (page: number) => {
  pagination.currentPage = page;
  fetchResults();
};

watch(() => props.taskId, fetchResults, { immediate: true });
</script>

<style lang="scss" scoped>
.filter-card {
  margin-bottom: 16px;
  flex-shrink: 0;
}

.table-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.card-list-container {
  flex: 1;
  overflow: hidden;
}

.card-grid {
  padding: 8px;
}

.pagination-wrapper {
  padding-top: 16px;
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
}
</style>
