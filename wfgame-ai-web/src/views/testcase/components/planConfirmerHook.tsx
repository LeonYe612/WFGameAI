import { ref, Ref } from "vue";
import { getCollectList, addOrEditCollect, deleteCollect } from "@/api/user";
import { superRequest } from "@/utils/request";
import { collectTypeEnum } from "@/utils/enums";
import { usePlanStoreHook } from "@/store/modules/plan";

interface CollectParams {
  page?: number;
  size?: number;
  id?: number;
  type?: number;
  name?: string;
  json_data?: string;
}

export function usePlanConfirmerHook(props: any) {
  const currentCollectId = ref(-1);
  const collectTableRef = ref(null);
  const planStore = usePlanStoreHook();
  const collectList: Ref<any> = ref([]);
  const collectListTotal = ref(0);

  const collectParams: Ref<CollectParams> = ref(props.query);
  const collectListLoading = ref(false);
  const formLoading = ref(false);
  const editStateRows = ref({});

  const fetchCollectList = async () => {
    await superRequest({
      apiFunc: getCollectList,
      apiParams: collectParams.value,
      onBeforeRequest: () => {
        collectListLoading.value = true;
      },
      onSucceed: data => {
        collectList.value = data.list || [];
        collectListTotal.value = data.total || 0;
      },
      onCompleted: () => {
        collectListLoading.value = false;
      }
    });
  };

  // 双击可进入编辑状态
  const handleCellDblclick = (row, column) => {
    if (column.property !== "name") return;
    row.enableNameEdit = true;
    row.nameCopy = row.name;
    row.name = "";
    editStateRows.value[row.id] = row;
  };

  // 点击dialog的其他区域可以退出编辑模式
  const handleCancelEditState = () => {
    // 其他其他地方的时候，恢复只读模式和值
    Object.keys(editStateRows.value).forEach(key => {
      const item = editStateRows.value[key];
      if (item.enableNameEdit) {
        item.enableNameEdit = false;
        if (item.nameCopy) {
          item.name = item.nameCopy;
        }
      }
      delete editStateRows.value[key];
    });
  };

  // 编辑收藏名称
  const handleNameChanged = row => {
    const prop = "enableNameEdit";
    superRequest({
      apiFunc: addOrEditCollect,
      apiParams: {
        id: row.id,
        name: row.name
      },
      enableSucceedMsg: true,
      succeedMsgContent: "收藏名称修改成功！",
      onSucceed: () => {
        row[prop] = false;
      }
    });
  };

  // 将当前设置保存为收藏
  const handleSaveCurrentSettings = async () => {
    // 1. 获取当前时间戳后8位数字
    const timestamp = Date.now(); // 获取当前时间戳
    const last8Digits = timestamp.toString().slice(-8); // 获取后8位数字
    // 2. 从 planStore 拷贝info副本
    const infoCopy = JSON.parse(JSON.stringify(planStore.info));
    // 指定需要保存到数据库的计划设置字段
    const fields = [
      "env",
      "server_no",
      "plan_type",
      "run_type",
      "run_info",
      "inform",
      "prefix",
      "account_num",
      "account_num_min",
      "account_num_max",
      "nick_prefix",
      "times",
      "interval",
      "case_type",
      "is_reuse",
      "account_len",
      "cycle_type",
      "assign_account",
      "assign_account_type",
      "cycle_text"
    ];
    const settings = {};
    fields.forEach(field => {
      if (infoCopy?.[field] !== null && infoCopy?.[field] !== undefined) {
        settings[field] = infoCopy[field];
      }
    });

    await superRequest({
      apiFunc: addOrEditCollect,
      apiParams: {
        id: 0,
        type: collectTypeEnum.PLAN_RUN_SETTINGS.value,
        name: `我的常用[${last8Digits}]`,
        json_data: JSON.stringify(settings)
      },
      enableSucceedMsg: true,
      succeedMsgContent: "添加常用计划设置成功！"
    });
    await fetchCollectList();
    if (collectList.value?.length) {
      currentCollectId.value = collectList.value[0].id;
    }
  };

  // 删除收藏
  const handleDeleteCollect = async (id: number) => {
    await superRequest({
      apiFunc: deleteCollect,
      apiParams: {
        id
      },
      enableSucceedMsg: false,
      succeedMsgContent: "删除收藏成功！"
    });
    await fetchCollectList();
  };

  // 点击行时，将当前的计划设置同步到 store 中
  const handleCollectRowClick = row => {
    const info = JSON.parse(row.json_data);
    planStore.SET_INFO(info);
    if (info.assign_account !== "") {
      planStore.GENERATE_ACCOUNT_CSV();
    }
    currentCollectId.value = row.id;
  };

  return {
    currentCollectId,
    collectTableRef,
    collectParams,
    collectListLoading,
    collectList,
    collectListTotal,
    editStateRows,
    formLoading,
    fetchCollectList,
    handleCellDblclick,
    handleCancelEditState,
    handleNameChanged,
    handleSaveCurrentSettings,
    handleDeleteCollect,
    handleCollectRowClick
  };
}
