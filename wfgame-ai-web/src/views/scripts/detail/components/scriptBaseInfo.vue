<script setup lang="ts">
import { List, Folder } from "@element-plus/icons-vue";
import {
  onMounted,
  computed,
  onUnmounted,
  onActivated,
  onDeactivated
} from "vue";
import { useScriptStoreHook } from "@/store/modules/script";
import { categoryApi } from "@/api/scripts";
import { scriptTypeEnum, sortedEnum } from "@/utils/enums";
import { ref } from "vue";
import CategoryEditorDialog from "@/views/common/editor/categoryEditor/dialog.vue";

const scriptStore = useScriptStoreHook();

defineOptions({
  name: "ScriptBaseInfo"
});

const emit = defineEmits<{
  save: [];
}>();

const categories = ref([]);
const showCategoryEditor = ref(false);
const scriptItem = computed(() => scriptStore.scriptItem);

const fetchCategories = async () => {
  const { data } = await categoryApi.tree();
  categories.value = data || [];
};

// 监听键盘保存事件
const handleKeyDown = (event: KeyboardEvent) => {
  if (event.ctrlKey && event.key === "s") {
    event.preventDefault();
    handleSave();
  }
};

onActivated(() => {
  fetchCategories();
  window.addEventListener("keydown", handleKeyDown);
});

onDeactivated(() => {
  window.removeEventListener("keydown", handleKeyDown);
});

onMounted(async () => {
  fetchCategories();
  window.addEventListener("keydown", handleKeyDown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeyDown);
});

const handleSave = async () => {
  await scriptStore.saveScript();
  emit("save");
};
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center gap-4">
      <el-icon size="30">
        <List />
      </el-icon>
      <el-input
        style="min-width: 400px; width: auto !important"
        class="step-name"
        clearable
        v-model="scriptItem.name"
        placeholder="脚本名称"
      />
      <el-divider direction="vertical" />
      <el-tree-select
        v-model="scriptItem.category"
        check-strictly
        clearable
        :data="categories"
        default-expand-all
        highlight-current
        :props="{
          children: 'children',
          label: 'name',
          value: 'id'
        }"
        :render-after-expand="false"
        style="width: 255px"
      />
      <el-button
        plain
        type="warning"
        title="目录管理"
        @click="showCategoryEditor = true"
      >
        <el-icon size="18">
          <Folder />
        </el-icon>
      </el-button>
      <el-divider direction="vertical" />
      <el-select
        v-model="scriptItem.type"
        placeholder="类型"
        style="width: 120px"
      >
        <el-option
          v-for="item in sortedEnum(scriptTypeEnum)"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
      </el-select>
      <el-divider direction="vertical" />
      <el-switch
        class="scale-[1.1]"
        v-model="scriptItem.is_active"
        inline-prompt
        active-text="激活状态"
        inactive-text="禁用状态"
      />
      <el-switch
        class="scale-[1.1]"
        v-model="scriptItem.include_in_log"
        inline-prompt
        active-text="启用日志"
        inactive-text="禁用日志"
      />
      <el-button class="ml-auto" type="success" @click="handleSave">
        保存（Ctrl+s）
      </el-button>
    </div>
    <div>
      <el-input
        type="textarea"
        :rows="1"
        v-model="scriptItem.description"
        placeholder="您可以在此添加此脚本的额外说明"
      />
    </div>
    <!-- 目录编辑弹窗 -->
    <CategoryEditorDialog
      v-model="showCategoryEditor"
      @closed="fetchCategories"
    />
  </div>
</template>

<style lang="scss" scoped>
.step-name :deep() {
  .el-input__wrapper {
    background-color: transparent;
    box-shadow: none;
    border-radius: 0;
    padding: 0;
    border-bottom: 1px solid #dcdfe6;
  }
  .el-input__inner {
    font-size: 1.5rem;
    font-weight: bold;
  }
}
</style>
