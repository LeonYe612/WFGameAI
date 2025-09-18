<script setup lang="ts">
import { CaretRight } from "@element-plus/icons-vue";
import { envEnum, configTestTypeEnum } from "@/utils/enums";
import { useConfigTesterHook } from "../utils/configTesterHook";

defineOptions({
  name: "ConfigsTester"
});

const props = defineProps({
  env: {
    type: String,
    default: envEnum.TEST.toString()
  }
});

const options = [
  {
    label: "GIT",
    options: [
      configTestTypeEnum.TYPE1,
      configTestTypeEnum.TYPE2,
      configTestTypeEnum.TYPE3
    ]
  },
  {
    label: "GM",
    options: [configTestTypeEnum.TYPE4, configTestTypeEnum.TYPE5]
  },
  {
    label: "SCRIPT",
    options: [configTestTypeEnum.TYPE6, configTestTypeEnum.TYPE7]
  }
];

const {
  // ref data
  testTypeId,
  loading,
  dialogVisible,
  isSuccess,
  subTitle,
  content,
  // methods
  onVerifyButtonClick
} = useConfigTesterHook(props);
</script>
<template>
  <div>
    <el-select
      v-model="testTypeId"
      placeholder="请选择待验证配置"
      size="large"
      style="width: 280px"
    >
      <el-option-group
        v-for="group in options"
        :key="group.label"
        :label="group.label"
      >
        <el-option
          v-for="item in group.options"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
      </el-option-group>
    </el-select>
    <el-button
      :icon="CaretRight"
      type="default"
      plain
      :loading="loading"
      size="large"
      @click="onVerifyButtonClick"
    >
      验证
    </el-button>
    <!-- 测试结果弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      title="配置验证结果"
      width="40vw"
      :draggable="true"
      align-center
      :modal="true"
    >
      <div class="w-full mt-[-20px] overflow-hidden">
        <div>
          <el-result
            v-loading="loading"
            :icon="isSuccess ? 'success' : 'error'"
            :title="isSuccess ? '验证成功' : '验证失败'"
            :sub-title="subTitle"
          />
        </div>
        <div class="w-full h-[40vh]" v-if="content">
          <el-scrollbar class="h-full">
            <p
              class="p-2 bg-yellow-100 mt-2 rounded-lg font-thin w-full"
              style="white-space: pre-wrap; line-height: 26px"
            >
              {{ content }}
            </p>
          </el-scrollbar>
        </div>
      </div>
    </el-dialog>
  </div>
</template>
