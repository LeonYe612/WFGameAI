<template>
  <el-dialog
    v-model="localVisible"
    :title="isEdit ? '编辑任务' : '新建任务'"
    width="600px"
    :close-on-click-modal="false"
    @close="handleCancel"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="taskFormRules"
      label-width="100px"
    >
      <el-form-item label="任务名称" prop="name">
        <el-input
          v-model="formData.name"
          placeholder="请输入任务名称"
          maxlength="50"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="任务类型" prop="type">
        <el-select
          v-model="formData.type"
          placeholder="请选择任务类型"
          style="width: 100%"
        >
          <el-option
            v-for="option in taskTypeOptions.slice(1)"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          >
            <div style="display: flex; align-items: center; gap: 8px">
              <el-icon>
                <component
                  :is="taskTypeConfig[option.value as TaskType]?.icon"
                />
              </el-icon>
              {{ option.label }}
            </div>
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="目标设备" prop="device">
        <el-select
          v-model="formData.device"
          placeholder="请选择目标设备"
          style="width: 100%"
          filterable
        >
          <el-option
            v-for="device in deviceOptions"
            :key="device.value"
            :label="device.label"
            :value="device.value"
          >
            <div style="display: flex; align-items: center; gap: 8px">
              <el-icon>
                <Iphone />
              </el-icon>
              {{ device.label }}
            </div>
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="任务描述">
        <el-input
          v-model="formData.description"
          type="textarea"
          :rows="3"
          placeholder="请输入任务描述（可选）"
          maxlength="200"
          show-word-limit
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleCancel"> 取消 </el-button>
        <el-button type="primary" :loading="loading" @click="handleSubmit">
          {{ isEdit ? "保存" : "创建" }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from "vue";
import { ElMessage, type FormInstance } from "element-plus";
import { Iphone } from "@element-plus/icons-vue";
import { TaskType } from "@/api/tasks";
import { taskFormRules, taskTypeOptions, taskTypeConfig } from "../utils/rules";
import type {
  TaskFormDialogProps,
  TaskFormDialogEmits,
  TaskFormData
} from "../utils/types";

// Props
const props = withDefaults(defineProps<TaskFormDialogProps>(), {
  visible: false,
  task: null,
  loading: false
});

// Emits
const emit = defineEmits<TaskFormDialogEmits>();

// 本地显示状态
const localVisible = computed({
  get: () => props.visible,
  set: value => emit("update:visible", value)
});

// 表单引用
const formRef = ref<FormInstance>();

// 表单数据
const formData = ref<TaskFormData>({
  name: "",
  type: "",
  device: "",
  description: ""
});

// 是否编辑模式
const isEdit = computed(() => !!props.task);

// 设备选项 (模拟数据，实际应该从API获取)
const deviceOptions = ref([
  { label: "OnePlus 9 Pro", value: "oneplus_9_pro" },
  { label: "Samsung Galaxy S21", value: "samsung_s21" },
  { label: "Xiaomi Mi 11", value: "xiaomi_mi11" },
  { label: "多设备", value: "multiple" }
]);

// 重置表单
const resetForm = () => {
  formData.value = {
    name: "",
    type: "",
    device: "",
    description: ""
  };
  nextTick(() => {
    formRef.value?.clearValidate();
  });
};

// 监听任务数据变化
watch(
  () => props.task,
  newTask => {
    if (newTask) {
      formData.value = {
        name: newTask.name,
        type: newTask.type,
        device: newTask.device,
        description: newTask.description || ""
      };
    } else {
      resetForm();
    }
  },
  { immediate: true }
);

// 监听对话框显示状态
watch(
  () => props.visible,
  visible => {
    if (visible && !props.task) {
      resetForm();
    }
  }
);

// 处理提交
const handleSubmit = async () => {
  try {
    await formRef.value?.validate();
    emit("submit", { ...formData.value });
  } catch (error) {
    ElMessage.warning("请完善表单信息");
  }
};

// 处理取消
const handleCancel = () => {
  emit("cancel");
};
</script>

<style scoped>
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
