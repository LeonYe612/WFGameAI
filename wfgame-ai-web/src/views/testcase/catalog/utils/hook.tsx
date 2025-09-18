import { listTeam, delTeam, listMineTeam } from "@/api/team";
import { ref } from "vue";
import { superRequest } from "@/utils/request";

export function useSysTeamManagement(props: any) {
  const editRef = props.editRef;
  const teamTableRef = props.teamTableRef;

  const dataList = ref([]);
  const loading = ref(false);
  const defaultExpandAll = ref(true);

  async function fetchData(scope = "all", afterFetchData?: Function) {
    await superRequest({
      apiFunc: scope === "all" ? listTeam : listMineTeam,
      onBeforeRequest: () => {
        loading.value = true;
      },
      onSucceed: data => {
        dataList.value = data;
      },
      onCompleted: () => {
        loading.value = false;
        typeof afterFetchData === "function" && afterFetchData(dataList.value);
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
      apiFunc: delTeam,
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
      teamTableRef.value.toggleRowExpansion(rows[i], expand);
      if (rows[i].children?.length) {
        toggleTreeExpansion(rows[i].children, expand);
      }
    }
  }

  function toggleTableExpansion(expand: Boolean) {
    toggleTreeExpansion(dataList.value, expand);
  }

  // onMounted(() => {
  //   console.log("onMounted", "********************");
  //   fetchData();
  // });

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
