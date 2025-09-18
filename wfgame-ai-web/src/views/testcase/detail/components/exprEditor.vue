<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { listFuncs, evalExpr, extractExprVars } from "@/api/testcase";
import { superRequest } from "@/utils/request";
import { CaretRight, Star } from "@element-plus/icons-vue";
import { message } from "@/utils/message";

const testcaseStore = useTestcaseStoreHook();
const dialogTitle = ref("⚡  设置自定义表达式");
const dialogVisible = ref(false);

// 打开 Dialog 传入 protoDataItem 的指针，可以让大窗口中的值改变后 同步到 protoDataItem
let p: any;
const expression = ref("");

const show = (props: { protoDataItem: any; protoInfo: any }) => {
  p = props.protoDataItem;
  expression.value = p.expr;
  evalResult.value = {
    error: null,
    value: ""
  };
  dialogVisible.value = true;
};

const clearP = (done: () => void) => {
  p = null;
  done();
};

const confirm = () => {
  // step1. 记录表达式至 protoInfo.expressions 中
  if (!testcaseStore.currentProto?.expressions) {
    testcaseStore.currentProto.expressions = {};
  }

  const locationStr = testcaseStore.findDescriptionPathString(
    testcaseStore.currentProto.proto_data,
    p.key,
    ""
  );

  testcaseStore.currentProto.expressions[locationStr] = "";

  // step2. 需要同步修改 protoDataItem 的 expr 属性，用于前端展示
  p.expr = expression.value;
  dialogVisible.value = false;
  testcaseStore.saveStep();
};

const cancel = () => {
  dialogVisible.value = false;
};

// 查询变量列表
const tableData = ref([]);
const tableLoading = ref(false);
const fetchTableData = () => {
  superRequest({
    apiFunc: listFuncs,
    apiParams: {},
    enableSucceedMsg: false,
    onBeforeRequest: () => {
      tableLoading.value = true;
    },
    onSucceed: data => {
      tableData.value = data || [];
    },
    onCompleted: () => {
      tableLoading.value = false;
    }
  });
};

const params = ref("");
const paramsInputVisible = ref(false);
const paramsExample = ref(`模拟变量填写示例：
{
  "var1": 1,
  "var2": "value2"
}`);

const evalResult = ref({
  error: null,
  value: ""
});
const evalLoading = ref(false);
// 执行表达式
const handleEvalExpr = () => {
  if (expression.value.trim() === "") {
    message("请填写表达式！", { type: "warning" });
    return;
  }
  superRequest({
    apiFunc: evalExpr,
    apiParams: {
      expression: expression.value,
      params: paramsInputVisible.value ? params.value : ""
    },
    enableSucceedMsg: false,
    onBeforeRequest: () => {
      evalLoading.value = true;
    },
    onSucceed: data => {
      evalResult.value = data;
    },
    onCompleted: () => {
      evalLoading.value = false;
    }
  });
};

// 自动解析变量并填充
const handleExtractExprVars = () => {
  superRequest({
    apiFunc: extractExprVars,
    apiParams: {
      expression: expression.value
    },
    enableFailedMsg: true,
    enableSucceedMsg: false,
    onSucceed: data => {
      params.value = data;
    }
  });
};

// 使用函数名填充表达式
const handleUseFunc = (row: any) => {
  expression.value = row.example || `${row.name}()`;
  handleEvalExpr();
};

onMounted(() => {
  fetchTableData();
});

defineExpose({ show });
</script>

<template>
  <el-dialog
    :title="dialogTitle"
    v-model="dialogVisible"
    width="50vw"
    :draggable="true"
    align-center
    :before-close="clearP"
  >
    <div class="w-full overflow-auto">
      <!-- 表达式输入框 -->
      <div class="m-2 bg-green-[#dafff3] rounded-md flex">
        <!-- 表达式 -->
        <div class="flex-1">
          <el-input
            class="expression text-base font-medium"
            v-model="expression"
            style="width: 100%; height: 100%"
            :autosize="{ minRows: 5, maxRows: 10 }"
            type="textarea"
            placeholder="请在此输入表达式（回车快速执行）"
            @input="
              evalResult.value = '';
              evalResult.error = null;
            "
            @keydown.enter.prevent="handleEvalExpr"
          />
        </div>
        <!-- 模拟变量 -->
        <div class="w-1/3" v-if="paramsInputVisible">
          <el-input
            class="parameters text-base font-medium ml-2"
            v-model="params"
            style="width: 100%; height: 100%"
            :autosize="{ minRows: 5, maxRows: 10 }"
            type="textarea"
            :placeholder="paramsExample"
          />
        </div>
      </div>
      <!-- 显示参数填写 & 执行按钮 -->
      <div class="m-2 flex items-center justify-between">
        <div>
          <el-button
            style="width: 180px"
            :icon="CaretRight"
            type="success"
            @click="handleEvalExpr"
            plain
            >执 行</el-button
          >
        </div>
        <div class="flex justify-center items-center">
          <el-checkbox
            v-model="paramsInputVisible"
            label="使用模拟变量值(JSON格式)"
            size="large"
          />
          <el-button
            v-if="paramsInputVisible"
            class="ml-2"
            :icon="Star"
            type="warning"
            @click="handleExtractExprVars"
            size="small"
            plain
            >智能解析变量</el-button
          >
        </div>
      </div>
      <!-- 表达式执行结果 -->
      <div
        class="m-2 rounded-md overflow-hidden h-auto"
        v-loading="evalLoading"
      >
        <p
          class="text-lg font-medium p-3"
          :class="{
            'bg-gray-200': !evalResult.value && !evalResult.error,
            'bg-green-200': !evalResult.error,
            'bg-red-200': evalResult.error
          }"
        >
          <span
            v-if="!evalResult.value && !evalResult.error"
            class="text-base font-light text-gray-400"
          >
            💡
            此处为表达式执行结果展示区域，请在上方输入表达式后回车或点击执行按钮
          </span>
          <span v-else-if="!evalResult.error" class="text-green-600">
            {{ evalResult.value }}
          </span>
          <span v-else class="text-red-600">❌ {{ evalResult.error }}</span>
        </p>
      </div>
      <el-divider />
      <!-- 支持函数列表 -->
      <div class="h-[30vh]">
        <el-table height="100%" :data="tableData">
          <el-table-column prop="name" label="函数名" />
          <el-table-column prop="desc" label="描述" />
          <el-table-column prop="example" label="示例" />
          <el-table-column prop="params" label="应用" width="100">
            <template #default="scope">
              <el-button
                size="small"
                type="success"
                plain
                @click="handleUseFunc(scope.row)"
              >
                应用
              </el-button>
            </template></el-table-column
          >
        </el-table>
      </div>
    </div>
    <template #footer>
      <el-button @click="cancel" size="large">取 消</el-button>
      <el-button type="primary" @click="confirm" size="large"> 确定 </el-button>
    </template>
  </el-dialog>
</template>
<style scoped>
:deep() .expression .el-textarea__inner {
  font-size: 20px;
  font-weight: 600;
  color: #589cfd;
  height: 100%;
  /* box-shadow: none;
  background-color: #dafff3; */
}

:deep() .parameters .el-textarea__inner {
  font-size: 20px;
  font-weight: 500;
  color: #ff7300;
  height: 100%;
}
</style>
