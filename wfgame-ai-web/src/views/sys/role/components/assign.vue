<script lang="ts" setup>
import { permissionRole, listMenu, assignRole } from "@/api/system";
import { superRequest } from "@/utils/request";
import { nextTick, onActivated, ref } from "vue";

defineOptions({
  name: "SysRoleManagementAssign"
});

const props = defineProps({
  // 标识相关接口是否作用在【全局域】内
  // 如果组件设置此值为 true，则会在所有接口中传递 is_global: true
  isGlobal: {
    type: Boolean,
    default: true
  }
});

const formVisible = ref(false);
const title = ref("");
const treeRef = ref();
const role = ref();
const permission = ref();
const loading = ref(false);

const fetchMenu = async () => {
  await superRequest({
    apiFunc: listMenu,
    onSucceed: data => {
      // 如果isGlobal === false, 即非超级管理员权限查看权限列表
      // 需要过滤掉 data 数据中的{name: "SystemSetting"} 的子元素
      // 防止用户在【我的团队】列表中操作[系统管理]相关权限控制
      // "API"
      const needHiddens = ["SystemSetting", "API"];
      if (!props.isGlobal) {
        data = data.filter(item => !needHiddens.includes(item?.name));
      }
      permission.value = data;
    }
  });
};

const showAssign = row => {
  role.value = row;
  title.value = `[${row.name}] - 权限指派`;
  initCheckoutTree();
  formVisible.value = true;
};

const closeDialog = () => {
  role.value = {};
  formVisible.value = false;
};

// 对半选和全选的进行反选
const initCheckoutTree = async () => {
  // 初始化需要等dom元素加载完毕以后在进行获取ref
  nextTick(async () => {
    // defaultCheckedKeys:后端返回的选中id [1,3,4,56,7,8,9,223]
    await treeRef.value.setCheckedKeys([]);
    await superRequest({
      apiFunc: permissionRole,
      apiParams: { id: role.value.id, is_global: props.isGlobal },
      onSucceed: data => {
        for (const key of data) {
          // getNode（获取tree中对应的节点）
          const node = treeRef.value.getNode(key);
          treeRef.value.setChecked(node, true);
          // isLeaf（判断节点是否为叶子节点）
          // 如果存在isLeaf 代表是叶子节点为最后一级那么就选中即可 不是则不选择
          if (node?.isLeaf) {
            // setChecked （设置tree中对应的节点为选中状态）
            treeRef.value.setChecked(node, true);
          }
        }
      }
    });
  });
};

const customNodeClass = () => {
  return "text-large bg-text-blue-400";
};

onActivated(() => {
  fetchMenu();
});

const showLable = (data: any) => {
  return data.meta?.title;
};

const save = async () => {
  const data = {
    menu_ids: [
      ...treeRef.value.getCheckedKeys(),
      ...treeRef.value.getHalfCheckedKeys()
    ],
    id: role.value.id,
    is_global: props.isGlobal
  };
  if (data.menu_ids.length >= 0) {
    await superRequest({
      apiFunc: assignRole,
      apiParams: data,
      enableSucceedMsg: true,
      onBeforeRequest: () => {
        loading.value = true;
      },
      onSucceed: () => {
        closeDialog();
      },
      onCompleted: () => {
        loading.value = false;
      }
    });
  }
};

defineExpose({ showAssign });
</script>

<template>
  <el-dialog
    v-model="formVisible"
    :title="title"
    width="500px"
    :before-close="closeDialog"
    :draggable="true"
  >
    <el-scrollbar style="height: 62vh">
      <el-tree
        ref="treeRef"
        :data="permission"
        default-expand-all
        :height="200"
        node-key="id"
        :props="{
          children: 'children',
          label: showLable,
          class: customNodeClass
        }"
        show-checkbox
      >
        <template #default="{ node }">
          <span class="custom-tree-node">
            <!-- <span v-if="data.genre == 1">📚</span>
          <span v-if="data.genre == 2">🕹</span>
          <span v-if="data.genre == 3">🔗</span>
          <span v-if="data.genre == 4">🅰</span> -->
            <span class="ml-2">{{ node.label }}</span>
          </span>
        </template>
      </el-tree>
    </el-scrollbar>

    <template #footer>
      <el-button @click="closeDialog" size="large">取 消</el-button>
      <el-button type="primary" @click="save" size="large" :loading="loading"
        >确 定</el-button
      >
    </template>
  </el-dialog>
</template>
