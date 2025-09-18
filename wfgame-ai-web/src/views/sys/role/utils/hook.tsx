import { ref, onMounted } from "vue";
import { delRole, listRole } from "@/api/system";
import { superRequest } from "@/utils/request";

export const useSysRoleManagement = (
  editRef: any,
  assignRef: any,
  apiScope = true
) => {
  const dataList = ref([]);
  const loading = ref(true);

  const handleEdit = row => {
    if (row.id) {
      editRef.value.showEdit(row);
    } else {
      editRef.value.showEdit();
    }
  };

  const handleAssign = row => {
    if (row.id) {
      assignRef.value.showAssign(row);
    }
  };

  async function handleDelete(row: any) {
    await superRequest({
      apiFunc: delRole,
      apiParams: { id: row.id, is_global: apiScope },
      enableSucceedMsg: true,
      succeedMsgContent: "删除成功！",
      onSucceed: () => {
        fetchData();
      }
    });
  }

  const fetchData = async () => {
    await superRequest({
      apiFunc: listRole,
      apiParams: { is_global: apiScope },
      onBeforeRequest: () => {
        loading.value = true;
      },
      onSucceed: data => {
        dataList.value = data;
      },
      onCompleted: () => {
        loading.value = false;
      }
    });
  };

  onMounted(() => {
    fetchData();
  });

  return {
    dataList,
    loading,
    handleEdit,
    handleAssign,
    handleDelete,
    fetchData
  };
};
