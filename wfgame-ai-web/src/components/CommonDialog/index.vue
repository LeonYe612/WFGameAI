<script setup lang="ts">
import { ElDialog, ElButton } from "element-plus";
import { ref } from "vue";

// 定义组件名称
defineOptions({
  name: "CustomDialog",
  inheritAttrs: true
});

// 定义 props
defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: "提示"
  }
});

// 定义 emits
const emit = defineEmits(["update:modelValue", "confirm", "cancel"]);

// 处理对话框显示/隐藏状态更新
const handleUpdate = value => {
  emit("update:modelValue", value);
};

const loadingRef = ref(false);

// 控制对话框显示隐藏函数
const show = (state: boolean) => {
  emit("update:modelValue", state);
};

const loading = (state: boolean) => {
  loadingRef.value = state;
};

// 防抖处理，避免多次触发
let confirmLock = false;
const handleConfirm = async () => {
  if (confirmLock) return;
  confirmLock = true;
  // emit("update:modelValue", false);
  emit("confirm", {
    show: show,
    loading: loading
  });
  // 300ms后允许再次点击
  setTimeout(() => {
    confirmLock = false;
  }, 300);
};

// 处理取消按钮点击
const handleCancel = () => {
  emit("cancel");
  show(false);
};
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="handleUpdate"
    v-bind="$attrs"
    :title="title"
  >
    <slot name="body" />
    <template #footer>
      <slot name="footer">
        <div class="dialog-footer">
          <el-button size="large" @click="handleCancel">取消</el-button>
          <el-button
            :loading="loadingRef"
            size="large"
            type="primary"
            @click="handleConfirm"
          >
            确定
          </el-button>
        </div>
      </slot>
    </template>
  </el-dialog>
</template>

<style scoped>
.dialog-footer {
  text-align: right;
}
</style>
