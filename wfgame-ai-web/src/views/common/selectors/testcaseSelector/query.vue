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
    <!-- 运行环境 -->
    <span class="text-base mx-2 text-gray-400 dark:text-white">
      运行环境：
    </span>
    <div>
      <el-radio-group
        disabled
        v-model="queryForm.env"
        size="large"
        @change="handleEnvChange"
      >
        <el-radio label="" border style="margin-right: 5px">全部环境</el-radio>
        <el-radio :label="envEnum.TEST" border style="margin-right: 5px">
          测试环境
        </el-radio>
        <el-radio :label="envEnum.DEV" border style="margin-right: 5px">
          开发环境
        </el-radio>
      </el-radio-group>
    </div>
    <div class="ml-auto flex items-center">
      <el-input
        v-model="queryForm.keyword"
        size="large"
        placeholder="请输入关键字搜索"
        :prefix-icon="Search"
        clearable
        @change="handleKeywordChange"
      />
      <el-divider direction="vertical" />
      <el-button :icon="RefreshLeft" size="large" plain @click="reset">
        查询重置
      </el-button>
    </div>
  </div>
</template>
