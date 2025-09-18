<script lang="ts" setup>
import { ref } from "vue";
import { Search, RefreshLeft } from "@element-plus/icons-vue";

defineOptions({
  name: "SysUserManagementQuery"
});

const props = defineProps({
  queryForm: {
    type: Object,
    default: () => {
      return {
        keyword: ""
      };
    }
  }
});

const queryForm = ref(props.queryForm);

const emit = defineEmits(["fetch-data", "reset"]);

const handleKeywordChange = val => {
  queryForm.value.keyword = val;
  emit("fetch-data");
};

const handleResetClick = () => {
  queryForm.value.page = 1;
  queryForm.value.size = 20;
  queryForm.value.keyword = "";
  emit("fetch-data");
  emit("reset");
};
</script>

<template>
  <div class="flex justify-start mb-4">
    <div class="me-4">
      <el-button
        :icon="RefreshLeft"
        size="large"
        type="info"
        plain
        @click="handleResetClick"
      >
        查询重置
      </el-button>
    </div>
    <div class="w-72">
      <el-input
        v-model="queryForm.keyword"
        size="large"
        placeholder="请输入关键字搜索"
        :prefix-icon="Search"
        clearable
        @change="handleKeywordChange"
      />
    </div>
  </div>
</template>
