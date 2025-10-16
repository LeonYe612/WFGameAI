<script setup lang="ts">
import { ElForm } from "element-plus";
import { ref } from "vue";
import type { SystemSettings, TimeZoneOption } from "../utils/types";
import { systemSettingsRules } from "../utils/rules";

defineOptions({
  name: "GeneralSettings"
});

const props = defineProps<{
  settings: SystemSettings;
  timeZoneOptions: TimeZoneOption[];
  loading: boolean;
}>();

const emit = defineEmits<{
  save: [];
  reset: [];
  "update:settings": [settings: SystemSettings];
}>();

const formRef = ref<InstanceType<typeof ElForm>>();

// 保存设置
const handleSave = async () => {
  if (!formRef.value) return;

  const valid = await formRef.value.validate().catch(() => false);
  if (valid) {
    emit("save");
  }
};

// 重置设置
const handleReset = () => {
  emit("reset");
};

// 更新设置
const updateSettings = (key: keyof SystemSettings, value: any) => {
  const newSettings = { ...props.settings, [key]: value };
  emit("update:settings", newSettings);
};
</script>

<template>
  <el-card shadow="never" class="h-full">
    <template #header>
      <div class="card-header">
        <el-icon><Setting /></el-icon>
        <span class="header-title">通用设置</span>
      </div>
    </template>

    <div class="settings-content">
      <el-form
        ref="formRef"
        :model="settings"
        :rules="systemSettingsRules"
        label-width="120px"
        label-position="left"
      >
        <el-form-item label="系统名称" prop="systemName">
          <el-input
            :model-value="settings.systemName"
            @update:model-value="updateSettings('systemName', $event)"
            placeholder="请输入系统名称"
          />
        </el-form-item>

        <el-form-item label="管理员邮箱" prop="adminEmail">
          <el-input
            :model-value="settings.adminEmail"
            @update:model-value="updateSettings('adminEmail', $event)"
            placeholder="请输入管理员邮箱"
            type="email"
          />
        </el-form-item>

        <el-form-item label="最大设备数量" prop="maxDevice">
          <el-input-number
            :model-value="settings.maxDevice"
            @update:model-value="updateSettings('maxDevice', $event)"
            :min="1"
            :max="1000"
            placeholder="请输入最大设备数量"
          />
        </el-form-item>

        <el-form-item label="报告保留天数" prop="reportRetentionDays">
          <el-input-number
            :model-value="settings.reportRetentionDays"
            @update:model-value="updateSettings('reportRetentionDays', $event)"
            :min="1"
            :max="365"
            placeholder="请输入报告保留天数"
          />
        </el-form-item>

        <el-form-item label="时区设置" prop="timeZone">
          <el-select
            :model-value="settings.timeZone"
            @update:model-value="updateSettings('timeZone', $event)"
            placeholder="请选择时区"
            style="width: 100%"
          >
            <el-option
              v-for="option in timeZoneOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="邮件通知">
          <el-switch
            :model-value="settings.enableNotifications"
            @update:model-value="updateSettings('enableNotifications', $event)"
            active-text="启用"
            inactive-text="关闭"
          />
        </el-form-item>

        <el-form-item label="自动备份">
          <el-switch
            :model-value="settings.enableAutoBackup"
            @update:model-value="updateSettings('enableAutoBackup', $event)"
            active-text="启用"
            inactive-text="关闭"
          />
        </el-form-item>

        <el-form-item label="调试模式">
          <el-switch
            :model-value="settings.debugMode"
            @update:model-value="updateSettings('debugMode', $event)"
            active-text="开启"
            inactive-text="关闭"
          />
        </el-form-item>

        <el-form-item>
          <div class="form-actions">
            <el-button type="primary" :loading="loading" @click="handleSave">
              保存设置
            </el-button>
            <el-button type="default" @click="handleReset"> 重置 </el-button>
          </div>
        </el-form-item>
      </el-form>
    </div>
  </el-card>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  font-weight: 500;
}

.header-title {
  margin-left: 8px;
}

.settings-content {
  padding: 20px 0;
}

.form-actions {
  display: flex;
  gap: 12px;
}
</style>
