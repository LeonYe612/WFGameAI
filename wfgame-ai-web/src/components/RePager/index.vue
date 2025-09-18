<script lang="ts" setup>
import { ref } from "vue";

defineOptions({
  name: "ComponentPager"
});

const props = defineProps({
  queryForm: {
    type: Object,
    default: () => {
      return {
        page: 1,
        size: 20
      };
    }
  },
  total: {
    type: Number,
    default: 0
  },
  layout: {
    type: String,
    default: "total, sizes, prev, pager, next, jumper"
  },
  pageSizes: {
    type: Array as () => number[],
    default: () => [10, 20, 50, 100, 200] as number[]
  },
  background: {
    type: Boolean,
    default: true
  }
});

const queryForm = ref(props.queryForm);

const emit = defineEmits(["fetch-data"]);

const handleSizeChange = val => {
  queryForm.value.size = val;
  emit("fetch-data");
};
const handleCurrentChange = val => {
  queryForm.value.page = val;
  emit("fetch-data");
};
</script>

<template>
  <div class="h-14 flex items-end justify-center w-full">
    <div class="flex justify-center w-full h-full">
      <div class="flex-1 px-2 flex items-center">
        <slot name="left" />
      </div>
      <el-pagination
        :background="props.background"
        :current-page="queryForm.page"
        :layout="props.layout"
        :page-size="queryForm.size"
        :page-sizes="props.pageSizes"
        :total="total"
        @current-change="handleCurrentChange"
        @size-change="handleSizeChange"
      />
      <div class="flex-1">
        <slot name="right" />
      </div>
    </div>
  </div>
</template>
