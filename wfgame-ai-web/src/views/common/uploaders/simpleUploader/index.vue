<script lang="ts" setup>
import { ref } from "vue";
import { Upload } from "@element-plus/icons-vue";
import { ApiResult, baseUrlApi } from "@/api/utils";
import { message } from "@/utils/message";

defineOptions({
  name: "SimpleUploader"
});

const emit = defineEmits(["uploadSucceed"]);

const uploadRef = ref();
const uploadUrl = baseUrlApi("/upload");
const loading = ref(false);

const handleSuccess = (response: ApiResult) => {
  loading.value = false;
  const { data, code } = response;
  if (code === 0) {
    message("文件上传成功！", { type: "success" });
    emit("uploadSucceed", data);
  }
};

const handleError = (err: Error) => {
  loading.value = false;
  message(`上传文件失败：${err}`, { type: "error" });
};

const handleBeforeUpload = () => {
  loading.value = true;
  return true;
};

const start = () => {
  uploadRef.value.$el.querySelector(".el-upload__input").click();
};

defineExpose({
  start
});
</script>
<template>
  <el-upload
    ref="uploadRef"
    class="p-0 m-0"
    :action="uploadUrl"
    :multiple="false"
    :show-file-list="false"
    :on-success="handleSuccess"
    :on-error="handleError"
    :before-upload="handleBeforeUpload"
  >
    <el-button :icon="Upload" type="primary" :loading="loading" />
  </el-upload>
</template>
