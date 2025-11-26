<script setup lang="ts">
import { onMounted } from "vue";
import MainContent from "@/layout/components/mainContent/index.vue";
import SettingsMenu from "./components/settingsMenu.vue";
import GeneralSettings from "./components/generalSettings.vue";
import PythonSettings from "./components/pythonSettings.vue";
import ActionSettings from "./components/actionSettings.vue";
import AIModelSettings from "./components/aiModelSettings.vue";
import PlaceholderSettings from "./components/placeholderSettings.vue";
import { useSettingsManagement } from "./utils/hook";

defineOptions({
  name: "SystemSettings"
});

const {
  loading,
  activeMenu,
  systemSettings,
  pythonEnvs,
  pythonEnvLoading,
  pythonEnvError,
  menuItems,
  timeZoneOptions,
  // fetchSystemSettings,
  saveSettings,
  resetSettings,
  fetchPythonEnvironments,
  switchPythonEnv,
  switchMenu
} = useSettingsManagement();

onMounted(() => {
  // fetchSystemSettings();
});

// 处理菜单切换
const handleMenuClick = (menuId: string) => {
  switchMenu(menuId);

  // 如果切换到Python环境页面，自动加载环境数据
  if (menuId === "python" && pythonEnvs.value.length === 0) {
    fetchPythonEnvironments();
  }
};

// 处理Python环境刷新
const handlePythonEnvRefresh = () => {
  fetchPythonEnvironments();
};

// 处理Python环境切换
const handlePythonEnvSwitch = (envPath: string) => {
  switchPythonEnv(envPath);
};

// 处理设置更新
const updateSystemSettings = (newSettings: any) => {
  Object.assign(systemSettings, newSettings);
};
</script>

<template>
  <MainContent :show-team-info="false">
    <template #custom-header>
      <div class="flex items-center mr-2">
        <h2 class="mr-2" style="letter-spacing: 1px">系统设置</h2>
        <el-divider direction="vertical" />
        <span class="text-gray-400">
          配置平台的各项全局参数，在所有团队中生效，请谨慎修改
        </span>
      </div>
    </template>
    <div class="settings-layout">
      <!-- 左侧菜单 -->
      <div class="settings-sidebar">
        <SettingsMenu
          :menu-items="menuItems"
          :active-menu="activeMenu"
          @menu-click="handleMenuClick"
        />
      </div>

      <!-- 右侧内容区域 -->
      <div class="settings-content">
        <!-- 通用设置 -->
        <GeneralSettings
          v-if="activeMenu === 'general'"
          :settings="systemSettings"
          :time-zone-options="timeZoneOptions"
          :loading="loading"
          @save="saveSettings"
          @reset="resetSettings"
          @update:settings="updateSystemSettings"
        />

        <!-- Python环境设置 -->
        <PythonSettings
          v-else-if="activeMenu === 'python'"
          :environments="pythonEnvs"
          :loading="pythonEnvLoading"
          :error="pythonEnvError"
          @refresh="handlePythonEnvRefresh"
          @switch="handlePythonEnvSwitch"
        />

        <!-- 动作库管理 -->
        <ActionSettings v-else-if="activeMenu === 'action-library'" />

        <!-- AI模型管理 -->
        <AIModelSettings v-else-if="activeMenu === 'ai-models'" />

        <!-- 占位符 -->
        <PlaceholderSettings title="" icon="" v-else />
      </div>
    </div>
  </MainContent>
</template>

<style scoped>
.settings-header-extra {
  display: flex;
  align-items: center;
}

.settings-layout {
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: 24px;
  height: 100%;
}

.settings-sidebar {
  height: fit-content;
}

.settings-content {
  min-height: 600px;
}

@media (max-width: 768px) {
  .settings-layout {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .settings-sidebar {
    order: 2;
  }

  .settings-content {
    order: 1;
  }
}
</style>
