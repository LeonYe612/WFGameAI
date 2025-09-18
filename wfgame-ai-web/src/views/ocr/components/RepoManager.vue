<template>
  <el-dialog
    v-model="dialogVisible"
    title="OCR 仓库管理"
    width="60%"
    @close="handleClose"
  >
    <div class="repo-manager-container">
      <!-- 工具栏 -->
      <div class="toolbar">
        <el-button type="primary" @click="handleOpenAddDialog">
          <el-icon><Plus /></el-icon>
          添加仓库
        </el-button>
        <el-button @click="loadData" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>

      <!-- 表格 -->
      <el-table
        :data="tableData"
        v-loading="loading"
        stripe
        style="width: 100%"
        height="400px"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column
          prop="url"
          label="仓库地址"
          min-width="250"
          show-overflow-tooltip
        />
        <el-table-column prop="branch" label="默认分支" width="150" />
        <el-table-column prop="created_at" label="添加时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_by" label="添加者" width="120">
          <template #default="{ row }">
            {{ row.created_by?.username || "-" }}
          </template>
        </el-table-column>

        <!-- 操作列 -->
        <el-table-column label="操作" fixed="right" width="150">
          <template #default="{ row }">
            <el-button
              v-if="false"
              type="primary"
              size="small"
              text
              @click="handleSelectRepo(row)"
            >
              选择
            </el-button>
            <el-button
              type="danger"
              size="small"
              text
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          :current-page="pagination.currentPage"
          :page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">关闭</el-button>
      </span>
    </template>

    <!-- 添加仓库对话框 -->
    <el-dialog
      v-model="addDialogVisible"
      title="添加新仓库"
      width="40%"
      append-to-body
    >
      <el-form
        :model="newRepoForm"
        :rules="repoFormRules"
        ref="newRepoFormRef"
        label-width="100px"
      >
        <el-form-item label="仓库地址" prop="url">
          <el-input
            v-model="newRepoForm.url"
            placeholder="例如：https://github.com/user/repo.git"
          />
        </el-form-item>

        <el-form-item label="访问令牌" prop="token">
          <el-input
            v-model="newRepoForm.token"
            placeholder="仓库的访问令牌"
            type="password"
          />
        </el-form-item>

        <el-form-item label="默认分支" prop="branch">
          <el-input v-model="newRepoForm.branch" placeholder="例如：main" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button
          :loading="addConfirmLoading"
          type="primary"
          @click="handleAddNewRepo"
        >
          确定
        </el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from "vue";
import { ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { Plus, Refresh } from "@element-plus/icons-vue";
import { ocrRepositoryApi } from "@/api/ocr";
import type { OcrRepository } from "@/api/ocr";
import { superRequest } from "@/utils/request";
import { message } from "@/utils/message";

interface Props {
  modelValue: boolean;
}

interface Emits {
  (e: "update:modelValue", value: boolean): void;
  (e: "select-repo", repo: OcrRepository): void;
  (e: "close"): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const dialogVisible = ref(props.modelValue);
const loading = ref(false);
const tableData = ref<OcrRepository[]>([]);

const pagination = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0
});

// --- 添加仓库 ---
const addDialogVisible = ref(false);
const newRepoFormRef = ref<FormInstance>();
const newRepoForm = reactive({
  url: "",
  branch: "main",
  token: ""
});
const repoFormRules = reactive<FormRules>({
  url: [{ required: true, message: "请输入仓库地址", trigger: "blur" }],
  branch: [{ required: true, message: "请输入默认分支", trigger: "blur" }],
  token: [{ required: true, message: "请输入访问令牌", trigger: "blur" }]
});
const addConfirmLoading = ref(false);

const handleOpenAddDialog = () => {
  addDialogVisible.value = true;
  newRepoFormRef.value?.resetFields();
};

const handleAddNewRepo = async () => {
  if (!newRepoFormRef.value) return;
  addConfirmLoading.value = true;
  await newRepoFormRef.value.validate(async valid => {
    if (valid) {
      try {
        const res = await superRequest({
          apiFunc: ocrRepositoryApi.create,
          apiParams: {
            url: newRepoForm.url.trim(),
            branch: newRepoForm.branch.trim(),
            token: newRepoForm.token.trim()
          },
          enableSucceedMsg: true,
          succeedMsgContent: "仓库添加成功",
          enableFailedMsg: false
        });
        if (res?.code === 0) {
          addDialogVisible.value = false;
          loadData(); // 刷新列表
        } else {
          message("添加失败：请查看控制台输出的错误信息", {
            type: "error"
          });
          console.error("Failed to add repository:", res);
        }
      } catch (error) {
        console.error("Failed to add repository:", error);
        message("添加失败，请检查仓库地址或联系管理员", { type: "error" });
      } finally {
        addConfirmLoading.value = false;
      }
    }
  });
};

// --- 数据加载与处理 ---
const loadData = async () => {
  loading.value = true;
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.pageSize
    };
    const res = await superRequest({
      apiFunc: ocrRepositoryApi.list,
      apiParams: params
    });
    tableData.value = res.data || [];
    pagination.total = tableData.value.length;
  } catch (error) {
    console.error("Failed to fetch repositories:", error);
    message("获取仓库列表失败", { type: "error" });
    tableData.value = [];
    pagination.total = 0;
  } finally {
    loading.value = false;
  }
};

const handlePageChange = (page: number) => {
  pagination.currentPage = page;
  loadData();
};

const handleSizeChange = (size: number) => {
  pagination.pageSize = size;
  pagination.currentPage = 1;
  loadData();
};

const formatDate = (dateString: string) => {
  if (!dateString) return "-";
  const date = new Date(dateString);
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
};

// --- 操作 ---
const handleSelectRepo = (repo: OcrRepository) => {
  emit("select-repo", repo);
  handleClose();
};

const handleDelete = (repo: OcrRepository) => {
  ElMessageBox.confirm(
    `确定要删除仓库 "${repo.url}" 吗？此操作不可恢复。`,
    "警告",
    {
      confirmButtonText: "确定删除",
      cancelButtonText: "取消",
      type: "warning"
    }
  )
    .then(async () => {
      try {
        await superRequest({
          apiFunc: ocrRepositoryApi.delete,
          apiParams: repo.id,
          enableSucceedMsg: true,
          succeedMsgContent: "仓库删除成功"
        });
        loadData(); // 重新加载数据
      } catch (error) {
        console.error("Failed to delete repository:", error);
        message("删除失败，请稍后重试", { type: "error" });
      }
    })
    .catch(() => {
      // 用户取消
    });
};

const handleClose = () => {
  emit("update:modelValue", false);
  emit("close");
};

watch(
  () => props.modelValue,
  newValue => {
    dialogVisible.value = newValue;
    if (newValue) {
      loadData();
    }
  }
);
</script>

<style scoped>
.repo-manager-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.toolbar {
  display: flex;
  justify-content: flex-start;
}
.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
