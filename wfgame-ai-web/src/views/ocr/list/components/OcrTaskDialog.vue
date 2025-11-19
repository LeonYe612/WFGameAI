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
            ref="uploadRef"
            action=""
            :auto-upload="false"
            :limit="100"
            multiple
            drag
            :accept="acceptTypes"
            :before-upload="beforeFileUpload"
            :on-change="handleFileChange"
            :file-list="form.files"
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
      <el-form-item label="识别语言" prop="language">
        <div>
          <el-radio-group v-model="form.language">
            <el-radio-button
              v-for="lang in sortedEnum(ocrLanguageEnum)"
              :key="lang.value"
              :label="lang.value"
            >
              {{ lang.label }}
            </el-radio-button>
          </el-radio-group>
        </div>
      </el-form-item>
      
      <!-- 关键字过滤 -->
      <el-form-item label="关键字过滤">
        <div class="w-full space-y-3">
          <div class="flex items-center gap-2">
            <el-switch
              v-model="form.keyword_filter.enabled"
              active-text="启用"
              inactive-text="禁用"
              inline-prompt
              class="scale-[1.2]"
            />
            <span class="text-sm text-gray-500">仅保留包含指定关键字的图片</span>
          </div>
          
          <template v-if="form.keyword_filter.enabled">
            <el-input
              v-model="form.keyword_filter.keywords"
              type="textarea"
              :rows="2"
              placeholder="输入关键字，多个用逗号分隔，例如：kess game, game center"
              clearable
            />
            
            <div class="flex items-center gap-4 text-sm">
              <el-checkbox v-model="form.keyword_filter.fuzzy_match" label="模糊匹配" />
              <el-checkbox v-model="form.keyword_filter.ignore_case" label="忽略大小写" />
              <el-checkbox v-model="form.keyword_filter.ignore_spaces" label="忽略空格" />
              <el-checkbox v-model="form.keyword_filter.ignore_digits" label="忽略数字" />
            </div>
            
            <div v-if="form.keyword_filter.fuzzy_match" class="flex items-center gap-3">
              <span class="text-sm text-gray-600 whitespace-nowrap">相似度:</span>
              <el-slider
                v-model="form.keyword_filter.fuzzy_similarity"
                :min="0.5"
                :max="1.0"
                :step="0.05"
                :format-tooltip="(val) => `${(val * 100).toFixed(0)}%`"
                class="flex-1"
              />
              <span class="text-sm text-gray-600 w-12">{{ (form.keyword_filter.fuzzy_similarity * 100).toFixed(0) }}%</span>
            </div>
            
            <div class="flex items-center gap-3">
              <span class="text-sm text-gray-600 whitespace-nowrap">置信度:</span>
              <el-slider
                v-model="form.keyword_filter.min_confidence"
                :min="0.5"
                :max="1.0"
                :step="0.05"
                :format-tooltip="(val) => `${(val * 100).toFixed(0)}%`"
                class="flex-1"
              />
              <span class="text-sm text-gray-600 w-12">{{ (form.keyword_filter.min_confidence * 100).toFixed(0) }}%</span>
            </div>
          </template>
        </div>
      </el-form-item>
      
      <el-form-item label="启用缓存" prop="disable_cache">
        <el-switch
          title="启用后，系统会查询缓存跳过有历史识别记录的图片，加快处理速度"
          v-model="form.disable_cache"
          active-text="启用"
          inactive-text="禁用"
          inline-prompt
          class="scale-[1.2] ml-1"
        />
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
import { ref, watch, computed } from "vue";
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
// import { useTeamGlobalState } from "@/views/team/hooks/teamStoreStateHook";

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
const uploadRef = ref();
const isSubmitting = ref(false);

const initialForm = {
  source_type: ocrSourceTypeEnum.GIT.value,
  repo_id: "",
  branch: "",
  files: [] as File[],
  language: "ch",  // 默认中文，单选
  enable_cache: true,
  // 关键字过滤配置
  keyword_filter: {
    enabled: false,  // 是否启用关键字过滤
    keywords: "",  // 关键字列表（逗号分隔）
    fuzzy_match: true,  // 是否启用模糊匹配
    fuzzy_similarity: 0.80,  // 模糊匹配相似度阈值
    ignore_case: true,  // 忽略大小写
    ignore_spaces: true,  // 忽略空格
    ignore_digits: true,  // 忽略数字和符号
    min_confidence: 0.80  // OCR置信度阈值
  }
};

// 使用深拷贝初始化表单，避免嵌套对象引用问题
const form = ref(JSON.parse(JSON.stringify(initialForm)));

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
  language: [
    {
      required: true,
      message: "请选择识别语言",
      trigger: "change"
    }
  ]
});

const repositories = ref<OcrRepository[]>([]);
const branches = ref<string[]>([]);
const loadingBranches = ref(false);

const resetForm = () => {
  // 使用深拷贝避免嵌套对象引用问题
  form.value = JSON.parse(JSON.stringify(initialForm));
  formRef.value?.resetFields();
};

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

const setFormDefaults = async () => {
  await fetchRepositories();
  if (repositories.value.length > 0 && !isEditMode.value) {
    form.value.repo_id = repositories.value[1].id;
    fetchBranches();
  }
  // 默认选择第一个分支,测试使用，后续需要删除
  form.value.languages = [ocrLanguageEnum.CH.value];
};

const handleFileChange = (file: any, fileList: any[]) => {
  // 保存原始的文件列表，包含raw属性
  form.value.files = fileList;
  console.log("文件列表更新:", fileList);
};

const handleClose = () => {
  dialogVisible.value = false;
  resetForm();
};

watch(
  () => props.modelValue,
  val => {
    if (val) {
      setFormDefaults();
    }
  }
);

const submitForm = async () => {
  if (!formRef.value) return;
  await formRef.value.validate();

  // 🔍 调试：检查表单数据
  console.log("=== 提交表单 ===");
  console.log("完整表单数据:", JSON.stringify(form.value, null, 2));
  console.log("关键字过滤enabled:", form.value.keyword_filter?.enabled);
  console.log("关键字:", form.value.keyword_filter?.keywords);

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
        languages: [form.value.language],  // 将单选值转为数组
        enable_cache: form.value.enable_cache,
        keyword_filter: form.value.keyword_filter
      };
      postData = gitData;
      apiFunc = ocrTaskApi.createGitTask;
    } else if (form.value.source_type === ocrSourceTypeEnum.UPLOAD.value) {
      if (form.value.files.length === 0) {
        message("请上传文件", { type: "warning" });
        return;
      }
      const formData = new FormData();
      
      // 从upload组件获取文件列表
      const uploadComponent = uploadRef.value;
      const uploadFiles = uploadComponent?.uploadFiles || form.value.files;
      
      if (!uploadFiles || uploadFiles.length === 0) {
        message("请选择有效的文件", { type: "error" });
        return;
      }
      
      // 后端只支持单文件上传，取第一个文件
      const fileItem = uploadFiles[0];
      const file = fileItem.raw || fileItem;
      
      if (!file || !file.name) {
        message("无法获取文件对象", { type: "error" });
        return;
      }
      
      formData.append("file", file);
      formData.append("project_id", "1");
      // languages作为JSON字符串发送，后端需要解析（将单选值转为数组）
      formData.append("languages", JSON.stringify([form.value.language]));
      // 关键字过滤配置作为JSON字符串发送
      formData.append("keyword_filter", JSON.stringify(form.value.keyword_filter));
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

// 监听团队切换
// const { initWatchTeamId } = useTeamGlobalState();
// initWatchTeamId(fetchRepositories, true);

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
