<script setup lang="ts">
import { computed, ref } from "vue";
import {
  directive,
  Contextmenu,
  ContextmenuItem,
  ContextmenuDivider,
  ContextmenuSubmenu,
  ContextmenuGroup
} from "v-contextmenu";
import "v-contextmenu/dist/themes/default.css";
import { CirclePlus, Remove, UserFilled } from "@element-plus/icons-vue";
import { MenuClickEvent } from "@/store/types";
// import { message } from "@/utils/message";

const props = defineProps({
  accountMin: {
    type: Number,
    default: 1
  },
  accountMax: {
    type: Number,
    default: 100
  }
});

const accountList = computed(() => {
  const list = [];
  for (let i = props.accountMin; i <= props.accountMax; i++) {
    list.push({
      value: i,
      label: `Client ${i}`
    });
  }
  return list;
});

defineOptions({
  name: "ArrangerContextMenu",
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

const emit = defineEmits(["menu-click", "hide"]);
const contextmenu = ref(null);

// ========================= 对外暴露的方法 =========================
/**
 * 显示菜单栏
 * @param  treeNode 当前树节点
 * @param  treeNodeData 当前树节点数据
 */
const show = (event: any) => {
  // 综合判断是否满足条件以显示菜单
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
  contextmenu.value?.hide();
  emit("hide");
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
  const event: MenuClickEvent = {
    label: label
  };
  emit("menu-click", event);
};

const menuList = ref([
  {
    label: "复制用例",
    hideOnClick: true,
    icon: CirclePlus,
    visible: () => {
      return true;
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
      <!-- 设置账号 -->
      <div v-if="false">
        <v-contextmenu-item :hideOnClick="true" @click="onMenuClick('abc')">
          <div class="p-1 items-center flex">
            <el-select
              placeholder="请选择账号"
              style="width: 120px; z-index: 99999"
            >
              <el-option
                v-for="item in accountList"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </div>
        </v-contextmenu-item>
      </div>
      <div>
        <v-contextmenu-divider />
        <v-contextmenu-submenu title="设置账号">
          <v-contextmenu-item style="padding: 0">
            <div
              class="bg-white w-[120px] h-[160px] rounded-sm overflow-y-auto overflow-x-hidden"
            >
              <el-scrollbar class="w-full h-full">
                <div
                  class="h-[24px] my-1 hover:bg-[#46a0fc] hover:text-white text-gray-900 flex items-center"
                  v-for="item in accountList"
                  :key="item.value"
                >
                  <el-icon class="ml-[10px]" size="14px">
                    <component :is="UserFilled" />
                  </el-icon>
                  <span class="ml-1 text-sm">{{ item.label }}</span>
                </div>
              </el-scrollbar>
            </div>
          </v-contextmenu-item>
        </v-contextmenu-submenu>
      </div>
      <!-- 批量操作 -->
      <div>
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
