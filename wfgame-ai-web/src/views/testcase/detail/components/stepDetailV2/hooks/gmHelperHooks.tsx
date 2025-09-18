import { computed, ref } from "vue";
import { protoGenreEnum } from "@/utils/enums";
import { useTestcaseStoreHook } from "@/store/modules/testcase";

export function useGmHelperHooks() {
  let currItemPointer: any;
  const store = useTestcaseStoreHook();
  const gmHelperRef = ref<any>(null);

  const gmButtonVisible = computed(() => {
    return (row: any): boolean => {
      return (
        // 卡牌
        (store.currentStep?.[protoGenreEnum.SEND.value]?.[0]?.proto_message ===
          "GMReq" &&
          store.currentStep?.[protoGenreEnum.SEND.value]?.[0]?.proto_data?.[0]
            ?.value == 4 &&
          row.field == "param") ||
        // 纸老虎
        (store.currentStep?.[protoGenreEnum.SEND.value]?.[0]?.proto_message ===
          "GmCmdReq" &&
          store.currentStep?.[protoGenreEnum.SEND.value]?.[0]?.proto_data?.[0]
            ?.value == 3 && // 这里先只开放 tp=3：添加道具
          row.field == "content")
      );
    };
  });

  const handleShowGmHelperDialog = (currParam: any) => {
    if (currParam) {
      currItemPointer = currParam;
      gmHelperRef.value?.show();
    }
  };

  const handleGmHelperCompleted = (value: string) => {
    currItemPointer.value = value;
  };

  return {
    gmHelperRef,
    gmButtonVisible,
    handleShowGmHelperDialog,
    handleGmHelperCompleted
  };
}
