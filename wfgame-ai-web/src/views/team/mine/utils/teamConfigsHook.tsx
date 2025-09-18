import { ref } from "vue";
import { superRequest } from "@/utils/request";
import { getTeamConfig, editTeamConfig } from "@/api/team";
import { ossUpload } from "@/api/oss";
import { envEnum } from "@/utils/enums";

export function useTeamConfigs() {
  const testYaml = ref("");
  const devYaml = ref("");
  const prodYaml = ref("");

  const loading = ref(false);
  const saveLoading = ref(false);
  const testLoadings = ref({});
  const uploadLoadings = ref(false);

  const activeEnv = ref(envEnum.TEST.toString());
  const handleTabChange = (tabVal: string) => {
    activeEnv.value = tabVal;
  };

  async function fetchData() {
    await superRequest({
      apiFunc: getTeamConfig,
      onBeforeRequest: () => {
        loading.value = true;
      },
      onSucceed: data => {
        testYaml.value = data?.test_yaml || "";
        devYaml.value = data?.dev_yaml || "";
        prodYaml.value = data?.prod_yaml || "";
      },
      onCompleted: () => {
        loading.value = false;
      }
    });
  }

  async function handleSaveClick() {
    await superRequest({
      apiFunc: editTeamConfig,
      apiParams: {
        test_yaml: testYaml.value,
        dev_yaml: devYaml.value,
        prod_yaml: prodYaml.value
      },
      enableSucceedMsg: true,
      succeedMsgContent: "环境配置保存成功！",
      onBeforeRequest: () => {
        saveLoading.value = true;
      },
      onCompleted: () => {
        saveLoading.value = false;
      }
    });
  }

  async function uploadOss(uploadFile) {
    const formData = new FormData();
    formData.append("local_file", uploadFile.file);
    formData.append("remote_file", "");
    formData.append("env", activeEnv.value);
    const fileName = uploadFile.file.name;
    await superRequest({
      apiFunc: ossUpload,
      apiParams: formData, // 修改这里
      enableSucceedMsg: true,
      succeedMsgContent: `上传【 ${fileName} 】至oss文件服务器成功 ！`,
      enableFailedMsg: true,
      onBeforeRequest: () => {
        uploadLoadings.value = true;
      },
      onCompleted: () => {
        uploadLoadings.value = false;
      },
      onSucceed: () => {
        uploadLoadings.value = true;
      }
    });
  }

  // async function handleTestClick(testType: string) {
  //   testLoadings.value[testType] = true;
  //   // step1. 测试前先保存
  //   await superRequest({
  //     apiFunc: editTeamConfig,
  //     apiParams: formData.value,
  //     enableSucceedMsg: false
  //   });
  //   // step2. 保存后根据类型去执行不同的测试
  //   setTimeout(() => {
  //     if (
  //       testType === "DevServerOptionsTest" ||
  //       testType === "TestServerOptionsTest"
  //     ) {
  //       testServerOptions(testType);
  //     }
  //   }, 500);
  // }

  // 测试服务器选项查询
  // async function testServerOptions(testType: string) {
  //   const envParam =
  //     testType === "DevServerOptionsTest" ? envEnum.DEV : envEnum.TEST;
  //   // 直接调用查询服务器列表的接口
  //   superRequest({
  //     apiFunc: listServer,
  //     apiParams: { env: envParam },
  //     enableSucceedMsg: false,
  //     onSucceed: data => {
  //       message(
  //         `服务器选项查询配置测试通过，共查询到 ${
  //           data?.length || 0
  //         } 条服务器选项！`,
  //         { type: "success" }
  //       );
  //     },
  //     onCompleted: () => {
  //       delete testLoadings.value[testType];
  //     }
  //   });
  // }

  return {
    testYaml,
    devYaml,
    prodYaml,
    loading,
    testLoadings,
    saveLoading,
    uploadLoadings,
    activeEnv,
    uploadOss,
    fetchData,
    handleSaveClick,
    handleTabChange
  };
}
