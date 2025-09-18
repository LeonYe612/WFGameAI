<!-- 此组件弹出计划执行的周期设置 -->
<script lang="ts" setup>
import { ref } from "vue";
import { formRules } from "./rules";
import { usePlanStoreHook } from "@/store/modules/plan";
import { cloneDeep } from "@pureadmin/utils";
import CircleSelectorResult from "./result.vue";
import { dayOfWeekEnum, sortedEnum } from "@/utils/enums";

const store = usePlanStoreHook();
defineOptions({
  name: "CircleSelector"
});

const emit = defineEmits(["complete"]);
const dialogVisible = ref(false);
const title = ref("请设置循环周期：");
const formRef = ref(null);

const settings = {
  date_range: null, // 初始为空字符串，应该根据 DateModelType 的定义来赋值
  which_days: [], // 在一周的哪些天执行
  run_time: "" // 运行时间
};
const settingsRef = ref(settings);

const setDisabledDate = dt => {
  return dt.getTime() < Date.now() - 8.64e7;
};

const stringToDate = timeString => {
  const [hours, minutes, seconds] = timeString.split(":");
  const date = new Date();
  date.setHours(hours);
  date.setMinutes(minutes);
  date.setSeconds(seconds);
  return date;
};

const show = (initFromStore = true) => {
  if (initFromStore) {
    const circle = store.info.run_info.circle;
    settingsRef.value.date_range = cloneDeep(circle.date_range);
    settingsRef.value.which_days = cloneDeep(circle.which_days);
    settingsRef.value.run_time = circle.run_time;
  }
  dialogVisible.value = true;
};

const cancel = () => {
  dialogVisible.value = false;
};

const confirm = async formEl => {
  if (!formEl) return;
  formEl.validate(valid => {
    if (valid) {
      dialogVisible.value = false;
      emit("complete", settingsRef.value);
    }
  });
};

defineExpose({ show });
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    width="40vw"
    :draggable="true"
    align-center
  >
    <el-main>
      <el-form
        :model="settingsRef"
        size="large"
        label-width="100px"
        ref="formRef"
        :rules="formRules"
      >
        <!-- 周期执行的日期范围 -->
        <el-form-item prop="date_range" class="pr-16">
          <template #label>
            <div class="flex justify-center items-center">
              <el-tooltip
                content="请选择测试计划运行周期的起始日期"
                effect="dark"
                placement="top"
              >
                <IconifyIconOnline icon="material-symbols:help-outline" />
              </el-tooltip>
              <label>起始日期</label>
            </div>
          </template>
          <el-date-picker
            v-model="settingsRef.date_range"
            unlink-panels
            value-format="YYYY-MM-DD HH:mm:ss"
            type="daterange"
            range-separator="~"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            :default-time="[stringToDate('00:00:00'), stringToDate('23:59:59')]"
            :disabledDate="setDisabledDate"
          />
        </el-form-item>
        <!-- 周期执行时候执行哪些天 -->
        <el-form-item prop="which_days" class="pr-16">
          <template #label>
            <div class="flex justify-center items-center">
              <el-tooltip
                content="请设置计划在每周的哪些天中执行"
                effect="dark"
                placement="top"
              >
                <IconifyIconOnline icon="material-symbols:help-outline" />
              </el-tooltip>
              <label>推送设置</label>
            </div>
          </template>
          <el-checkbox-group v-model="settingsRef.which_days" size="large">
            <el-checkbox-button
              v-for="item in sortedEnum(dayOfWeekEnum)"
              :key="item.value"
              :label="item.value"
            >
              {{ item.label }}
            </el-checkbox-button>
          </el-checkbox-group>
        </el-form-item>
        <!-- 每天中运行的时间 -->
        <el-form-item prop="run_time" class="pr-16">
          <template #label>
            <div class="flex justify-center items-center">
              <el-tooltip
                content="请设置周期运行时当天执行计划的时间"
                effect="dark"
                placement="top"
              >
                <IconifyIconOnline icon="material-symbols:help-outline" />
              </el-tooltip>
              <label>运行时间</label>
            </div>
          </template>
          <el-time-picker
            v-model="settingsRef.run_time"
            placeholder="请选择时间"
            value-format="HH:mm:ss"
          />
        </el-form-item>
        <!-- 计划说明 -->
        <el-form-item class="pr-16">
          <template #label>
            <div class="flex justify-center items-center">
              <IconifyIconOnline icon="ph:warning-circle-duotone" />
              <label>设置说明</label>
            </div>
          </template>
          <CircleSelectorResult :settings="settingsRef" />
        </el-form-item>
      </el-form>
    </el-main>
    <template #footer>
      <el-button @click="cancel" size="large">取 消</el-button>
      <el-button type="primary" @click="confirm(formRef)" size="large">
        确定
      </el-button>
    </template>
  </el-dialog>
</template>
