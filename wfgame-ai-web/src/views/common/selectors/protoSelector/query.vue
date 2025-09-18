<script lang="ts" setup>
import { ref, onMounted, nextTick } from "vue";
import { Search, RefreshLeft } from "@element-plus/icons-vue";
import {
  envTypeEnum,
  sortedEnum,
  protoTypeEnum,
  getLabel
} from "@/utils/enums";
import { listBranches, syncProto } from "@/api/testcase";
import { superRequest } from "@/utils/request";
import { ElMessageBox } from "element-plus";

defineOptions({
  name: "protoQuery"
});

const props = defineProps({
  queryForm: {
    type: Object,
    default: () => {
      return {
        page: 1,
        size: 20,
        keyword: "",
        env: envTypeEnum.TEST.value,
        ref: "master",
        proto_type: protoTypeEnum.REQUEST.value
      };
    }
  },
  envDisabled: {
    type: Boolean,
    default: true
  },
  protoTypeDisabled: {
    type: Boolean,
    default: true
  }
});

const queryForm = ref(props.queryForm);
const branchOptions = ref(["master"]);
const detailColumnVisible = ref(false);
const syncButtonLoading = ref(false);

onMounted(() => {
  fetchBranchOptions();
});

const fetchBranchOptions = () => {
  superRequest({
    apiFunc: listBranches,
    apiParams: { env: queryForm.value.env },
    onSucceed: data => {
      nextTick(() => {
        branchOptions.value = data;
        /**
         * 如果当前未选择分支，则默认选择 master/main 分支
         * 如果不存在 master/main 分支，则默认选择第一个分支
         */
        if (!queryForm.value.ref && data?.length > 0) {
          const refs = ["master", "main", data[0]];
          for (const ref of refs) {
            if (data.indexOf(ref) > -1) {
              queryForm.value.ref = ref;
              break;
            }
          }
          emit("fetch-data");
        }
      });
    }
  });
};
const emit = defineEmits(["fetch-data", "show-detail"]);

const handleQuerychanged = (val: any, key: string) => {
  queryForm.value[key] = val;
  emit("fetch-data");
};
const handleSwitchChanged = (val: any) => {
  detailColumnVisible.value = val;
  emit("show-detail", val);
};
const refresh = () => {
  emit("fetch-data");
};

const handleProtoSync = () => {
  // 二次弹窗确认提示：plan一旦创建后，不能编辑只能删除或者禁用！
  const envLabel = getLabel(envTypeEnum, queryForm.value.env);
  ElMessageBox.confirm(
    `此操作将从团队配置中【${envLabel}】预留的Gitlab仓库中, 同步【${queryForm.value.ref}】分支下所有 *.proto 文件包含的协议，确认继续？`,
    "协议同步",
    {
      confirmButtonText: "继续",
      cancelButtonText: "取消",
      type: "warning"
    }
  )
    .then(() => {
      // 发送新建请求
      superRequest({
        apiFunc: syncProto,
        apiParams: {
          env: queryForm.value.env,
          ref: queryForm.value.ref
        },
        onBeforeRequest: () => {
          syncButtonLoading.value = true;
        },
        onSucceed: () => {
          // 同步成功后，自动刷新数据
          refresh();
        },
        onCompleted: () => {
          syncButtonLoading.value = false;
        }
      });
    })
    .catch(() => {});
};

defineExpose({
  fetchBranchOptions
});
</script>

<template>
  <div class="flex justify-start mb-4 items-center">
    <!-- 环境选择 -->
    <div class="flex justify-center items-center">
      <el-tooltip
        content="请选择此用例的运行环境"
        effect="dark"
        placement="top"
      >
        <IconifyIconOnline icon="material-symbols:help-outline" />
      </el-tooltip>
      <span class="text-base mx-2 text-gray-500 dark:text-white">环 境</span>
    </div>
    <el-radio-group
      :disabled="props.envDisabled"
      v-model="queryForm.env"
      size="large"
      @change="handleQuerychanged($event, 'env')"
    >
      <el-radio
        v-for="item in sortedEnum(envTypeEnum)"
        :key="item.order"
        :label="item.value"
        border
        style="margin-right: 5px"
      >
        {{ item.label }}
      </el-radio>
    </el-radio-group>
    <el-divider direction="vertical" />
    <!-- 协议类型 -->
    <div class="flex justify-center items-center">
      <el-tooltip
        content="用例预期的请求协议类型"
        effect="dark"
        placement="top"
      >
        <IconifyIconOnline icon="material-symbols:help-outline" />
      </el-tooltip>
      <span class="text-base mx-2 text-gray-500 dark:text-white">类 型</span>
    </div>
    <div>
      <el-radio-group
        :disabled="props.protoTypeDisabled"
        v-model="queryForm.proto_type"
        size="large"
        @change="handleQuerychanged($event, 'proto_type')"
      >
        <el-radio
          :label="protoTypeEnum.REQUEST.value"
          border
          style="margin-right: 5px"
        >
          请求-Req
        </el-radio>
        <el-radio
          :label="protoTypeEnum.RESPONSE.value"
          border
          style="margin-right: 5px"
        >
          响应-Resp
        </el-radio>
      </el-radio-group>
    </div>
    <el-divider direction="vertical" />
    <!-- 分支 -->
    <div class="flex justify-center items-center">
      <el-tooltip
        content="请选择环境对应Gitlab中的分支"
        effect="dark"
        placement="top"
      >
        <IconifyIconOnline icon="material-symbols:help-outline" />
      </el-tooltip>
      <span class="text-base mx-2 text-gray-500 dark:text-white">分 支</span>
    </div>
    <el-select
      style="width: 160px"
      v-model="queryForm.ref"
      filterable
      placeholder="请选择分支"
      size="large"
      @change="handleQuerychanged($event, 'ref')"
    >
      <el-option
        v-for="branch in branchOptions"
        :key="branch"
        :label="branch"
        :value="branch"
      />
    </el-select>
    <el-divider direction="vertical" />
    <!-- 搜索框 -->
    <div class="w-64">
      <el-input
        v-model="queryForm.keyword"
        size="large"
        placeholder="请输入关键字搜索"
        :prefix-icon="Search"
        clearable
        @change="handleQuerychanged($event, 'keyword')"
      />
    </div>
    <el-divider direction="vertical" />
    <el-switch
      v-model="detailColumnVisible"
      :active-value="true"
      :inactive-value="false"
      active-text="显示详情"
      @change="handleSwitchChanged"
    />
    <div class="ml-auto">
      <el-button :icon="RefreshLeft" size="large" plain @click="refresh">
        刷 新
      </el-button>
      <el-button
        :loading="syncButtonLoading"
        size="large"
        type="primary"
        plain
        @click="handleProtoSync"
        >同步协议</el-button
      >
    </div>
  </div>
</template>
