import { ref } from "vue";
import { superRequest } from "@/utils/request";
import { testTeamConfig } from "@/api/team";
import { configTestTypeEnum } from "@/utils/enums";
import { ElMessageBox } from "element-plus";

export function useConfigTesterHook(props: { env: string }) {
  const testTypeId = ref(null); // 测试类型id

  // ================= 执行测试 ====================
  const loading = ref(false);
  const execute = async (params: object) => {
    dialogVisible.value = true;
    loading.value = true;
    isSuccess.value = null;
    subTitle.value = "";
    content.value = "";
    await superRequest({
      apiFunc: testTeamConfig,
      apiParams: {
        env: parseInt(props.env),
        type_id: testTypeId.value,
        json_str: JSON.stringify(params)
      },
      onSucceed: (res: any) => {
        const { pass, desc, data } = res;
        isSuccess.value = pass;
        subTitle.value = desc;
        if (data) {
          try {
            content.value = JSON.stringify(JSON.parse(data), null, 4);
          } catch (e) {
            content.value = data;
          }
        }
      },
      onCompleted: () => {
        loading.value = false;
      }
    });
  };
  const onVerifyButtonClick = () => {
    /**
     * 配置校验需要特殊处理的：写在前面if判断并天返回
     * 其余全部由 execute({}) 执行
     */
    if (testTypeId.value === configTestTypeEnum.TYPE2.value) {
      // 同步 proto 文件，需要用户填写分支名
      openCommonInputBox({
        title: "请输入Git分支名称",
        prompt: "您可以先运行分支配置测试，以获取可用的分支名",
        validator: (value: string) => {
          if (!value) {
            return "请输入分支名";
          }
          return true;
        },
        onSucceed: (value: string) => {
          execute({ ref: value });
        }
      });
      return;
    }
    execute({});
  };

  const openCommonInputBox = (param: {
    title: string;
    prompt: string;
    validator: (value: string) => boolean | string;
    onSucceed?: (value: string) => void;
    onFailed?: (value: string) => void;
  }) => {
    /**
     * 输入框的校验函数。 应该返回一个 boolean 或者 string,
     * 如果返回的是一个 string 类型，
     * 那么该返回值会被赋值给 inputErrorMessage 用于向用户展示错误消息。
     */
    ElMessageBox.prompt(param.prompt, param.title, {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      inputValidator: param.validator
    })
      .then(({ value }) => {
        param?.onSucceed && param.onSucceed(value);
      })
      .catch(() => {
        param?.onFailed && param?.onFailed("取消输入");
      });
  };
  /**
   * 测试结果展示变量
   */
  const dialogVisible = ref(false);
  const isSuccess = ref(false);
  const subTitle = ref("");
  const content = ref("");
  return {
    // ref data
    testTypeId,
    loading,
    dialogVisible,
    isSuccess,
    subTitle,
    content,
    // methods
    onVerifyButtonClick
  };
}
