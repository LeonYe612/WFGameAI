<script setup lang="ts">
import type { ReplayConfig, ReplayRequest, ScriptInfo } from "@/api/scripts";
import { replayScripts } from "@/api/scripts";
import { message } from "@/utils/message";
import { superRequest } from "@/utils/request";
import { Delete, Plus, VideoPlay } from "@element-plus/icons-vue";
import { computed, ref } from "vue";
import { useRouter } from "vue-router";

defineOptions({
  name: "ScriptReplayDialog"
});

defineProps<{
  scripts: ScriptInfo[];
}>();

const dialogVisible = ref(false);
const loading = ref(false);
const selectedScript = ref<ScriptInfo | null>(null);
const showScreens = ref(true);
const scriptConfigs = ref<ReplayConfig[]>([]);
const router = useRouter();

const showDialog = (script?: ScriptInfo) => {
  selectedScript.value = script || null;

  // 初始化脚本配置
  if (script) {
    scriptConfigs.value = [
      {
        script_filename: script.filename,
        delay: 0,
        loop: 1
      }
    ];
  } else {
    scriptConfigs.value = [
      {
        script_filename: "",
        delay: 0,
        loop: 1
      }
    ];
  }

  dialogVisible.value = true;
};

const addScriptConfig = () => {
  scriptConfigs.value.push({
    script_filename: "",
    delay: 0,
    loop: 1
  });
};

const removeScriptConfig = (index: number) => {
  if (scriptConfigs.value.length > 1) {
    scriptConfigs.value.splice(index, 1);
  }
};

const commandPreview = computed(() => {
  const validConfigs = scriptConfigs.value.filter(
    config => config.script_filename
  );
  if (validConfigs.length === 0) return "请先选择要回放的脚本";

  const scripts = validConfigs
    .map(config => {
      let scriptName = config.script_filename;
      if (config.delay && config.delay > 0) {
        scriptName += ` (延迟: ${config.delay}ms)`;
      }
      if (config.loop && config.loop > 1) {
        scriptName += ` (循环: ${config.loop}次)`;
      }
      return scriptName;
    })
    .join(", ");

  return `回放脚本: ${scripts}${showScreens.value ? " --show-screens" : ""}`;
});

const startReplay = async () => {
  // 验证配置
  const validConfigs = scriptConfigs.value.filter(
    config => config.script_filename
  );

  if (validConfigs.length === 0) {
    message("请至少选择一个脚本进行回放", { type: "warning" });
    return;
  }

  // 构建回放请求
  const replayData: ReplayRequest = {
    scripts: validConfigs,
    show_screens: showScreens.value
  };

  await superRequest({
    apiFunc: replayScripts,
    apiParams: replayData,
    enableSucceedMsg: true,
    succeedMsgContent: "脚本回放已开始执行！",
    onBeforeRequest: () => {
      loading.value = true;
    },
    onSucceed: (data: any) => {
      closeDialog();
      // 新开窗口跳转到replay页面，传递task_id和device_ids
      const { task_id, device_ids } = data || {};
      if (task_id && Array.isArray(device_ids)) {
        const url = router.resolve({
          name: "AI-REPLAY-ROOM", // 路由name需与replay页面一致
          query: {
            task_id,
            device_ids: device_ids.join(",") //todo改成接口查询，而不是url传递
          }
        }).href;
        window.open(url, "_blank");
      } else {
        message("回放房间参数缺失", { type: "error" });
      }
    },
    onFailed: () => {
      message("脚本回放启动失败", { type: "error" });
    },
    onCompleted: () => {
      loading.value = false;
    }
  });
};

const closeDialog = () => {
  dialogVisible.value = false;
  selectedScript.value = null;
  scriptConfigs.value = [];
  showScreens.value = true;
};

defineExpose({
  showDialog
});
</script>

<template>
  <el-dialog v-model="dialogVisible" title="脚本回放" width="800px" :draggable="true" @close="closeDialog">
    <div v-loading="loading" class="script-replay-content">
      <div class="space-y-4">
        <!-- 回放配置 -->
        <el-card shadow="never" class="border">
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center">
                <el-icon class="mr-2">
                  <VideoPlay />
                </el-icon>
                <span class="font-medium">回放配置</span>
              </div>
              <el-button size="small" type="primary" :icon="Plus" @click="addScriptConfig" :disabled="loading">
                添加脚本
              </el-button>
            </div>
          </template>

          <!-- 脚本配置列表 -->
          <div class="space-y-4">
            <div v-for="(config, index) in scriptConfigs" :key="index" class="script-config p-4 bg-gray-50 rounded-lg">
              <div class="flex items-center justify-between mb-3">
                <span class="font-medium text-gray-700">脚本 {{ index + 1 }}</span>
                <el-button v-if="scriptConfigs.length > 1" size="small" type="danger" :icon="Delete"
                           @click="removeScriptConfig(index)" :disabled="loading">
                  移除
                </el-button>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    选择脚本 *
                  </label>
                  <el-select v-model="config.script_filename" placeholder="请选择脚本" style="width: 100%" filterable
                             :disabled="loading">
                    <el-option v-for="script in scripts" :key="script.filename" :label="script.filename"
                               :value="script.filename">
                      <div class="flex justify-between items-center">
                        <span>{{ script.filename }}</span>
                        <el-tag v-if="script.category" type="info" size="small">
                          {{ script.category }}
                        </el-tag>
                      </div>
                    </el-option>
                  </el-select>
                </div>

                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    延迟时间 (毫秒)
                  </label>
                  <el-input-number v-model="config.delay" :min="0" :max="10000" style="width: 100%"
                                   :disabled="loading" />
                </div>

                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    循环次数
                  </label>
                  <el-input-number v-model="config.loop" :min="1" :max="100" style="width: 100%" :disabled="loading" />
                </div>
              </div>
            </div>
          </div>

          <!-- 全局设置 -->
          <div class="mt-6 p-4 bg-blue-50 rounded-lg">
            <h4 class="text-sm font-medium text-gray-700 mb-3">全局设置</h4>
            <div class="flex items-center space-x-4">
              <el-checkbox v-model="showScreens" :disabled="loading">
                显示屏幕截图
              </el-checkbox>
            </div>
          </div>
        </el-card>

        <!-- 命令预览 -->
        <el-card shadow="never" class="border">
          <template #header>
            <span class="font-medium">命令预览</span>
          </template>
          <div class="bg-gray-100 p-3 rounded-lg font-mono text-sm">
            {{ commandPreview }}
          </div>
        </el-card>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end space-x-2">
        <el-button @click="closeDialog" :disabled="loading"> 取消 </el-button>
        <el-button type="primary" :icon="VideoPlay" :loading="loading" @click="startReplay">
          {{ loading ? "启动中..." : "开始回放" }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.script-replay-content {
  min-height: 300px;
}

.script-config {
  border: 1px solid #e5e7eb;
  transition: all 0.3s ease;
}

.script-config:hover {
  border-color: #d1d5db;
  background-color: #f9fafb;
}
</style>
