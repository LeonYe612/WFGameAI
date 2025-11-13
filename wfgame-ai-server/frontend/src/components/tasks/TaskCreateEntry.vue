<template>
  <div class="task-create-entry">
    <el-button
      class="ml-auto"
      type="primary"
      :loading="buttonLoading"
      @click="openDialog"
    >
      <el-icon><Plus /></el-icon>
      {{ buttonText }}
    </el-button>

    <TaskFormDialog
      v-model:visible="dialogVisible"
      :task="null"
      :loading="formLoading"
      @submit="onSubmitInternal"
      @cancel="closeDialog"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Plus } from '@element-plus/icons-vue'
// 说明：此处假设任务表单组件位置为如下路径，如与你项目不一致请调整为实际路径
import TaskFormDialog from '@/pages/tasks/components/taskFormDialog.vue'

interface Props {
  loading?: boolean
  buttonText?: string
  // 外部提交处理函数，返回 Promise；resolve 表示成功创建，reject 表示失败
  onSubmit: (formData: Record<string, any>) => Promise<any>
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  buttonText: '新建任务'
})

const emit = defineEmits<{
  (e: 'created', payload: any): void
  (e: 'cancel'): void
}>()

const dialogVisible = ref(false)
const formLoading = ref(false)
const buttonLoading = computed(() => props.loading || formLoading.value)

function openDialog() {
  dialogVisible.value = true
}

function closeDialog() {
  dialogVisible.value = false
  emit('cancel')
}

async function onSubmitInternal(formData: Record<string, any>) {
  try {
    formLoading.value = true
    const result = await props.onSubmit(formData)
    emit('created', result)
    dialogVisible.value = false
  } catch (err) {
    // 留给上层处理错误提示
  } finally {
    formLoading.value = false
  }
}
</script>

<style scoped>
.task-create-entry {
  display: inline-flex;
  align-items: center;
}
</style>
