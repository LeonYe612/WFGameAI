<script setup lang="ts">
import { onMounted } from "vue";
import MainContent from "@/layout/components/mainContent/index.vue";
import SettingsMenu from "./components/settingsMenu.vue";
import GeneralSettings from "./components/generalSettings.vue";
import PythonSettings from "./components/pythonSettings.vue";
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
  fetchSystemSettings,
  saveSettings,
  resetSettings,
  fetchPythonEnvironments,
  switchPythonEnv,
  switchMenu
} = useSettingsManagement();

onMounted(() => {
  fetchSystemSettings();
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
  <MainContent title="系统设置">
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

        <!-- 用户管理 -->
        <PlaceholderSettings
          v-else-if="activeMenu === 'user'"
          title="用户管理"
          icon="User"
          description="用户管理功能正在开发中，敬请期待..."
        />

        <!-- AI设置 -->
        <PlaceholderSettings
          v-else-if="activeMenu === 'ai'"
          title="AI设置"
          icon="MagicStick"
          description="AI设置功能正在开发中，敬请期待..."
        />

        <!-- 备份与恢复 -->
        <PlaceholderSettings
          v-else-if="activeMenu === 'backup'"
          title="备份与恢复"
          icon="Download"
          description="备份与恢复功能正在开发中，敬请期待..."
        />

        <!-- 系统日志 -->
        <PlaceholderSettings
          v-else-if="activeMenu === 'log'"
          title="系统日志"
          icon="Document"
          description="系统日志功能正在开发中，敬请期待..."
        />

        <!-- API配置 -->
        <PlaceholderSettings
          v-else-if="activeMenu === 'api'"
          title="API配置"
          icon="Link"
          description="API配置功能正在开发中，敬请期待..."
        />
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
