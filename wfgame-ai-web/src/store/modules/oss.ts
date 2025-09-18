import { ElMessageBox } from "element-plus";
import { genFileId } from "element-plus";
import type { UploadInstance, UploadProps, UploadRawFile } from "element-plus";
import { Ref } from "vue";
import { message } from "@/utils/message";

// el-upload组件相关的钩子函数
export function useUpload(upload: Ref<UploadInstance | undefined>) {
  // :before-upload
  const beforeUpload: UploadProps["beforeUpload"] = async (
    rawFile: UploadRawFile
  ) => {
    // console.log("==> beforeUpload");
    const isLt5M = rawFile.size / 1024 / 1024 < 5;
    if (!isLt5M) {
      message("上传文件大小不能超过 5MB!", { type: "error" });
    }
    return isLt5M;
  };
  // :before-remove
  const beforeRemove: UploadProps["beforeRemove"] = uploadFile => {
    // console.log("==> beforeRemove");
    return ElMessageBox.confirm(
      `Cancel the transfer of 【${uploadFile.name} 】?`
    ).then(
      () => true,
      () => false
    );
  };

  // :on-remove
  const handleRemove: UploadProps["onRemove"] = (file, uploadFiles) => {
    // console.log("==> handleRemove");
    const index = uploadFiles.findIndex(f => f.uid === file.uid);
    if (index !== -1) {
      uploadFiles.splice(index, 1);
    }
  };
  // :on-preview
  const handlePreview: UploadProps["onPreview"] = uploadFile => {
    // console.log("==> handlePreview");
  };
  // :on-exceed
  const handleExceed: UploadProps["onExceed"] = (files, uploadFiles) => {
    // console.log("==> handleExceed");
    ElMessageBox.confirm(
      "上传限制为1个文件，继续添加将替换现有文件，是否继续？"
    )
      .then(() => {
        if (upload.value) {
          const newFile = files[0] as UploadRawFile; // 暂存新文件
          newFile.uid = genFileId();
          upload.value.clearFiles(); // 清空当前列表
          upload.value.handleStart(newFile); // 添加新文件并触发上传
          upload.value.submit(); // 提交上传(可加可不加)
        }
      })
      .catch(() => {
        // 用户取消操作
        if (upload.value) {
          upload.value.clearFiles(); // 清空当前列表
        }
      });
  };
  // :on-success
  const handleSuccess: UploadProps["onSuccess"] = (
    response,
    file,
    fileList
  ) => {
    // 清理上传列表
    // 这里可以添加你的代码来处理上传成功的情况
    // console.log("==> handleSuccess");
    if (upload.value) {
      upload.value?.clearFiles();
    }
  };
  // :on-error
  const handleError: UploadProps["onError"] = (err, file, fileList) => {
    // 清理上传列表
    // console.log("==> handleError");
    if (upload.value) {
      upload.value.clearFiles();
    }
    if (fileList.length > 0) {
      fileList.splice(0, fileList.length - 1);
    }
  };

  return {
    beforeUpload,
    beforeRemove,
    handleRemove,
    handlePreview,
    handleExceed,
    handleSuccess,
    handleError
  };
}
