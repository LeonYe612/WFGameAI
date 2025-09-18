import { delUser, listUser } from "@/api/system";
import { superRequest } from "@/utils/request";
import { ref } from "vue";

export const useSysUserManagement = (props: any) => {
  const dataList = ref([]);
  const dataTotal = ref(0);
  const loading = ref(true);

  const handleEdit = row => {
    if (row.id) {
      props.editRef.value.showEdit(row);
    } else {
      props.editRef.value.showEdit();
    }
  };

  async function handleDelete(row: any) {
    await superRequest({
      apiFunc: delUser,
      apiParams: { id: row.id },
      enableSucceedMsg: true,
      succeedMsgContent: "删除成功！",
      onSucceed: () => {
        fetchData();
      }
    });
  }

  const fetchData = async () => {
    await superRequest({
      apiFunc: listUser,
      apiParams: {
        ...props.queryForm
      },
      onBeforeRequest: () => {
        loading.value = true;
      },
      onSucceed: data => {
        dataList.value = data?.list;
        dataTotal.value = data?.total;
      },
      onCompleted: () => {
        loading.value = false;
      }
    });
  };

  return {
    dataList,
    dataTotal,
    loading,
    handleEdit,
    handleDelete,
    fetchData
  };
};
