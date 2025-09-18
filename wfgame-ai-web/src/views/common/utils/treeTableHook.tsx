import { ref, nextTick, Ref } from "vue";
import { superRequest } from "@/utils/request";

export function useTreeTable(props: any) {
  // 通过props需要传递的参数如下：
  const listApi = props.listApi;
  const delApi = props.delApi;
  const expandAll = props.expandAll || true;
  const editRef = props.editRef;
  const treeTableRef = props.treeTableRef;

  // 状态
  const dataList = ref([]);
  const loading = ref(false);
  const defaultExpandAll = ref(expandAll);
  const currentRow = ref(null);

  // 刷新数据
  async function fetchData(afterFetchData?: Function) {
    await superRequest({
      apiFunc: listApi,
      onBeforeRequest: () => {
        loading.value = false;
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

  async function fetchDataWithMemoryCurrent(afterFetchData?: Function) {
    const currentId = currentRow.value?.id;
    await fetchData(afterFetchData);
    autoSetCurrent(currentId);
  }

  // 编辑
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
      apiFunc: delApi,
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
      treeTableRef.value.toggleRowExpansion(rows[i], expand);
      if (rows[i].children?.length) {
        toggleTreeExpansion(rows[i].children, expand);
      }
    }
  }

  function toggleTableExpansion(expand: Boolean) {
    toggleTreeExpansion(dataList.value, expand);
  }

  // 设置当前选中行
  function setCurrent(row?: any) {
    treeTableRef.value?.setCurrentRow(row);
  }

  // 中间函数，用于递归查找目标节点
  function findTarget(list: any[], targetId: number) {
    for (let i = 0; i < list.length; i++) {
      const item = list[i];
      if (item.id == targetId) {
        return item;
      }
      if (item.children && item.children.length > 0) {
        const t = findTarget(item.children, targetId);
        if (t) {
          return t;
        }
      }
    }
    return null;
  }

  function autoSetCurrent(targetId?: number | null) {
    // a. 如果待查找目标ID为空，则清空当前选中项
    if (!targetId) {
      setCurrent();
      return;
    }
    // b. 如果当前表格选中项 id 与 全局状态 teamId 相同, 则不需要再次设置
    // 注意：这里还是需要设置下，因为重新加载数据后，当前选中项会被置空
    // if (currentRow.value?.id == targetId) {
    //   return;
    // }
    // c. 如果当前表格选中项 id 与 全局状态 targetId 不同, 则需要设置
    const target = findTarget(dataList.value, targetId);
    if (target) {
      nextTick(() => {
        setCurrent(target);
      });
    }
  }

  /**
   * 根据ID查找节点路径
   * @param dataListRef
   * @param targetId
   * @returns
   */
  const getItemPathById = (dataListRef: Ref, targetId: number) => {
    const path = [];
    const findItem = (list: any[], id: number) => {
      const len = list.length;
      for (let i = 0; i < len; i++) {
        const item = list[i];
        path.push(item);
        if (item.id === id) {
          return;
        }
        if (item.children && item.children.length > 0) {
          findItem(item.children, id);
        }
        if (path[path.length - 1].id !== id) {
          path.pop();
        }
      }
    };
    findItem(dataListRef.value, targetId);
    return path;
  };

  const recordCurrentChange = (row: any) => {
    currentRow.value = row;
  };

  return {
    dataList, // 属性表格数据
    loading, // 表格数据加载状态
    defaultExpandAll, // 是否默认展开所有行
    currentRow, // 当前选中行
    recordCurrentChange,
    handleEdit,
    handleEditChild,
    handleDelete,
    fetchData,
    fetchDataWithMemoryCurrent,
    toggleTableExpansion,
    setCurrent,
    autoSetCurrent,
    getItemPathById
  };
}
