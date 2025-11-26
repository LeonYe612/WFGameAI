<script setup lang="ts">
import { ref, onMounted, reactive } from "vue";
import {
  getAIModels,
  createAIModel,
  updateAIModel,
  deleteAIModel,
  getAIModelFiles,
  type AIModel,
  type FileNode
} from "@/api/settings";
import { ElMessage, ElMessageBox } from "element-plus";
import { superRequest } from "@/utils/request";
import {
  Plus,
  Edit,
  Delete,
  Refresh,
  Cpu,
  InfoFilled
} from "@element-plus/icons-vue";

defineOptions({
  name: "AIModelSettings"
});

const loading = ref(false);
const treeLoading = ref(false);
const models = ref<AIModel[]>([]);
const dialogVisible = ref(false);
const dialogType = ref<"create" | "edit">("create");
const formRef = ref();
const fileTree = ref<FileNode[]>([]);

const formData = reactive<AIModel>({
  name: "",
  type: "ocr",
  version: "",
  path: "",
  description: "",
  enable: true
});

const rules = {
  name: [{ required: true, message: "请输入模型名称", trigger: "blur" }],
  type: [{ required: true, message: "请选择模型类型", trigger: "change" }],
  version: [{ required: false, message: "请输入版本号", trigger: "blur" }],
  path: [{ required: true, message: "请输入模型路径", trigger: "blur" }]
};

const fetchFileTree = async () => {
  treeLoading.value = true;
  try {
    await superRequest({
      apiFunc: getAIModelFiles,
      onSucceed: data => {
        fileTree.value = data;
      },
      onFailed: () => {
        fileTree.value = [];
      }
    });
  } catch (error) {
    console.error("获取文件列表失败", error);
    ElMessage.error("获取文件列表失败");
  } finally {
    treeLoading.value = false;
  }
};

const handleTreeVisibleChange = (visible: boolean) => {
  if (visible) {
    fetchFileTree();
  }
};

const fetchModels = async () => {
  loading.value = true;
  superRequest({
    apiFunc: getAIModels,
    onSucceed: data => {
      models.value = data;
    },
    onFailed: () => {
      models.value = [];
    },
    onCompleted: () => {
      loading.value = false;
    }
  });
};

const handleAdd = () => {
  dialogType.value = "create";
  Object.assign(formData, {
    id: undefined,
    name: "",
    type: "ocr",
    version: "",
    path: "",
    description: "",
    enable: true
  });
  dialogVisible.value = true;
  // fetchFileTree(); // Removed: Load on open
};

const handleEdit = (row: AIModel) => {
  dialogType.value = "edit";
  Object.assign(formData, row);
  dialogVisible.value = true;
  // fetchFileTree(); // Removed: Load on open
};

const handleDelete = (row: AIModel) => {
  ElMessageBox.confirm(`确定要删除模型 "${row.name}" 吗？`, "警告", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning"
  }).then(async () => {
    try {
      if (row.id) {
        await deleteAIModel(row.id);
        ElMessage.success("删除成功");
        fetchModels();
      }
    } catch (error) {
      ElMessage.error("删除失败");
    }
  });
};

const handleSubmit = async () => {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid: boolean) => {
    if (valid) {
      if (dialogType.value === "create") {
        await superRequest({
          apiFunc: createAIModel,
          apiParams: formData,
          enableSucceedMsg: true,
          succeedMsgContent: "创建模型成功",
          onSucceed: () => {
            dialogVisible.value = false;
            fetchModels();
          }
        });
      } else {
        if (!formData.id) return;
        await superRequest({
          apiFunc: updateAIModel,
          apiParams: [formData.id, formData],
          enableSucceedMsg: true,
          succeedMsgContent: "更新模型成功",
          onSucceed: () => {
            dialogVisible.value = false;
            fetchModels();
          }
        });
      }
    }
  });
};

const handleStatusChange = async (row: AIModel) => {
  try {
    if (row.id) {
      await updateAIModel(row.id, { enable: row.enable });
      ElMessage.success("状态更新成功");
    }
  } catch (error) {
    row.enable = !row.enable; // 恢复状态
    ElMessage.error("状态更新失败");
  }
};

onMounted(() => {
  fetchModels();
});
</script>

<template>
  <el-card class="ai-model-settings h-full" shadow="never">
    <template #header>
      <div class="flex items-center">
        <el-icon><Cpu /></el-icon>
        <span class="ml-2">AI模型管理 (共 {{ models.length }} 个)</span>
        <div class="ml-auto flex gap-2">
          <el-button :icon="Refresh" circle @click="fetchModels" />
          <el-button type="success" :icon="Plus" @click="handleAdd" plain>
            添加模型
          </el-button>
        </div>
      </div>
    </template>

    <el-table
      v-loading="loading"
      :data="models"
      style="width: 100%"
      height="100%"
    >
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.type === 'ocr' ? 'success' : 'warning'">
            {{ row.type.toUpperCase() }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" min-width="150">
        <template #default="{ row }">
          <div class="flex items-center">
            <span>{{ row.name }}</span>
            <el-tooltip
              effect="dark"
              :content="row.description || '暂无描述'"
              placement="right-start"
            >
              <el-icon class="ml-1 cursor-pointer text-gray-400">
                <InfoFilled />
              </el-icon>
            </el-tooltip>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="version" label="版本" width="120" />
      <el-table-column
        prop="path"
        label="路径"
        min-width="200"
        show-overflow-tooltip
      />
      <el-table-column prop="enable" label="状态" width="100">
        <template #default="{ row }">
          <el-switch v-model="row.enable" @change="handleStatusChange(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link :icon="Edit" @click="handleEdit(row)">
            编辑
          </el-button>
          <el-button
            type="danger"
            link
            :icon="Delete"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'create' ? '添加模型' : '编辑模型'"
      width="500px"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-width="80px"
      >
        <el-form-item label="名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入模型名称" />
        </el-form-item>
        <el-form-item label="类型" prop="type">
          <el-select v-model="formData.type" placeholder="请选择类型">
            <el-option label="OCR" value="ocr" />
            <el-option label="YOLO" value="yolo" />
          </el-select>
        </el-form-item>
        <el-form-item label="路径" prop="path">
          <el-tree-select
            v-model="formData.path"
            :data="fileTree"
            :loading="treeLoading"
            @visible-change="handleTreeVisibleChange"
            placeholder="请选择模型文件"
            :check-strictly="false"
            :render-after-expand="false"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="版本" prop="version">
          <el-input v-model="formData.version" placeholder="例如: v1.0.0" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            placeholder="可选描述"
          />
        </el-form-item>
        <el-form-item label="启用" prop="enable">
          <el-switch v-model="formData.enable" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </el-card>
</template>

<style scoped lang="scss">
.ai-model-settings {
  display: flex;
  flex-direction: column;
  :deep(.el-card__body) {
    flex: 1;
    min-height: 0;
    padding: 0; // 表格通常不需要内边距，或者根据需要调整
  }
}
</style>
