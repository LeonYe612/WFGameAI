<script setup lang="ts">
import { UploadFilled, Refresh } from "@element-plus/icons-vue";
import Save from "@/assets/svg/save.svg?component";
import { useTeamGlobalState } from "../utils/teamStoreStateHook";
import { useTeamConfigs } from "../utils/teamConfigsHook";
import ActiveTeamInfo from "@/views/common/display/activeTeamInfo.vue";
import { perms } from "@/utils/permsCode";
import { hasAuth } from "@/router/utils";
import { ref } from "vue";
import "codemirror/mode/yaml/yaml.js";
import Codemirror from "codemirror-editor-vue3";
import "codemirror/theme/darcula.css";
import "codemirror/addon/display/autorefresh.js";
import "codemirror/addon/fold/foldgutter.css";
import "codemirror/addon/fold/foldcode";
import "codemirror/addon/fold/foldgutter";
import "codemirror/addon/fold/brace-fold";
import "codemirror/addon/fold/comment-fold";
import "codemirror/addon/fold/markdown-fold";
import "codemirror/addon/fold/xml-fold";
import "codemirror/addon/fold/indent-fold";
import type { UploadInstance } from "element-plus";
import { useUpload } from "@/store/modules/oss";
import ConfigTester from "@/views/team/mine/components/configTester.vue";

defineOptions({
  name: "TeamConfigs"
});

const cmOptions = {
  autoRefresh: true, // 重点是这句，为true
  scrollbarStyle: null,
  mode: "text/x-yaml", // 语言模式
  theme: "darcula", // 主题样式
  lineWrapping: false, // 是否自动换行
  // 代码折叠
  gutters: [
    "CodeMirror-lint-markers",
    "CodeMirror-linenumbers",
    "CodeMirror-foldgutter"
  ],
  foldGutter: true // 启用行槽中的代码折叠
};

const {
  testYaml,
  devYaml,
  loading,
  saveLoading,
  uploadLoadings,
  activeEnv,
  uploadOss,
  fetchData,
  handleSaveClick,
  handleTabChange
} = useTeamConfigs();

const { initWatchTeamId } = useTeamGlobalState();
initWatchTeamId(fetchData);

const upload = ref<UploadInstance>();
const { beforeUpload, handleExceed, handleSuccess, handleError } =
  useUpload(upload);
</script>

<template>
  <el-container class="p-2">
    <el-header class="flex items-center justify-center">
      <el-row class="w-5/6 mx-auto">
        <ActiveTeamInfo>
          <div class="float-right" v-if="hasAuth(perms.myteam.manage.writable)">
            <div class="buttons-container flex items-center">
              <ConfigTester :env="activeEnv" class="mr-6" />
              <el-upload
                ref="upload"
                class="upload"
                multiple
                :limit="1"
                :http-request="uploadOss"
                :on-exceed="handleExceed"
                :before-upload="beforeUpload"
                :on-error="handleError"
                :on-success="handleSuccess"
                :show-file-list="false"
                v-loading="uploadLoadings"
              >
                <template #trigger>
                  <el-button
                    type="success"
                    :icon="UploadFilled"
                    size="large"
                    style="width: 120px"
                  >
                    上传
                  </el-button>
                </template>
              </el-upload>
              <el-button
                :icon="Refresh"
                size="large"
                style="width: 120px"
                @click="fetchData"
              >
                刷新
              </el-button>
              <el-button
                :icon="Save"
                size="large"
                type="primary"
                style="width: 120px"
                :loading="saveLoading"
                @click="handleSaveClick"
              >
                保存
              </el-button>
            </div>
          </div>
        </ActiveTeamInfo>
      </el-row>
    </el-header>
    <el-main v-loading="loading">
      <div class="mx-auto w-5/6">
        <el-tabs
          v-model="activeEnv"
          type="border-card"
          @tab-change="handleTabChange"
        >
          <el-tab-pane label="测试环境" name="1">
            <div class="w-full" style="height: calc(100vh - 350px)">
              <Codemirror
                v-model:value="testYaml"
                :options="cmOptions"
                style="font-size: 20px"
                smartIndent
                border
              />
            </div>
          </el-tab-pane>
          <el-tab-pane label="开发环境" name="2">
            <div class="w-full" style="height: calc(100vh - 350px)">
              <Codemirror
                v-model:value="devYaml"
                :options="cmOptions"
                style="font-size: 20px"
                smartIndent
                border
              />
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-main>
  </el-container>
</template>
<style scoped>
.buttons-container {
  display: flex;
  align-items: center;
  gap: 1px; /* 根据需要调整按钮之间的间距 */
}

/* 上传按钮微调 */
.upload {
  transform: translateX(-10%); /* 如有需要，进行微小位移调整 */
}

.CodeMirror {
  font-family: Arial, monospace;
  font-size: 126px !important;
}
</style>
