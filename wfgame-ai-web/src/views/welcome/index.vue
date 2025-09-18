<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { ElCard, ElRow, ElCol, ElButton } from "element-plus";
import defaultRoutes from "@/router/defaultRoutes";
import extraIcon from "@/layout/components/sidebar/extraIcon.vue";

defineOptions({
  name: "Overview"
});

const router = useRouter();

// 描述信息映射
const descriptionMapping = {
  控制台: "平台运行状态和数据统计",
  设备管理: "管理测试设备状态和连接",
  脚本管理: "测试脚本录制与管理",
  任务管理: "测试任务创建与执行",
  测试报告: "查看测试执行结果和分析",
  数据管理: "测试数据分析与导出",
  OCR识别: "图片文字识别与管理",
  系统设置: "配置系统参数和用户管理"
};

// 颜色配置
const colorMapping = {
  控制台: "#0d6efd",
  设备管理: "#198754",
  脚本管理: "#fd7e14",
  任务管理: "#6f42c1",
  测试报告: "#dc3545",
  数据管理: "#20c997",
  OCR识别: "#ffc107",
  系统设置: "#6c757d"
};

// 从 defaultRoutes 提取并组织模块数据
const moduleData = computed(() => {
  return defaultRoutes
    .filter(route => route.meta?.showLink && route.meta?.showParent)
    .map(route => ({
      id: route.id,
      path: route.path,
      name: route.name,
      title: route.meta.title,
      icon: route.meta.icon,
      description: descriptionMapping[route.meta.title] || "功能模块",
      color: colorMapping[route.meta.title] || "#6c757d",
      queue: route.queue
    }))
    .sort((a, b) => a.queue - b.queue); // 按 queue 排序
});

// 开发者资源链接
const developerResources = ref([
  { name: "Swagger API文档", url: "/swagger/", icon: "fas fa-book" },
  { name: "ReDoc API文档", url: "/redoc/", icon: "fas fa-file-code" },
  { name: "设备API", url: "/api/devices/", icon: "fas fa-mobile-alt" },
  { name: "OCR API", url: "/api/ocr/", icon: "fas fa-camera" },
  { name: "管理后台", url: "/admin/", icon: "fas fa-tools" }
]);

// 平台特性
const platformFeatures = ref([
  "基于AI的UI元素识别和交互",
  "多设备并行测试",
  "测试脚本录制与回放",
  "测试报告生成与分析",
  "设备管理与监控",
  "OCR图片文字识别"
]);

// 导航到指定路由
const navigateTo = (path: string) => {
  router.push(path);
};

// 打开外部链接
const openExternalLink = (url: string) => {
  window.open(url, "_blank");
};
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-6">
    <!-- 页面头部 -->
    <div class="max-w-7xl mx-auto">
      <div class="bg-white rounded-lg shadow-sm p-8 mb-8 text-center">
        <h1 class="text-4xl font-bold text-gray-800 mb-4">
          WFGame AI自动化测试平台
        </h1>
        <p class="text-lg text-gray-600 leading-relaxed">
          集成AI视觉识别、多设备管理和自动化测试的一体化解决方案
        </p>
      </div>

      <!-- 功能模块卡片 -->
      <div class="mb-8">
        <h2 class="text-2xl font-semibold text-gray-800 mb-6">平台功能</h2>
        <el-row :gutter="24" class="mb-6">
          <el-col
            v-for="module in moduleData"
            :key="module.id"
            :xs="24"
            :sm="12"
            :md="8"
            :lg="6"
            class="mb-6"
          >
            <el-card
              class="h-full cursor-pointer transition-all duration-300 hover:shadow-lg hover:-translate-y-1"
              @click="navigateTo(module.path)"
            >
              <div class="text-center p-4">
                <div class="mb-4">
                  <extraIcon :extraIcon="module.icon" />
                </div>
                <h3 class="text-xl font-semibold text-gray-800 mb-3">
                  {{ module.title }}
                </h3>
                <p class="text-gray-600 text-sm mb-4 leading-relaxed">
                  {{ module.description }}
                </p>
                <el-button type="primary" plain>
                  进入{{ module.title }}
                </el-button>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <!-- 内容区域 -->
      <el-row :gutter="24">
        <!-- 平台概述 -->
        <el-col :xs="24" :md="12" class="mb-6">
          <el-card class="h-full">
            <template #header>
              <h3 class="text-xl font-semibold text-gray-800 flex items-center">
                <extraIcon
                  class="mr-2"
                  extraIcon="ant-design:exclamation-circle-twotone"
                />
                平台概述
              </h3>
            </template>

            <div class="space-y-4">
              <p class="text-gray-600 leading-relaxed">
                WFGame
                AI自动化测试平台是一个集成了AI视觉识别、多设备管理和自动化测试的一体化解决方案。
                该平台使用YOLO11m自定义模型进行UI元素识别，支持多设备并行测试，提供Web界面进行测试管理和结果分析。
              </p>

              <div>
                <h4 class="font-semibold text-gray-800 mb-3">主要功能包括：</h4>
                <ul class="space-y-2">
                  <li
                    v-for="feature in platformFeatures"
                    :key="feature"
                    class="flex items-center text-gray-600"
                  >
                    <i class="text-green-500 mr-2 text-sm">✅</i>
                    <span class="text-sm">{{ feature }}</span>
                  </li>
                </ul>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 开发者资源 -->
        <el-col :xs="24" :md="12" class="mb-6">
          <el-card class="h-full">
            <template #header>
              <h3 class="text-xl font-semibold text-gray-800 flex items-center">
                <extraIcon class="mr-2" extraIcon="ant-design:code-outlined" />
                开发者资源
              </h3>
            </template>

            <div class="space-y-3">
              <div
                v-for="resource in developerResources"
                :key="resource.name"
                class="flex items-center justify-between p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors"
                @click="openExternalLink(resource.url)"
              >
                <div class="flex items-center">
                  <i class="text-gray-500 mr-3">◾</i>
                  <span class="text-gray-700 font-medium">{{
                    resource.name
                  }}</span>
                </div>
                <i class="text-gray-400 text-sm">→</i>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 页脚 -->
      <div class="text-center mt-8 py-6 border-t border-gray-200">
        <p class="text-gray-500">
          WFGame AI自动化测试平台 &copy; 2025 WFGame AI团队
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 自定义样式 */
.el-card {
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.el-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

/* FontAwesome 图标样式 */
.fas {
  font-family: "Font Awesome 5 Free";
  font-weight: 900;
}
</style>
