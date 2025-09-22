<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEditMode ? '编辑 OCR 任务' : '创建 OCR 任务'"
    width="720px"
    height="70vh"
    @close="handleClose"
  >
    <el-form
      :model="form"
      :rules="rules"
      ref="formRef"
      label-width="120px"
      class="form-container"
      size="default"
    >
      <el-form-item label="数据源" prop="source_type">
        <el-radio-group v-model="form.source_type" :disabled="isEditMode">
          <el-radio-button
            v-for="item in sortedEnum(ocrSourceTypeEnum)"
            :key="item.value"
            :label="item.value"
          >
            {{ item.label }}
          </el-radio-button>
        </el-radio-group>
      </el-form-item>

      <!-- Git 仓库参数 -->
      <template v-if="form.source_type === ocrSourceTypeEnum.GIT.value">
        <el-form-item label="Git 仓库" prop="repo_id">
          <el-select
            v-model="form.repo_id"
            placeholder="请选择仓库"
            :disabled="isEditMode"
            @change="fetchBranches"
            style="width: 70%"
            filterable
          >
            <el-option
              v-for="r in repositories"
              :key="r.id"
              :label="r.url"
              :value="r.id"
            />
          </el-select>
          <el-button
            :icon="Tools"
            type="warning"
            @click="$emit('manage-repos')"
            plain
            style="margin-left: 10px"
          />
        </el-form-item>
        <el-form-item label="Git 分支" prop="branch">
          <el-select
            v-model="form.branch"
            v-loading="loadingBranches"
            placeholder="请选择分支"
            :disabled="isEditMode"
            style="width: 70%"
            filterable
          >
            <el-option
              v-for="name in branches"
              :key="name"
              :label="name"
              :value="name"
            />
          </el-select>
        </el-form-item>
      </template>

      <!-- 文件上传参数 -->
      <template
        v-if="
          form.source_type === ocrSourceTypeEnum.UPLOAD.value && !isEditMode
        "
      >
        <el-form-item label="上传文件" prop="files">
          <el-upload
            v-model:file-list="form.files"
            action=""
            :auto-upload="false"
            :limit="100"
            multiple
            drag
            :accept="acceptTypes"
            :before-upload="beforeFileUpload"
            :on-change="handleFileChange"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 .zip、.tar.gz 及图片文件，最多上传 100 个。
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </template>
      <el-form-item label="识别语言" prop="languages">
        <div>
          <el-checkbox-group v-model="form.languages">
            <el-checkbox-button
              v-for="lang in sortedEnum(ocrLanguageEnum)"
              :key="lang.value"
              :label="lang.value"
            >
              {{ lang.label }}
            </el-checkbox-button>
          </el-checkbox-group>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="isSubmitting">
          {{ isEditMode ? "保存" : "创建" }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from "vue";
import { UploadFilled } from "@element-plus/icons-vue";
// 支持的文件类型
const acceptTypes = ".zip,.tar.gz,.jpg,.jpeg,.png,.bmp,.gif,.webp";

// 文件类型校验
const beforeFileUpload = (file: File) => {
  const allowedTypes = [
    "application/zip",
    "application/x-zip-compressed",
    "application/gzip",
    "application/x-gzip",
    "image/jpeg",
    "image/png",
    "image/bmp",
    "image/gif",
    "image/webp"
  ];
  const allowedExts = [
    ".zip",
    ".tar.gz",
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".gif",
    ".webp"
  ];
  const fileName = file.name.toLowerCase();
  const isTarGz = fileName.endsWith(".tar.gz");
  const isAllowedType = allowedTypes.includes(file.type) || isTarGz;
  const isAllowedExt = allowedExts.some(ext => fileName.endsWith(ext));
  if (!isAllowedType || !isAllowedExt) {
    message("仅支持 .zip、.tar.gz 及常见图片文件", { type: "warning" });
    return false;
  }
  return true;
};
import type { FormInstance, FormRules } from "element-plus";
import {
  ocrTaskApi,
  ocrRepositoryApi,
  OcrRepository,
  OcrTask
} from "@/api/ocr";
import type { CreateGitTaskParams } from "@/api/ocr";
import { superRequest } from "@/utils/request";
import { ocrLanguageEnum, ocrSourceTypeEnum, sortedEnum } from "@/utils/enums";
import { message } from "@/utils/message";
import { Tools } from "@element-plus/icons-vue";

interface Props {
  modelValue: boolean;
  task: OcrTask | null;
}

interface Emits {
  (e: "update:modelValue", value: boolean): void;
  (e: "success"): void;
  (e: "manage-repos"): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const dialogVisible = computed({
  get: () => props.modelValue,
  set: value => emit("update:modelValue", value)
});

const isEditMode = computed(() => !!props.task);
const formRef = ref<FormInstance>();
const isSubmitting = ref(false);

const initialForm = {
  source_type: ocrSourceTypeEnum.GIT.value,
  repo_id: "",
  branch: "",
  files: [] as File[],
  languages: [] as string[]
};

const form = ref({ ...initialForm });

const rules = ref<FormRules>({
  source_type: [
    { required: true, message: "请选择任务类型", trigger: "change" }
  ],
  repo_id: [
    {
      trigger: "blur",
      validator: (rule, value) => {
        if (form.value.source_type === ocrSourceTypeEnum.GIT.value && !value) {
          return new Error("请选择仓库");
        }
        return true;
      }
    }
  ],
  branch: [
    {
      trigger: "blur",
      validator: (rule, value) => {
        if (form.value.source_type !== ocrSourceTypeEnum.GIT.value) {
          return true;
        }
        if (!value) {
          return new Error("请选择分支");
        }
        if (!branches.value || !branches.value.length) {
          return new Error("请先选择仓库并加载分支");
        }
        if (!branches.value.includes(value)) {
          return new Error("所选分支无效，请重新选择");
        }
        return true;
      }
    }
  ],
  files: [
    {
      trigger: "change",
      validator: (rule, value) => {
        if (form.value.source_type === "upload" && value.length === 0) {
          return new Error("请上传文件");
        }
        return true;
      }
    }
  ],
  languages: [
    {
      required: true,
      message: "请选择识别语言",
      trigger: "blur"
    }
  ]
});

const repositories = ref<OcrRepository[]>([]);
const branches = ref<string[]>([]);
const loadingBranches = ref(false);

const resetForm = () => {
  form.value = { ...initialForm };
  formRef.value?.resetFields();
};

watch(
  () => props.task,
  newTask => {
    if (newTask) {
      form.value = {
        ...initialForm,
        source_type: newTask.source_type,
        repo_id: newTask.git_repository?.toString() || "",
        branch: newTask.git_branch || "master"
      };
    } else {
      resetForm();
    }
  },
  { immediate: true }
);

const fetchRepositories = async () => {
  try {
    const res = await superRequest({
      apiFunc: ocrRepositoryApi.list,
      apiParams: {}
    });
    repositories.value = res?.data || [];
  } catch (error) {
    console.error("获取仓库列表失败:", error);
  }
};

const fetchBranches = async () => {
  if (!form.value.repo_id) {
    branches.value = [];
    return;
  }
  try {
    loadingBranches.value = true;
    const res = await superRequest({
      apiFunc: ocrRepositoryApi.getBranches,
      apiParams: form.value.repo_id
    });
    branches.value = res?.data?.branches || [];
    // 若当前选中分支不在列表中，则置空以触发校验
    if (!branches.value.includes(form.value.branch)) {
      form.value.branch = "";
    }
  } catch (error) {
    console.error("获取分支列表失败:", error);
  } finally {
    loadingBranches.value = false;
  }
};

onMounted(() => {
  fetchRepositories();
});

const handleFileChange = (file: any, fileList: any[]) => {
  form.value.files = fileList.map(f => f.raw);
};

const handleClose = () => {
  dialogVisible.value = false;
  resetForm();
};

const submitForm = async () => {
  if (!formRef.value) return;
  await formRef.value.validate();

  isSubmitting.value = true;
  try {
    // 编辑模式
    if (isEditMode.value && props.task) {
      message("暂未实现编辑功能", { type: "warning" });
      return;
    }
    let apiFunc: any = null;
    let postData: any = null;
    if (form.value.source_type === ocrSourceTypeEnum.GIT.value) {
      const gitData: CreateGitTaskParams = {
        project_id: 1, // 后续通过 team_id 控制，暂时不需要传
        repo_id: Number(form.value.repo_id),
        branch: form.value.branch,
        languages: form.value.languages
      };
      postData = gitData;
      apiFunc = ocrTaskApi.createGitTask;
    } else if (form.value.source_type === ocrSourceTypeEnum.UPLOAD.value) {
      if (form.value.files.length === 0) {
        message("请上传文件", { type: "warning" });
        return;
      }
      const formData = new FormData();
      form.value.files.forEach((file: File) => {
        formData.append("file", file);
      });
      formData.append("project_id", "1");
      formData.append("languages", String(form.value.languages));
      postData = formData;
      apiFunc = ocrTaskApi.createUploadTask;
    }
    if (!apiFunc || !postData) {
      message("未知的任务类型", { type: "error" });
      return;
    }
    const res = await superRequest({
      apiFunc,
      apiParams: postData,
      enableSucceedMsg: true,
      succeedMsgContent: "任务创建成功"
    });
    if (res?.code === 0) {
      emit("success");
      handleClose();
    }
  } catch (error) {
    console.error("提交任务失败:", error);
    // 可以在这里添加更详细的错误提示
  } finally {
    isSubmitting.value = false;
  }
};

onMounted(() => {
  fetchRepositories();
});

defineExpose({
  fetchRepositories
});
</script>

<style scoped>
.form-container {
  padding: 0 20px;
}
.dialog-footer {
  text-align: right;
}
</style>
