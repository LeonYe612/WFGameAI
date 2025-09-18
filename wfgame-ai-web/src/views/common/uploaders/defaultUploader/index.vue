<script lang="ts" setup>
import { onMounted, ref } from "vue";
import { UploadFilled } from "@element-plus/icons-vue";
import type {
  UploadInstance,
  UploadRawFile,
  UploadRequestHandler,
  UploadUserFile
} from "element-plus";
import { PropType } from "vue";
import { usePlanStoreHook } from "@/store/modules/plan";
import { Awaitable } from "@vueuse/core";

// 当前组件默认调用上传接口：baseUrlApi("/file/upload")，将文件存储至服务器的相对路径下: /download/用户名/环境/本地存储的文件名(不传默认使用源文件名)
defineOptions({
  name: "DefaultUploader"
});

// 自定义默认变量
const props = defineProps({
  uploadRef: {
    type: Object as PropType<UploadInstance>,
    default: () => ref<UploadInstance>(null)
  },
  limit: {
    type: Number,
    default: 1
  },
  fileList: {
    type: Array as PropType<UploadUserFile[]>,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  httpRequest: {
    type: Function as PropType<UploadRequestHandler>,
    default: usePlanStoreHook().uploadFile
  },
  beforeUpload: {
    type: Function as PropType<
      (
        rawFile: UploadRawFile
      ) => Awaitable<void | undefined | null | boolean | File | Blob>
    >,
    default: () => {}
  },
  onExceed: {
    type: Function as PropType<
      (files: File[], uploadFiles: UploadUserFile[]) => void
    >,
    default: () => {}
  },
  onRemove: {
    type: Function as PropType<
      (file: UploadUserFile, fileList: UploadUserFile[]) => void
    >,
    default: () => {}
  },
  onSuccess: {
    type: Function as PropType<
      (response: any, file: UploadUserFile, fileList: UploadUserFile[]) => void
    >,
    default: () => null
  },
  onError: {
    type: Function as PropType<
      (err: Error, file: UploadUserFile, fileList: UploadUserFile[]) => void
    >,
    default: () => {}
  }
});
// 传递给父组件ref对象，方便其操作
const emit = defineEmits(["update:uploadRef"]);
const internalUploadRef = ref<UploadInstance | null>(null);

onMounted(() => {
  emit("update:uploadRef", internalUploadRef.value);
});
</script>

<template>
  <el-upload
    ref="internalUploadRef"
    :limit="limit"
    :file-list="fileList"
    :http-request="props.httpRequest || usePlanStoreHook().uploadFile"
    :on-exceed="onExceed"
    :before-upload="beforeUpload"
    :on-error="onError"
    :on-remove="onRemove"
    :on-success="onSuccess"
    :show-file-list="true"
    v-loading="loading"
    multiple
  >
    <template #trigger>
      <el-button
        type="success"
        :icon="UploadFilled"
        size="large"
        style="width: 120px; font-size: 16px; margin-left: 5px"
      >
        上传
      </el-button>
    </template>
  </el-upload>
</template>
