<script setup lang="ts">
import type { SettingsMenuItem } from "../utils/types";

defineOptions({
  name: "SettingsMenu"
});

defineProps<{
  menuItems: SettingsMenuItem[];
  activeMenu: string;
}>();

const emit = defineEmits<{
  "menu-click": [menuId: string];
}>();

const handleMenuClick = (menuId: string) => {
  emit("menu-click", menuId);
};
</script>

<template>
  <el-card shadow="never" class="menu-card">
    <div class="menu-list">
      <div
        v-for="item in menuItems"
        :key="item.id"
        class="menu-item"
        :class="{ 'menu-item--active': activeMenu === item.id }"
        @click="handleMenuClick(item.id)"
      >
        <el-icon class="menu-icon">
          <component :is="item.icon" />
        </el-icon>
        <span class="menu-label">{{ item.label }}</span>
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.menu-card {
  height: fit-content;
  position: sticky;
  top: 20px;
}

.menu-list {
  padding: 8px 0;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  border-radius: 6px;
  margin-bottom: 4px;
  transition: all 0.2s ease;
  color: var(--el-text-color-primary);
}

.menu-item:hover {
  background-color: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.menu-item--active {
  background-color: var(--el-color-primary);
  color: white;
}

.menu-item--active:hover {
  background-color: var(--el-color-primary);
  color: white;
}

.menu-icon {
  font-size: 16px;
  margin-right: 12px;
}

.menu-label {
  font-size: 14px;
  font-weight: 500;
}
</style>
