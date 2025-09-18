<script setup lang="ts">
import {
  Connection,
  EditPen,
  Plus,
  UploadFilled,
  InfoFilled,
  Message,
  ChatDotSquare,
  Minus
} from "@element-plus/icons-vue";
import { computed, nextTick, watch, defineProps } from "vue";
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { protoGenreEnum, protoTypeEnum } from "@/utils/enums";
import { message } from "@/utils/message";
import ProtoOperatorBar from "./protoOperateBar.vue";
import ProtoParamsTree from "./protoParamsTree.vue";
import { listProto } from "@/api/testcase";
import { superRequest } from "@/utils/request";
import { ref } from "vue";

defineOptions({
  name: "TestcaseStepDetailNew"
});

defineProps({
  editable: {
    type: Boolean,
    default: false
  }
});

const store = useTestcaseStoreHook();
const protoTreeRef = ref(null);

const hasCurrentSetp = computed(() => {
  return !!store.currentStep?.id;
});

interface ProtoNode {
  key: string;
  type: "send" | "recv";
  index: number;
  label: string;
  icon: any;
  iconColor: string;
  children: ProtoNode[];
}
const protoSelectedKey = computed(() => {
  return `${store.currentProtoType}-${store.currentProtoIndex}`;
});
const protosData = computed(() => {
  const tree = [];
  if (!store.currentStep?.id) {
    return [];
  }
  // 添加 send proto 节点 & recv proto 节点
  const protoTypes = [protoGenreEnum.SEND.value, protoGenreEnum.RECV.value];
  protoTypes.forEach((protoType, typeIdx) => {
    const protoNode: ProtoNode = {
      key: protoType,
      type: protoType,
      index: typeIdx,
      icon: protoType === protoGenreEnum.SEND.value ? Message : ChatDotSquare,
      iconColor: protoType === protoGenreEnum.SEND.value ? "green" : "orange",
      label: protoType === protoGenreEnum.SEND.value ? "请求" : "响应",
      children: []
    };
    if (store.currentStep?.[protoType]?.length) {
      protoNode.children = store.currentStep[protoType].map((item, index) => {
        return {
          key: `${protoType}-${index}`,
          type: protoType,
          index: index,
          label: item.proto_name,
          icon: null,
          children: []
        };
      });
    }
    tree.push(protoNode);
  });
  return tree;
});
// 新增协议
const handleAddProto = (item: ProtoNode) => {
  // a. 校验能否新增：请求只能新增一个，响应可以新增多个
  if (
    item.type === protoGenreEnum.SEND.value &&
    store.currentStep?.send?.length > 0
  ) {
    message("每个步骤只能添加一个请求协议！", { type: "warning" });
    return;
  }
  // c. 打开协议选择器
  store.protoSelectorType =
    item.type === protoGenreEnum.SEND.value
      ? protoTypeEnum.REQUEST.value
      : protoTypeEnum.RESPONSE.value;
  nextTick(() => {
    store.components?.protoSelectorRef?.show();
  });
};

/**
 * 自动根据用户已选择的请求，自动导入请求对应的响应
 * @param item
 */
const handleAutoAddProto = async (item: ProtoNode) => {
  const sendProto = store.GET_CURRENT_PROTOINFO(protoGenreEnum.SEND.value, 0);
  if (!sendProto) {
    message("尚未选择请求协议，无法智能导入响应！", { type: "warning" });
    return;
  }
  // 根据请求协议名称，解析出关键字
  if (!String(sendProto.proto_message).endsWith("Req")) {
    message("请求协议非常规命名，无法智能导入响应！", { type: "warning" });
    return;
  }
  // const keyword = String(sendProto.proto_message).slice(0, -3).concat("Resp");
  const keyword = String(sendProto.proto_message).slice(0, -3);
  // 设置协议选择器类型为：响应类型
  store.protoSelectorType =
    item.type === protoGenreEnum.SEND.value
      ? protoTypeEnum.REQUEST.value
      : protoTypeEnum.RESPONSE.value;
  const { data } = await superRequest({
    apiFunc: listProto,
    apiParams: {
      page: 1,
      size: 100,
      keyword: keyword,
      env: store.baseInfo.env,
      ref: "",
      proto_type: protoTypeEnum.RESPONSE.value
    }
  }).catch(err => {
    Promise.reject(err);
  });
  if (!data?.list?.length) {
    message("未智能匹配到响应协议，请手动选择！", { type: "warning" });
    return;
  }
  // 过滤出符合要求的协议
  const targets = data.list.filter(item => {
    return (
      String(item.proto_message)
        .toLowerCase()
        .includes(keyword.toLowerCase()) && item.proto_id > 0
    );
  });
  if (!targets.length) {
    message("未智能匹配到响应协议，请手动选择！", { type: "warning" });
    return;
  }
  store.handleProtoSelectorComplete([targets[0]]);
};
/**
 * 有些老的已填写数据, 可能protoInfo中没有
 * protoInfo.verify_rules.omit_code
 * protoInfo.verify_rules.omit_data
 * 需要为其补齐
 */
const autoAddCodeSettingsFields = protoInfo => {
  if (!protoInfo?.verify_rules) {
    protoInfo.verify_rules = {};
  }
  if (typeof protoInfo?.verify_rules?.omit_code !== "boolean") {
    protoInfo.verify_rules.omit_code = false;
  }
  if (typeof protoInfo?.verify_rules?.omit_data !== "boolean") {
    protoInfo.verify_rules.omit_data = false;
  }
  protoTreeRef.value?.setCheckCode(!protoInfo.verify_rules.omit_code);
  protoTreeRef.value?.setCheckData(!protoInfo.verify_rules.omit_data);
};

watch(
  [() => store.currentProtoIndex, () => store.currentProtoType],
  ([protoIndex, protoType]) => {
    if (store.currentStep?.[protoType]?.[protoIndex]) {
      store.currentProto = store.currentStep[protoType][protoIndex];
      if (!store.currentProto?.proto_data?.length) {
        store.currentProto.proto_data = [];
      }
      // a. 自动补足字段
      autoAddCodeSettingsFields(store.currentProto);
    } else {
      store.currentProto = null;
    }
    // console.log("watcher 被触发了！！！", store.currentProto?.proto_message);
  },
  {
    immediate: true,
    flush: "pre"
  }
);
</script>

<template>
  <el-container class="h-full" v-loading="store.shareState.stepDetailLoading">
    <!-- A. 步骤名称输入框 -->
    <el-header class="pt-2">
      <div
        class="mt-2 flex items-center p-8 bg-slate-100 dark:bg-transparent rounded-lg w-full h-12"
      >
        <div class="flex items-center">
          <el-icon size="22">
            <InfoFilled />
          </el-icon>
          <span class="text-lg font-bold ml-2 text-gray-600 dark:text-white">
            {{ "步骤 " + (store.currentStepIndex + 1 || "") }}：
          </span>
        </div>
        <div class="flex-1 px-4 step-name" v-if="hasCurrentSetp">
          <el-input
            :disabled="!editable"
            clearable
            v-model="store.currentStep.name"
            size="large"
            placeholder="请在此输入步骤名称"
            :prefix-icon="EditPen"
            @change="store.UPDATE_STEPS_LIST_ITEM('name', $event)"
          />
        </div>
        <div v-if="false">
          <el-button
            :icon="UploadFilled"
            :loading="store.shareState.stepSaveLoading"
            size="large"
            type="primary"
            style="width: 120px"
            @click="store.saveStep"
          >
            保存
          </el-button>
        </div>
      </div>
    </el-header>
    <!-- B. 步骤协议编辑区域 -->
    <el-main>
      <div
        v-if="!hasCurrentSetp"
        class="w-full h-full flex justify-center items-center"
      >
        <el-empty description="单击左侧步骤列表中的步骤以查看步骤详情！" />
      </div>
      <div
        v-else
        class="overflow-hidden flex w-full h-full max-h-full border border-gray-300 shadow-sm p-2 rounded-md"
      >
        <!-- LEFT：协议选择区域 -->
        <el-scrollbar
          class="w-[32%] h-full p-1 rounded-lg overflow-hidden border-gray-300 border"
        >
          <div
            v-for="item in protosData"
            :key="item.key"
            :class="{
              'mt-6': item.type === protoGenreEnum.RECV.value
            }"
          >
            <!-- 协议类型 -->
            <div
              class="flex items-center p-4 rounded-lg w-full h-14"
              :class="{
                'bg-orange-100': item.type === protoGenreEnum.SEND.value,
                'bg-cyan-100': item.type === protoGenreEnum.RECV.value
              }"
            >
              <div
                class="flex items-center w-full"
                :class="{
                  'text-orange-500': item.type === protoGenreEnum.SEND.value,
                  'text-cyan-500': item.type === protoGenreEnum.RECV.value
                }"
              >
                <el-icon size="22">
                  <component :is="item.icon" />
                </el-icon>
                <span class="text-base font-bold ml-2">
                  {{ item.label }}
                </span>
              </div>
              <div
                class="ml-auto flex items-center justify-center"
                :class="{
                  'flex-col': store.shareState.baseInfoFormVisible
                }"
              >
                <el-button
                  v-if="item.type === protoGenreEnum.RECV.value"
                  :class="{
                    'mb-1': store.shareState.baseInfoFormVisible,
                    'mr-1': !store.shareState.baseInfoFormVisible
                  }"
                  title="将会自动查找请求对应的响应并导入到步骤中"
                  type="success"
                  :icon="Connection"
                  size="small"
                  round
                  plain
                  @click="handleAutoAddProto(item)"
                  >智能添加
                </el-button>
                <el-button
                  style="margin-left: 0"
                  :type="
                    item.type === protoGenreEnum.SEND.value
                      ? 'warning'
                      : 'primary'
                  "
                  :icon="Plus"
                  size="small"
                  round
                  plain
                  @click="handleAddProto(item)"
                  >添加{{ item.label }}
                </el-button>
              </div>
            </div>
            <!-- 协议子项列表 -->
            <div
              v-for="proto in item.children"
              :key="proto.key"
              class="cursor-pointer mt-2 px-2 h-11 shadow-sm"
              @click.stop="store.activeProto(proto.type, proto.index)"
            >
              <div
                class="h-full border rounded-md flex justify-start items-center hover:bg-slate-50 overflow-hidden"
                :class="{
                  'border-2 border-blue-400 bg-slate-100':
                    proto.key === protoSelectedKey,
                  'border-slate-200': proto.key !== protoSelectedKey
                }"
              >
                <!-- 协议Index -->
                <div
                  class="ml-2 text-gray-400 font-bold"
                  :class="{ 'text-primary': proto.key === protoSelectedKey }"
                >
                  {{ proto.index + 1 }}.
                </div>
                <!-- 协议名称 -->
                <div class="ml-1 max-w-[65%] flex items-center">
                  <span class="text-gray-600 truncate text-base">
                    {{ proto.label || "未命名协议" }}
                  </span>
                </div>
                <!-- 协议操作 -->
                <div
                  class="h-full ml-auto flex items-center mr-3"
                  v-if="editable"
                >
                  <!-- 删除按钮 -->
                  <el-popconfirm
                    title="移除此协议?"
                    @confirm="
                      store.handleRemoveProtoInCurrentStep(
                        proto.type,
                        proto.index
                      )
                    "
                  >
                    <template #reference>
                      <el-button
                        size="small"
                        title="删除协议"
                        :icon="Minus"
                        circle
                        plain
                        type="danger"
                        @click.stop
                      />
                    </template>
                  </el-popconfirm>
                </div>
              </div>
            </div>
          </div>
        </el-scrollbar>
        <!-- RIGHT：协议详情 & 参数录入 -->
        <div
          class="w-[68%] h-full rounded-lg overflow-hidden px-2 flex flex-col"
        >
          <el-empty
            v-show="!store.currentProto"
            :image-size="200"
            description="尚未选择任何协议"
          />
          <!--协议操作栏 -->
          <ProtoOperatorBar
            v-show="store.currentProto"
            :proto="store.currentProto"
          />
          <!-- 协议Code 和 协议参数 -->
          <ProtoParamsTree
            ref="protoTreeRef"
            class="flex-1 overflow-hidden"
            v-show="store.currentProto"
            :proto-index="store.currentProtoIndex"
            :proto-type="store.currentProtoType"
            :editable="editable"
          />
        </div>
      </div>
    </el-main>
  </el-container>
</template>
<style lang="scss" scoped>
.step-name :deep() .el-input .el-input__wrapper {
  background-color: transparent !important;
  font-size: 18px;
  box-shadow: none !important;
  font-weight: bolder;
}
.step-name :deep() .el-input__inner {
  font-weight: bold;
}
.currentProtoClass {
  border-bottom: solid 2px #409eff !important;
  color: #409eff;
  font-weight: bolder;
}
</style>
