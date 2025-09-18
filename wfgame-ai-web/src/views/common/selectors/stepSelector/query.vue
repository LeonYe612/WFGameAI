<script lang="ts" setup>
import { ref } from "vue";
import { Search, RefreshLeft } from "@element-plus/icons-vue";
import { envEnum } from "@/utils/enums";

defineOptions({
  name: "TestcaseQuery"
});

const props = defineProps({
  queryForm: {
    type: Object,
    default: () => {
      return {};
    }
  }
});

const envOptions = [
  {
    label: "全部环境",
    value: null
  },
  {
    label: "测试环境",
    value: envEnum.TEST
  },
  {
    label: "开发环境",
    value: envEnum.DEV
  }
];

const queryForm = ref(props.queryForm);

const emit = defineEmits(["fetch-data", "reset"]);

const handleKeywordChange = val => {
  queryForm.value.keyword = val;
  emit("fetch-data");
};

const handleEnvChange = val => {
  queryForm.value.env = val;
  emit("fetch-data");
};

const reset = () => {
  queryForm.value.page = 1;
  queryForm.value.size = 20;
  queryForm.value.keyword = "";
  emit("fetch-data");
  emit("reset");
};

defineExpose({ reset });
</script>

<template>
  <div class="flex justify-start items-center py-4 px-2">
    <div class="w-32 mr-1">
      <el-select
        size="large"
        v-model="queryForm.env"
        placeholder="选择环境"
        @change="handleEnvChange"
      >
        <el-option
          v-for="item in envOptions"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
      </el-select>
    </div>
    <div class="flex-1 overflow-hidden">
      <el-input
        style="width: 100%"
        v-model="queryForm.keyword"
        size="large"
        placeholder="搜索用例"
        :prefix-icon="Search"
        clearable
        @change="handleKeywordChange"
      />
    </div>
    <div class="ml-auto flex items-center">
      <el-divider direction="vertical" />
      <el-button :icon="RefreshLeft" size="large" plain @click="reset">
        查询重置
      </el-button>
    </div>
  </div>
</template>
