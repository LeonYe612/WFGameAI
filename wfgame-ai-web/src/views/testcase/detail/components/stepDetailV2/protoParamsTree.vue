<script setup lang="tsx">
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { protoGenreEnum } from "@/utils/enums";
import CaretRightIcon from "@/assets/svg/caretRight.svg?component";
import {
  Plus,
  Minus,
  Connection,
  CloseBold,
  FullScreen
} from "@element-plus/icons-vue";
import { useGmHelperHooks } from "./hooks/gmHelperHooks";
import { useParamTreeHooks } from "./hooks/paramTreeHooks";
import { useMenuOperateHooks } from "./hooks/menuOperateHooks";
import GmHelper from "../gmHelper.vue";
import BigInput from "./bigInput.vue";
import TreeContextMenu from "./treeContextMenu.vue";
import saveVariableDialog from "./saveVariableDialog.vue";
import FishInfoDialog from "@/views/testcase/detail/components/stepDetailV2/fishInfoDialog.vue";
import FishSvg from "@/assets/svg/fish.svg?component";
import ScoreSvg from "@/assets/svg/score.svg?component";
import ScoreInfoDialog from "@/views/testcase/detail/components/stepDetailV2/scoreInfoDialog.vue";

const testcaseStore = useTestcaseStoreHook();

defineOptions({
  name: "ProtoParamsTree"
});

const props = defineProps({
  protoType: {
    type: String,
    default: protoGenreEnum.SEND.value
  },
  protoIndex: {
    type: Number,
    default: 0
  },
  editable: {
    type: Boolean,
    default: true
  }
});

/** Gm Helper 相关代码 */
const {
  gmHelperRef,
  gmButtonVisible,
  handleShowGmHelperDialog,
  handleGmHelperCompleted
} = useGmHelperHooks();

/** Param Tree 相关代码 */
const {
  // constants
  treeProps,
  treeNodeHeight,
  // ref
  treeContainerRef,
  paramTreeRef,
  treeContextMenuRef,
  bigInputRef,
  saveVariableDialogRef,
  fishInfoDialogRef,
  scoreInfoDialogRef,
  treeHeight,
  checkCode,
  checkData,
  enableTreeCheck,
  // computed
  tooltip,
  fieldClass,
  isProto3BasicType,
  isProto3NumberType,
  isCustomVar,
  // methods
  setCheckCode,
  setCheckData,
  handleCodeChanged,
  onCheckCodeChange,
  onCheckDataChange,
  onOperatorClick,
  showBigInputDialog,
  deleteRepeatedItem,
  addRepeatedItem,
  handleNodeContextMenu,
  showFishInfoDialog,
  showScoreInfoDialog
} = useParamTreeHooks();

/** 右键Menu 相关代码 */
const {
  menuTipBarVisible,
  menuTipBarLabel,
  handleMenuClick,
  menuTipBarCancel,
  menuTipBarConfirm,
  setNodeReference,
  deleteNodeReference,
  setNodeExpression,
  deleteNodeExpression
} = useMenuOperateHooks({
  paramTreeRef: paramTreeRef,
  enableTreeCheck: enableTreeCheck,
  saveVariableDialogRef: saveVariableDialogRef
});

defineExpose({
  setCheckCode,
  setCheckData
});
</script>

<template>
  <div class="w-full h-full flex flex-col" v-if="testcaseStore.currentProto">
    <!-- A. 响应码校验 (只在响应类型中显示) -->
    <div
      v-show="props.protoType === protoGenreEnum.RECV.value"
      class="relative"
    >
      <el-divider content-position="left">
        <el-checkbox
          :disabled="!editable"
          v-model="checkCode"
          label="校验响应码"
          size="large"
          @change="onCheckCodeChange"
        />
      </el-divider>
      <div v-show="checkCode" class="flex items-center justify-between h-8">
        <el-input-number
          clearable
          style="width: 180px; margin-left: 50px"
          type="number"
          :disabled="!editable"
          v-model="testcaseStore.currentProto.code"
          :controls="false"
          placeholder="请填写预期响应码"
          @change="handleCodeChanged"
          :value-on-clear="0"
        />
        <span>
          <span class="text-base font-light text-gray-400">含义：</span>
          <span
            class="text-base mr-4 font-light"
            :class="{
              'text-red-400':
                testcaseStore.currentProto.code_desc == '错误码不存在',
              'text-yellow-500': testcaseStore.currentProto.code != 0,
              'text-green-400': testcaseStore.currentProto.code == 0
            }"
          >
            {{
              testcaseStore.currentProto.code == 0
                ? "成功"
                : testcaseStore.currentProto.code_desc
            }}
          </span>
        </span>
      </div>
      <div v-show="!checkCode" class="flex items-center justify-between h-8">
        <span
          style="margin-left: 50px"
          class="text-primary text-base font-light"
          >⚠ 已设置此预期响应不校验响应码</span
        >
      </div>
      <div class="h-1" />
      <el-divider content-position="left">
        <el-checkbox
          :disabled="!editable"
          v-model="checkData"
          label="校验响应值"
          size="large"
          @change="onCheckDataChange"
        />
        <span
          v-show="false"
          style="margin-left: 50px"
          class="text-primary text-base font-light"
          >⚠ 已设置此预期响应不校验响应值</span
        >
      </el-divider>
      <!-- 操作提示栏 -->
      <div
        v-if="menuTipBarVisible"
        class="shadow-lg flex flex-col w-full h-full bg-sky-400/90 absolute left-0 bottom-0 z-10 rounded-lg p-2 animate-fade-in animate-once"
      >
        <div class="h-8 text-white font-bold text-lg text-center">
          ⚙ {{ menuTipBarLabel }}
        </div>
        <div
          class="text-white font-light text-lg flex-1 overflow-hidden flex justify-center items-center"
        >
          请勾选您想要批量操作的参数节点，然后点击确定！
        </div>
        <div class="p-1 mt-auto flex justify-end">
          <el-button @click="menuTipBarCancel" plain> 取消</el-button>
          <el-button type="primary" @click="menuTipBarConfirm">
            确定
          </el-button>
        </div>
      </div>
    </div>
    <!-- B. 参数值校验 -->
    <div
      class="flex-1 rounded-md p-1 border-2 border-gray-200 overflow-hidden relative"
      @contextmenu="handleNodeContextMenu($event, null, null)"
    >
      <!-- 参数填写 Tree -->
      <div
        ref="treeContainerRef"
        class="w-full h-full overflow-hidden bg-transparent"
      >
        <el-tree-v2
          class="overflow-hidden rounded-md"
          ref="paramTreeRef"
          style="width: 100%"
          :style="checkData ? '' : 'background-color: #f1f1f1 !important'"
          empty-text="此协议无参数"
          :data="testcaseStore.currentProto?.proto_data"
          :props="treeProps"
          :height="treeHeight"
          :indent="18"
          :item-size="treeNodeHeight"
          :icon="CaretRightIcon"
          :show-checkbox="
            props.protoType === protoGenreEnum.RECV.value && enableTreeCheck
          "
          @node-contextmenu="handleNodeContextMenu"
        >
          <template #default="{ node, data }">
            <div
              class="w-full font-mono items-center pr-2 flex"
              :style="`height: ${treeNodeHeight}px;`"
            >
              <!-- 参数含义 -->
              <el-tooltip
                :content="tooltip(data)"
                raw-content
                effect="light"
                placement="top"
                trigger="hover"
                :hide-after="0"
              >
                <IconifyIconOnline
                  class="text-lg font-bold text-gray-400 mx-1"
                  icon="material-symbols:help-outline"
                />
              </el-tooltip>
              <!-- 参数名: 数组子项显示 item, 其余正常显示  -->
              <span class="param-field" :class="fieldClass(data)">
                {{ data.modifier === "item" ? "item" : data.field }}
              </span>
              <!-- 自定义变量标记 -->
              <el-tooltip
                v-if="isCustomVar(node)"
                content="自定义变量"
                raw-content
                effect="light"
                placement="top"
                trigger="hover"
                :hide-after="0"
              >
                <IconifyIconOnline
                  class="text-2xl font-bold text-orange-400 ml-[2px]"
                  icon="ic:round-star"
                />
              </el-tooltip>
              <!-- 按钮：添加子项 -->
              <el-button
                v-if="
                  (data.modifier === 'repeated' ||
                    data.modifier.includes('map')) &&
                  !data.deleted
                "
                type="primary"
                plain
                class="ml-2"
                size="small"
                title="为数组添加子项"
                round
                :icon="Plus"
                @click.stop="addRepeatedItem(node, data)"
              />
              <!-- 按钮：删除子项 -->
              <el-button
                v-if="data.modifier === 'item' && !data.deleted"
                class="ml-2"
                :disabled="!editable"
                title="移除子项"
                type="danger"
                plain
                :icon="Minus"
                circle
                size="small"
                @click.stop="deleteRepeatedItem(node, data)"
              />
              <div class="ml-auto w-1" />
              <!-- ----------- 左右分隔 -------------------->
              <!-- A. 进行参数校验时：显示操作按钮 -->
              <div v-if="!data.deleted" class="flex">
                <!-- 操作符: 只有recv类型下的无子项参数才可见 -->
                <div
                  class="mr-2"
                  v-if="
                    props.protoType === protoGenreEnum.RECV.value &&
                    !data.children?.length &&
                    data.modifier !== 'repeated' &&
                    isProto3BasicType(data.type)
                  "
                >
                  <el-button
                    style="width: 40px"
                    :disabled="
                      !editable || props.protoType === protoGenreEnum.SEND.value
                    "
                    @click.stop="onOperatorClick(data)"
                  >
                    <span class="text-sm text-medium">{{ data.operator }}</span>
                  </el-button>
                </div>
                <!-- GM 输入助手（仅在GM命令时显示） -->
                <div>
                  <el-button
                    class="mr-1"
                    v-if="gmButtonVisible(data)"
                    :disabled="!editable"
                    type="warning"
                    plain
                    @click="handleShowGmHelperDialog(data)"
                  >
                    GM
                  </el-button>
                </div>
                <!-- 结果值填写: a. 基础类型 -->
                <div
                  v-if="
                    isProto3BasicType(data.type) && data.modifier !== 'repeated'
                  "
                >
                  <!-- A. 引用自定义变量 -->
                  <div v-if="data.refer_name">
                    <el-button-group style="width: 200px">
                      <el-button
                        style="width: 150px"
                        type="warning"
                        :icon="Connection"
                        plain
                        :disabled="!editable"
                        @click.stop="setNodeReference(node)"
                      >
                        <span class="text-sm font-bold mx-2">
                          {{ data.refer_name }}
                        </span>
                      </el-button>
                      <el-button
                        style="width: 50px"
                        type="warning"
                        :icon="CloseBold"
                        plain
                        :disabled="!editable"
                        @click.stop="deleteNodeReference(node)"
                      />
                    </el-button-group>
                  </div>
                  <!-- B. 设置高级表达式 -->
                  <div v-if="data.expr">
                    <el-button-group style="width: 200px">
                      <el-button
                        style="width: 150px"
                        type="success"
                        plain
                        :disabled="!editable"
                        @click.stop="setNodeExpression(node)"
                      >
                        <div
                          style="width: 96px"
                          class="text-sm font-bold mx-2 text-ellipsis overflow-hidden whitespace-nowrap"
                        >
                          {{ data.expr }}
                        </div>
                      </el-button>
                      <el-button
                        style="width: 50px"
                        type="success"
                        :icon="CloseBold"
                        plain
                        :disabled="!editable"
                        @click.stop="deleteNodeExpression(node)"
                      />
                    </el-button-group>
                  </div>
                  <!-- C. 手动填写参数值 -->
                  <div v-if="!data.refer_name && !data.expr">
                    <!-- 根据字段名称生成不同组件(当前只用来特殊处理多多玩-捕鱼) -->
                    <!-- fishId list -->
                    <el-tooltip placement="top">
                      <template #content>
                        显示当前鱼信息列表（<span style="color: yellow"
                          >特殊值：不填写时，后端默认填充 "随机鱼"</span
                        >）
                      </template>
                      <el-button
                        type="warning"
                        plain
                        v-if="data.field === 'fishId' && data.type === 'string'"
                        style="padding: 8px"
                        @click.stop="showFishInfoDialog(data)"
                      >
                        <FishSvg style="width: 24px; height: 24px" />
                        <!-- 调整SVG图标大小 -->
                      </el-button>
                    </el-tooltip>
                    <!-- score list -->
                    <el-tooltip
                      content="显示当前房间可选炮台分数"
                      placement="top"
                    >
                      <el-button
                        type="warning"
                        plain
                        v-if="data.field === 'score' && data.type === 'int32'"
                        style="padding: 5px"
                        @click.stop="showScoreInfoDialog(data)"
                      >
                        <ScoreSvg style="width: 30px; height: 28px" />
                        <!-- 调整SVG图标大小 -->
                      </el-button>
                    </el-tooltip>
                    <!-- 根据字段类型生成不同组件 -->
                    <!-- 数字类型 -->
                    <el-input-number
                      style="width: 200px"
                      :controls="false"
                      v-if="isProto3NumberType(data.type)"
                      :disabled="!editable"
                      v-model="data.value"
                    />
                    <!-- 布尔类型 -->
                    <el-switch
                      style="width: 200px"
                      v-else-if="data.type === 'bool'"
                      :disabled="!editable"
                      v-model="data.value"
                      active-text="true"
                      inactive-text="false"
                      :active-value="true"
                      :inactive-value="false"
                    />
                    <!-- 字符串类型 -->
                    <el-input
                      v-else-if="data.type === 'string'"
                      :disabled="!editable"
                      v-model="data.value"
                      style="width: 200px"
                      placeholder="请输入"
                      clearable
                    >
                      <template #append>
                        <!-- 放大编辑按钮 -->
                        <el-button
                          :icon="FullScreen"
                          @click.stop="showBigInputDialog(data)"
                        />
                      </template>
                    </el-input>
                  </div>
                </div>
                <!-- 结果值填写: b. 非基础类型 -->
                <!-- 枚举类型 -->
                <el-select
                  style="width: 200px"
                  v-if="data?.choices?.length"
                  :disabled="!editable"
                  v-model="data.value"
                  filterable
                  allow-create
                  default-first-option
                  placeholder="请选择"
                >
                  <el-option
                    v-for="choice in data.choices"
                    :key="choice.value"
                    :label="`【${choice.value}】 ${
                      choice.comment || choice.name
                    }`"
                    :value="choice.value"
                  />
                </el-select>
              </div>
              <div
                v-else
                style="width: 200px"
                class="text-center select-none cursor-not-allowed"
              >
                <span class="text-sm font-base text-gray-300 font-sans">
                  不校验此参数
                </span>
              </div>
            </div>
          </template>
        </el-tree-v2>
      </div>
    </div>
    <!-- C. GM Helper -->
    <GmHelper
      ref="gmHelperRef"
      :env="testcaseStore.baseInfo.env"
      @complete="handleGmHelperCompleted"
    />
    <!-- D. BIG INPUT -->
    <BigInput ref="bigInputRef" />
    <!-- E. Tree Contextmenu -->
    <TreeContextMenu ref="treeContextMenuRef" @menu-click="handleMenuClick" />
    <!-- F. Tree Contextmenu -->
    <saveVariableDialog ref="saveVariableDialogRef" />
    <!-- G. FishInfo List Dialog -->
    <FishInfoDialog ref="fishInfoDialogRef" />
    <!-- H. ScoreInfo List Dialog -->
    <ScoreInfoDialog ref="scoreInfoDialogRef" />
  </div>
</template>

<style scoped>
.param-field {
  @apply text-lg font-bold select-none;
}
</style>
