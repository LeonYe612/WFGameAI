import { listMenu, delMenu } from "@/api/system";
import { ref, onMounted } from "vue";
import { superRequest } from "@/utils/request";

export function useSysMenuManagement(editRef: any, menuTableRef: any) {
  const dataList = ref([]);
  const loading = ref(true);
  const defaultExpandAll = ref(false);

  async function fetchData() {
    await superRequest({
      apiFunc: listMenu,
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
  }

  function handleEdit(row: any) {
    editRef.value.fetchData();
    if (row.id) {
      editRef.value.showEdit(row);
    } else {
      editRef.value.showEdit();
    }
  }

  function handleEditChild(row: any) {
    if (row.id) {
      editRef.value.fetchData();
      editRef.value.showEditWithParent(row.id);
    }
  }

  async function handleDelete(row: any) {
    await superRequest({
      apiFunc: delMenu,
      apiParams: { id: row.id },
      enableSucceedMsg: true,
      succeedMsgContent: "删除成功！",
      onSucceed: () => {
        fetchData();
      }
    });
  }

  function toggleTreeExpansion(rows: any, expand: Boolean) {
    const len = rows?.length || 0;
    for (let i = 0; i < len; i++) {
      menuTableRef.value.toggleRowExpansion(rows[i], expand);
      if (rows[i].children?.length) {
        toggleTreeExpansion(rows[i].children, expand);
      }
    }
  }

  function toggleTableExpansion(expand: Boolean) {
    toggleTreeExpansion(dataList.value, expand);
  }

  onMounted(() => {
    fetchData();
  });

  return {
    dataList,
    loading,
    defaultExpandAll,
    handleEdit,
    handleEditChild,
    handleDelete,
    fetchData,
    toggleTableExpansion
  };
}
