<script setup lang="ts">
import { ref } from "vue";
import {
  directive,
  Contextmenu,
  ContextmenuItem,
  ContextmenuDivider,
  ContextmenuSubmenu,
  ContextmenuGroup
} from "v-contextmenu";
import "v-contextmenu/dist/themes/default.css";
import {
  View,
  CirclePlus,
  Remove,
  MagicStick,
  EditPen,
  RefreshLeft,
  Delete,
  Select
} from "@element-plus/icons-vue";
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { useParamTreeHooks } from "./hooks/paramTreeHooks";
import { protoGenreEnum } from "@/utils/enums";
import { menuClickEvent } from "./hooks/types";
// import { message } from "@/utils/message";

defineOptions({
  name: "TreeContextMenu",
  components: {
    [Contextmenu.name]: Contextmenu,
    [ContextmenuItem.name]: ContextmenuItem,
    [ContextmenuDivider.name]: ContextmenuDivider,
    [ContextmenuSubmenu.name]: ContextmenuSubmenu,
    [ContextmenuGroup.name]: ContextmenuGroup
  },
  directives: {
    contextmenu: directive
  }
});

const emit = defineEmits(["menu-click"]);
const testcaseStore = useTestcaseStoreHook();
const contextmenu = ref(null);
let node: any = null;
let nodeData: any = null;
const isBasicType = ref(false);
const { isCustomVar } = useParamTreeHooks();

// ========================= 对外暴露的方法 =========================
/**
 * 显示菜单栏
 * @param  treeNode 当前树节点
 * @param  treeNodeData 当前树节点数据
 */
const show = (event: any, treeNode: any) => {
  // step1. 记录当前节点 & 节点数据
  node = treeNode;
  nodeData = treeNode?.data;
  isBasicType.value = testcaseStore.isProto3BasicType(String(nodeData?.type));

  // step2. 综合判断是否满足条件以显示菜单
  // 菜单高度200,需要判断是否超出屏幕高度调整 top
  let top = event.clientY;
  if (window.innerHeight - event.clientY < 200) {
    top = window.innerHeight - 200;
  }
  contextmenu.value?.show({
    left: event.clientX,
    top: top
  });
  console.log("右键菜单显示", contextmenu.value);
};

//========================== 内部方法 ================================
/**
 * 隐藏右键菜单
 */
const hide = () => {
  node = null;
  nodeData = null;
  contextmenu.value?.hide();
};

/**
 * 阻止透明蒙层右键默认事件
 */
const handleCoverRightClick = (event: any) => {
  event.preventDefault();
  hide();
};

/**
 * 点击菜单时传递事件
 */
const onMenuClick = (label: string) => {
  const event: menuClickEvent = {
    menuLabel: label,
    currNode: node
  };
  emit("menu-click", event);
};

const menuList = ref([
  {
    label: "保存为自定义变量",
    hideOnClick: true,
    icon: CirclePlus,
    visible: () => {
      return (
        testcaseStore.currentProtoType === protoGenreEnum.RECV.value &&
        isBasicType.value &&
        node &&
        node?.isLeaf &&
        !nodeData.deleted &&
        !isCustomVar.value(node) // 不能重复保存自定义变量
      );
    }
  },
  {
    label: "引用自定义变量",
    hideOnClick: true,
    icon: MagicStick,
    visible: () => {
      return (
        isBasicType.value &&
        node &&
        node?.isLeaf &&
        !isCustomVar.value(node) &&
        !nodeData.deleted
      );
    }
  },
  {
    label: "设置高级表达式",
    hideOnClick: true,
    icon: EditPen,
    visible: () => {
      return (
        isBasicType.value &&
        node &&
        node?.isLeaf &&
        !isCustomVar.value(node) &&
        !nodeData.deleted &&
        !nodeData.refer_name
      );
    }
  },
  {
    label: "查看变量引用关系",
    hideOnClick: true,
    icon: View,
    visible: () => {
      return (
        testcaseStore.currentProtoType === protoGenreEnum.RECV.value &&
        isBasicType.value &&
        node &&
        node?.isLeaf &&
        isCustomVar.value(node) // 是自定义变量才能查看引用关系
      );
    }
  },
  {
    label: "删除自定义变量",
    hideOnClick: true,
    icon: Delete,
    visible: () => {
      return (
        testcaseStore.currentProtoType === protoGenreEnum.RECV.value &&
        isBasicType.value &&
        node &&
        node?.isLeaf &&
        isCustomVar.value(node) // 是自定义变量才能删除
      );
    }
  },
  {
    label: "不校验此参数",
    hideOnClick: true,
    icon: Remove,
    visible: () => {
      return (
        testcaseStore.currentProtoType === protoGenreEnum.RECV.value &&
        node &&
        !nodeData.deleted
      );
    }
  },
  {
    label: "校验此参数",
    hideOnClick: true,
    icon: Select,
    visible: () => {
      return (
        testcaseStore.currentProtoType === protoGenreEnum.RECV.value &&
        node &&
        nodeData.deleted
      );
    }
  },
  {
    label: "重置参数校验范围",
    hideOnClick: true,
    icon: RefreshLeft,
    visible: () => {
      return testcaseStore.currentProtoType === protoGenreEnum.RECV.value;
    }
  }
]);

const batchOperations = ref([
  {
    label: "批量保存自定义变量",
    hideOnClick: true,
    icon: CirclePlus,
    visible: () => {
      return true;
    }
  },
  {
    label: "批量设置不校验参数",
    hideOnClick: true,
    icon: Remove,
    visible: () => {
      return true;
    }
  }
]);

defineExpose({ show });
</script>

<template>
  <div>
    <!-- 右键菜单-文档：https://github.com/CyberNika/v-contextmenu/blob/main/docs/usage.md -->
    <v-contextmenu ref="contextmenu" autoAdjustPlacement>
      <div
        class="fixed left-0 top-0 bg-transparent"
        style="width: 100vw; height: 100vh; z-index: -1"
        @click.stop="hide"
        @contextmenu.stop="handleCoverRightClick"
      />
      <v-contextmenu-item
        v-show="item.visible()"
        v-for="(item, index) in menuList"
        :key="index"
        :hideOnClick="item.hideOnClick"
        @click="onMenuClick(item.label)"
      >
        <div class="p-1 items-center flex">
          <el-icon size="14px">
            <component :is="item.icon" />
          </el-icon>
          <span class="ml-1 text-sm">{{ item.label }}</span>
        </div>
      </v-contextmenu-item>
      <!-- 批量操作 -->
      <div v-if="testcaseStore.currentProtoType === protoGenreEnum.RECV.value">
        <v-contextmenu-divider />
        <v-contextmenu-submenu title="批量操作">
          <v-contextmenu-item
            v-for="(operation, idx) in batchOperations"
            v-show="operation.visible()"
            :key="idx"
            :hideOnClick="operation.hideOnClick"
            @click="onMenuClick(operation.label)"
          >
            <div class="p-1 items-center flex">
              <el-icon size="14px">
                <component :is="operation.icon" />
              </el-icon>
              <span class="ml-1 text-sm">{{ operation.label }}</span>
            </div>
          </v-contextmenu-item>
        </v-contextmenu-submenu>
      </div>
    </v-contextmenu>
  </div>
</template>

<style scoped></style>
