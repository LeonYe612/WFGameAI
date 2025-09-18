<script setup lang="ts">
import { computed, watch, ref, onMounted } from "vue";
import { dayOfWeekEnum, getLabel } from "@/utils/enums";

defineOptions({
  name: "CircleSelectorResult"
});
const props = defineProps({
  settings: {
    type: Object,
    default: () => ({})
  }
});
const days = ref([]);
const daysDesc = computed(() => {
  const arr = [];
  const len = props.settings?.which_days?.length || 0;
  if (!len) return "暂未选择";
  // 非原地排序 which_days
  const sortedWhichDays = props.settings.which_days
    .slice()
    .sort((a, b) => a - b);
  for (let i = 0; i < len; i++) {
    arr.push(getLabel(dayOfWeekEnum, sortedWhichDays[i]));
  }
  return arr?.length ? arr.join("、") : "暂未选择";
});

const generateDaysList = () => {
  const { date_range, which_days } = props.settings;
  if (date_range?.length && which_days?.length) {
    days.value.splice(0, days.value.length);
    days.value = listAllCircleDays(date_range, which_days);
  }
};

onMounted(() => {
  generateDaysList();
});

watch(
  () => props.settings,
  () => {
    generateDaysList();
  },
  {
    deep: true
  }
);

const formatDate = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");

  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
};

const listAllCircleDays = (date_range: string[], which_days: number[]) => {
  const [start, end] = date_range.map(dateString => new Date(dateString));
  const daysInRange = [];
  for (
    let date = new Date(start);
    date <= end;
    date.setDate(date.getDate() + 1)
  ) {
    const dayOfWeek = date.getDay() === 0 ? 7 : date.getDay(); // 修正星期天的值为7
    if (which_days.includes(dayOfWeek)) {
      daysInRange.push({
        date: formatDate(new Date(date)),
        dayOfWeek: getLabel(dayOfWeekEnum, dayOfWeek)
      });
    }
  }
  return daysInRange;
};
</script>

<template>
  <div>
    <div>
      日期范围：
      <span class="font-bold text-green-500">
        {{
          props.settings.date_range
            ? props.settings.date_range[0] || "暂未选择"
            : "暂未选择"
        }}
      </span>
      ~
      <span class="font-bold text-green-500">
        {{
          props.settings.date_range
            ? props.settings.date_range[1] || "暂未选择"
            : "暂未选择"
        }}
      </span>
    </div>
    <div>
      上述日期范围内每周的：
      <span class="font-bold text-green-500">
        {{ daysDesc }}
      </span>
    </div>
    <div>
      每天
      <span class="font-bold text-green-500">
        {{ props.settings.run_time || "暂未选择" }}
      </span>
      运行测试计划， 总计执行
      <span class="font-bold text-green-500">
        {{ days?.length || 0 }}
      </span>
      次
    </div>
  </div>
</template>

<style scoped></style>
