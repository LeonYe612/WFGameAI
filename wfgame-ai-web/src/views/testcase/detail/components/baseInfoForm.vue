<script setup lang="ts">
import { Setting, UploadFilled, EditPen } from "@element-plus/icons-vue";
import { ref, onActivated, defineProps } from "vue";
import { listCatalog, listServer } from "@/api/testcase";
import { superRequest } from "@/utils/request";
import { FormInstance } from "element-plus";
import { formRules } from "../utils/rules";
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { useCaseCommonHook } from "@/views/testcase/list/utils/caseCommonHook";
import { envEnum, caseTypeEnum, sortedEnum } from "@/utils/enums";

const store = useTestcaseStoreHook();
const { typeIconRender } = useCaseCommonHook();

defineOptions({
  name: "TestcaseBaseInfoForm"
});

defineProps({
  editable: {
    type: Boolean,
    default: false
  }
});

const baseInfo = store.baseInfo;
const formRef = ref<FormInstance>();
// 查询用例所属目录选项
const treeData = ref<any>();
const fetchTreeSelectOptions = async () => {
  await superRequest({
    apiFunc: listCatalog,
    onSucceed: data => {
      treeData.value = data;
    }
  });
};

// 查询服务器列表选项
const serverOptions = ref<any>();
const fetchServerOptions = async (envParam: number) => {
  await superRequest({
    apiFunc: listServer,
    apiParams: { env: envParam },
    onSucceed: data => {
      serverOptions.value = data;
    }
  });
};

const onEnvChanged = value => {
  baseInfo.server_no = null;
  fetchServerOptions(value);
};

onActivated(() => {
  initData();
});

const initData = () => {
  fetchTreeSelectOptions();
  fetchServerOptions(baseInfo.env);
};

defineExpose({
  formRef,
  fetchTreeSelectOptions,
  initData
});
</script>

<template>
  <el-container
    v-loading="store.shareState.baseInfoFormLoading"
    class="h-full rounded-md border-gray-200 border"
  >
    <el-header class="pt-2">
      <div
        class="mt-2 flex items-center p-8 bg-slate-100 dark:bg-transparent rounded-lg w-full h-12"
      >
        <div class="flex items-center w-full">
          <el-icon size="22">
            <Setting />
          </el-icon>
          <span class="text-lg font-bold ml-2 text-gray-600 dark:text-white">
            基础信息 & 环境配置
          </span>
          <!-- 上方保存按钮 -->
          <!-- <div class="ml-auto">
            <el-button
              v-if="!store.baseInfo.id"
              :loading="store.shareState.baseInfoSaveLoading"
              :icon="UploadFilled"
              size="large"
              type="primary"
              @click="store.saveBaseInfo(formRef)"
            >
              保存
            </el-button>
          </div> -->
        </div>
      </div>
    </el-header>
    <el-main>
      <el-scrollbar class="h-full">
        <el-form
          :model="baseInfo"
          size="large"
          label-width="100px"
          ref="formRef"
          :rules="formRules"
          :disabled="!editable"
        >
          <!-- 基础信息 -->
          <el-divider style="margin-bottom: 36px">
            <span class="text-gray-400">基础信息</span>
          </el-divider>
          <!-- 1. 用例名称 -->
          <el-form-item prop="name" class="pr-16">
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="为用例起一个简洁明了的名称"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>用例名称</label>
              </div>
            </template>
            <el-input
              v-model="baseInfo.name"
              placeholder="请填写用例名称"
              clearable
            />
          </el-form-item>
          <!-- 2. 用例目录 -->
          <el-form-item prop="catalog_id" class="pr-16">
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="将用例归属到某个目录下"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>所属目录</label>
              </div>
            </template>
            <div class="w-full flex items-center">
              <el-tree-select
                class="flex-1"
                v-model="baseInfo.catalog_id"
                check-strictly
                clearable
                :data="treeData"
                default-expand-all
                highlight-current
                :props="{
                  children: 'children',
                  label: 'name',
                  value: 'id'
                }"
                :render-after-expand="false"
              />
              <el-button
                class="ml-1"
                type="primary"
                plain
                :icon="EditPen"
                @click.stop="store.components.showCatalogDialog = true"
              />
            </div>
          </el-form-item>
          <!-- 3. 用例类型 -->
          <el-form-item prop="type" class="pr-16">
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="请选择用例所属的类型"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>用例类型</label>
              </div>
            </template>
            <el-radio-group v-model="baseInfo.type">
              <div
                class="w-full"
                v-for="item in sortedEnum(caseTypeEnum, [caseTypeEnum.ALL])"
                :key="item.value"
              >
                <el-radio size="large" :label="item.value">
                  <div class="flex items-center">
                    <el-icon size="26" class="mr-2">
                      <component :is="typeIconRender(item.value)" />
                    </el-icon>
                    <span class="font-medium"> {{ item.label }} </span>
                  </div>
                </el-radio>
              </div>
            </el-radio-group>
          </el-form-item>
          <!-- 用例类型(下拉列表形式，暂时不用了) -->
          <el-form-item v-if="false" prop="type" class="pr-16">
            <template #label>
              <div class="flex justify-center items-center">
                <el-tooltip
                  content="请选择用例所属的类型"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>用例类型</label>
              </div>
            </template>
            <el-select
              class="w-full"
              v-model="baseInfo.type"
              filterable
              placeholder="请选择类型"
              clearable
            >
              <el-option
                v-for="item in sortedEnum(caseTypeEnum, [caseTypeEnum.ALL])"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
          <!-- 运行配置(无需显示了) -->
          <div v-if="false">
            <el-divider style="margin-bottom: 36px">
              <span class="text-gray-400">运行配置</span>
            </el-divider>
            <el-form-item prop="env" class="pr-16">
              <template #label>
                <div class="flex justify-center items-center">
                  <el-tooltip
                    content="请选择此用例的运行环境"
                    effect="dark"
                    placement="top"
                  >
                    <IconifyIconOnline icon="material-symbols:help-outline" />
                  </el-tooltip>
                  <label>环境</label>
                </div>
              </template>
              <el-radio-group v-model="baseInfo.env" @change="onEnvChanged">
                <el-radio :label="envEnum.TEST" border>
                  <div class="flex items-center">
                    <el-tag type="success" size="small">测试</el-tag>
                  </div>
                </el-radio>
                <el-radio :label="envEnum.DEV" border>
                  <div class="flex items-center">
                    <el-tag type="warning" size="small">开发</el-tag>
                  </div>
                </el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item prop="server_no" class="pr-16">
              <template #label>
                <div class="flex justify-center items-center">
                  <el-tooltip
                    content="请选择在哪台服务器上执行测试用例"
                    effect="dark"
                    placement="top"
                  >
                    <IconifyIconOnline icon="material-symbols:help-outline" />
                  </el-tooltip>
                  <label>服务器</label>
                </div>
              </template>
              <el-select
                class="w-full"
                v-model="baseInfo.server_no"
                filterable
                placeholder="请选择服务器"
                clearable
              >
                <el-option
                  v-for="item in serverOptions"
                  :key="item.server_no"
                  :label="`${item.server_name}[${item.ws_url}]`"
                  :value="item.server_no"
                />
              </el-select>
            </el-form-item>
            <el-form-item prop="account" class="pr-16">
              <template #label>
                <div class="flex justify-center items-center">
                  <el-tooltip
                    content="请填写调试用例所使用的游戏账号"
                    effect="dark"
                    placement="top"
                  >
                    <IconifyIconOnline icon="material-symbols:help-outline" />
                  </el-tooltip>
                  <label>调试账号</label>
                </div>
              </template>
              <el-input
                v-model="baseInfo.account"
                placeholder="请填写游戏账号"
                clearable
              />
            </el-form-item>
          </div>
        </el-form>
      </el-scrollbar>
    </el-main>
    <el-footer v-if="editable">
      <div
        class="flex justify-center items-center p-8 rounded-lg w-full h-12 mb-3"
      >
        <el-button
          :loading="store.shareState.baseInfoSaveLoading"
          :icon="UploadFilled"
          size="large"
          type="primary"
          style="width: 260px"
          @click="store.saveBaseInfo(formRef)"
        >
          保存
        </el-button>
      </div>
    </el-footer>
  </el-container>
</template>
