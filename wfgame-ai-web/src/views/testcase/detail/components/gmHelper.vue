<!-- 此组件用于辅助填写 GM 命令的 param参数 -->
<script lang="ts" setup>
import {
  Refresh,
  CirclePlusFilled,
  DeleteFilled
} from "@element-plus/icons-vue";
import { message } from "@/utils/message";
import { ref, reactive, computed, nextTick } from "vue";
import {
  listGmResourceCategory,
  listGmResourceItem,
  syncGmResource
} from "@/api/testcase";
import { superRequest } from "@/utils/request";
import ComponentPager from "@/components/RePager/index.vue";
import { Search, RefreshLeft } from "@element-plus/icons-vue";
import { envTypeEnum, sortedEnum, getLabel } from "@/utils/enums";
import { ElMessageBox } from "element-plus";
import { useTeamStore } from "@/store/modules/team";
import { gmTypeEnum } from "@/utils/enums";

const props = defineProps({
  env: {
    type: Number,
    default: envTypeEnum.TEST.value
  },
  envDisabled: {
    type: Boolean,
    default: true
  }
});

defineOptions({
  name: "GmHelper"
});

const emit = defineEmits(["complete"]);
const teamStore = useTeamStore();

// GmHelper 组件变量
const title = ref(`🤡 GM 指令助手`);
const dialogVisible = ref(false);
const syncButtonLoading = ref(false);

// =============【资源目录】相关 ==============
const cateLoading = ref(false);
const categoryList = ref([]);
const categorySearch = ref("");
const filterCategoryList = computed(() =>
  categoryList.value.filter(
    data =>
      !categorySearch.value ||
      data.type_name.toLowerCase().includes(categorySearch.value.toLowerCase())
  )
);
const fetchCategory = async () => {
  await superRequest({
    apiFunc: listGmResourceCategory,
    apiParams: { env: props.env },
    onBeforeRequest: () => {
      cateLoading.value = true;
    },
    onSucceed: data => {
      categoryList.value = data;
    },
    onCompleted: () => {
      cateLoading.value = false;
    }
  });
};
const handleCategoryChanged = (val: any) => {
  queryRef.value.id = val ? val?.type_id : -1;
  queryRef.value.page = 1;
  fetchItems();
};

// =============【物品列表】相关 ==============
const query = {
  page: 1,
  size: 20,
  env: props.env,
  id: 0,
  keyword: ""
};
const itemLoading = ref(false);
const queryRef = ref(query);
const itemsList = ref([]);
const itemTotal = ref(0);
const itemTableRef = ref();

const fetchItems = async () => {
  if (queryRef.value.id < 0) {
    itemsList.value = [];
    itemTotal.value = 0;
    itemLoading.value = false;
    return;
  }
  await superRequest({
    apiFunc: listGmResourceItem,
    apiParams: queryRef.value,
    onBeforeRequest: () => {
      itemLoading.value = true;
    },
    onSucceed: data => {
      itemsList.value = data.list || [];
      itemTotal.value = data.total;
    },
    onCompleted: () => {
      itemLoading.value = false;
      itemTableRef.value?.scrollTo({ top: 0 });
    }
  });
};

const handleQuerychanged = (val: any, key: string) => {
  queryRef.value[key] = val;
  fetchItems();
};

// =============【物品栏】相关 ==============
// type CartItem = {
//   id: number;
//   name: string;
//   count: number;
//   children: CartItem[] | null;
// };
const goodsTable = ref();
const cartMap = ref({});
const cartList = reactive([]);
const inCart = computed(() => {
  return item => {
    const { type_id, prop_id } = item;
    return cartMap.value[type_id]?.[prop_id];
  };
});

const goodsTableScrollToBottom = () => {
  nextTick(() => {
    const dom =
      goodsTable.value.$refs.bodyWrapper.getElementsByClassName(
        "el-scrollbar__wrap"
      )[0];
    const { clientHeight, scrollTop } = dom;
    goodsTable.value.setScrollTop(clientHeight + scrollTop + 100);
  });
};

const addToCart = (item: any) => {
  const { type_id, type_name, prop_id, prop_name } = item;
  // 如果暂时没有该类型，则初始化
  if (!cartMap.value[type_id]) {
    cartMap.value[type_id] = {};
    cartList.push({
      id: type_id,
      parent_id: 0,
      name: type_name,
      count: 0,
      children: []
    });
  }
  // 如果物品不存在，则添加物品
  if (!cartMap.value[type_id]?.[prop_id]) {
    cartMap.value[type_id][prop_id] = true;
    const length = cartList.length;
    for (let i = 0; i < length; i++) {
      const item = cartList[i];
      if (item.id == type_id) {
        item.children.push({
          id: prop_id,
          parent_id: type_id,
          name: prop_name,
          count: 0,
          children: null
        });
        break;
      }
    }
  }
  goodsTableScrollToBottom();
};

const removeFromCart = (item: any) => {
  const type_id = item.type_id >= 0 ? item.type_id : item.parent_id;
  const prop_id = item.prop_id >= 0 ? item.prop_id : item.id;
  if (cartMap.value[type_id]?.[prop_id]) {
    const length = cartList.length;
    for (let i = 0; i < length; i++) {
      const item = cartList[i];
      if (item.id == type_id) {
        if (item.children.length === 1) {
          // a. 类型下删除时只有一个元素
          cartList.splice(i, 1);
          delete cartMap.value[type_id];
          return;
        } else {
          // b. 类型下删除时有多个元素
          for (let j = 0; j < item.children.length; j++) {
            if (item.children[j].id == prop_id) {
              cartList[i].children.splice(j, 1);
              delete cartMap.value[type_id][prop_id];
              return;
            }
          }
        }
      }
    }
  }
};

const clearCart = () => {
  cartMap.value = {};
  cartList.splice(0, cartList.length);
};
// ==========================================
// onMounted(() => {
//   fetchCategory();
// });

const show = () => {
  dialogVisible.value = true;
  queryRef.value.env = props.env;
  if (!categoryList.value?.length) {
    fetchCategory();
  }
};

const cancel = () => {
  dialogVisible.value = false;
};

// 卡牌项目：type_id:prop_id:count#type_id:prop_id:count
const kapaiFormatter = () => {
  const params = [];
  for (let i = 0; i < cartList.length; i++) {
    const item = cartList[i];
    if (item.children.length > 0) {
      for (let j = 0; j < item.children.length; j++) {
        const child = item.children[j];
        if (child.count) {
          params.push(`${item.id}:${child.id}:${child.count}`);
        }
      }
    }
  }
  return params.join("#");
};

// 纸老虎项目：prop_id count (空格分隔，不支持多个物品操作)
const zilaohuFormatter = () => {
  const countLimitError = new Error(
    "纸老虎GM不支持批量操作, 请确保物品栏只有一个物品"
  );
  if (cartList.length > 1) {
    throw countLimitError;
  }
  const cartItem = cartList[0];
  if (cartItem.children.length > 1) {
    throw countLimitError;
  }
  const child = cartItem.children[0];
  return `${child.id} ${child.count}`;
};

const getFormatter = () => {
  const formatters = {
    [gmTypeEnum.KAPAI.value]: kapaiFormatter,
    [gmTypeEnum.ZHILAOHU.value]: zilaohuFormatter
  };
  const gmType = teamStore.GET_TEAM_GM_TYPE();
  if (formatters[gmType]) {
    return formatters[gmType];
  } else {
    throw new Error("无法确定团队对应的 [GM Formatter]，请联系管理员确认");
  }
};

const confirm = () => {
  // 通用校验
  if (cartList.length === 0) {
    message("未编辑任何物品资源", { type: "error" });
    return;
  }
  /**
   * 2024-11-18 更新
   * 支持不同团队下，gm 辅助填写的格式差异
   * - 卡牌项目：type_id:prop_id:count#type_id:prop_id:count
   * - 纸老虎项目：prop_id count (空格分隔，不支持多个物品操作)
   */
  try {
    const formatter = getFormatter();
    const paramsStr = formatter();
    dialogVisible.value = false;
    emit("complete", paramsStr);
  } catch (error) {
    message(error.message, { type: "error" });
  }
};

const handleResourceSync = () => {
  // 二次弹窗确认提示：plan一旦创建后，不能编辑只能删除或者禁用！
  const envLabel = getLabel(envTypeEnum, props.env);
  ElMessageBox.confirm(
    `此操作将根据团队配置中【${envLabel}】预留的相关GM配置, 同步所有物品资源数据，确认继续？`,
    "资源数据同步",
    {
      confirmButtonText: "继续",
      cancelButtonText: "取消",
      type: "warning"
    }
  )
    .then(() => {
      // 发送新建请求
      superRequest({
        apiFunc: syncGmResource,
        apiParams: {
          env: props.env
        },
        enableSucceedMsg: true,
        succeedMsgContent: "资源同步成功！",
        onBeforeRequest: () => {
          syncButtonLoading.value = true;
        },
        onSucceed: () => {
          // 同步成功后，自动刷新数据
          setTimeout(fetchCategory, 2000);
        },
        onCompleted: () => {
          syncButtonLoading.value = false;
        }
      });
    })
    .catch(() => {});
};

defineExpose({ show });
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    width="80vw"
    :draggable="true"
    align-center
  >
    <!-- 顶部信息 -->
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
        v-model="query.env"
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
      <div class="ml-auto">
        <el-button v-show="false" :icon="RefreshLeft" size="large" plain>
          刷 新
        </el-button>
        <el-button
          @click="handleResourceSync"
          :loading="syncButtonLoading"
          size="large"
          type="primary"
          plain
          >同步资源</el-button
        >
      </div>
    </div>

    <!-- 资源类型 | 物品列表 | 自动生成文本 -->
    <div
      class="flex bg-gray-100 m-2 rounded-lg overflow-hidden"
      style="height: 60vh"
    >
      <!-- A. 资源类型 -->
      <div class="w-1/5 p-2">
        <div
          class="rounded-md bg-white border-1 h-full overflow-hidden shadow-md"
        >
          <!-- 搜索框 -->
          <div class="w-full my-1 px-1">
            <el-input
              v-model="categorySearch"
              size="large"
              placeholder="搜索资源类型"
              :prefix-icon="Search"
              clearable
            />
          </div>
          <el-table
            v-loading="cateLoading"
            height="calc(100% - 52px)"
            :data="filterCategoryList"
            highlight-current-row
            empty-text="未查询到物品类目, 请同步后查看"
            @current-change="handleCategoryChanged"
          >
            <el-table-column label="ID" prop="type_id" width="50px" />
            <el-table-column
              label="资源类型"
              prop="type_name"
              show-overflow-tooltip
            >
              <template #header>
                <div class="flex items-center justify-between">
                  <span>资源类型</span>
                  <el-button-group class="ml-2">
                    <el-button
                      circle
                      title="刷新数据"
                      type="default"
                      plain
                      size="small"
                      :icon="Refresh"
                      @click="fetchCategory"
                    />
                  </el-button-group>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- B. 物品列表 -->
      <div class="w-2/5 p-2">
        <div
          class="rounded-md bg-white border-1 h-full overflow-hidden shadow-md flex flex-col"
        >
          <!-- 搜索框 -->
          <div class="w-full my-1 px-1">
            <el-input
              v-model="queryRef.keyword"
              size="large"
              placeholder="搜索物品名称"
              :prefix-icon="Search"
              @change="handleQuerychanged($event, 'keyword')"
              clearable
            />
          </div>
          <div class="flex-1 overflow-auto">
            <el-table
              height="100%"
              ref="itemTableRef"
              v-loading="itemLoading"
              :data="itemsList"
              empty-text="请单击选择左侧资源类型后查看物品列表"
            >
              <el-table-column label="ID" prop="prop_id" width="150px" />
              <el-table-column
                label="物品名称"
                prop="prop_name"
                show-overflow-tooltip
              />
              <el-table-column label="操作">
                <template #header>
                  <div class="flex items-center justify-between">
                    <span />
                    <el-button-group class="ml-2">
                      <el-button
                        circle
                        title="刷新数据"
                        type="default"
                        plain
                        size="small"
                        :icon="Refresh"
                        @click="fetchItems"
                      />
                    </el-button-group>
                  </div>
                </template>
                <template #default="{ row }">
                  <el-button
                    v-if="inCart(row)"
                    title="移除"
                    type="danger"
                    plain
                    round
                    :icon="DeleteFilled"
                    @click="removeFromCart(row)"
                    >移除</el-button
                  >
                  <el-button
                    v-else
                    title="添加"
                    type="success"
                    plain
                    round
                    :icon="CirclePlusFilled"
                    @click="addToCart(row)"
                    >添加</el-button
                  >
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 分页组件 -->
          <ComponentPager
            layout="total, sizes, prev, next, jumper"
            :query-form="query"
            :total="itemTotal"
            @fetch-data="fetchItems"
          />
        </div>
      </div>

      <!-- C. 物品栏 -->
      <div class="w-2/5 p-2">
        <div
          class="rounded-md bg-white border-1 h-full overflow-hidden shadow-md"
        >
          <!-- 标题栏 -->
          <div class="w-full my-1 px-1">
            <div
              class="rounded-md bg-blue-50 h-9 flex justify-center items-center"
            >
              <span class="text-lg font-bold text-primary">物品栏</span>
            </div>
          </div>
          <el-table
            ref="goodsTable"
            height="90%"
            :data="cartList"
            empty-text="尚未添加物品"
            default-expand-all
            row-key="id"
            fit
          >
            <el-table-column label="物品">
              <template #default="{ row }">
                <div class="inline-block">
                  <!-- 类型行 -->
                  <div v-if="row.children">
                    <span class="text-base font-bold text-primary">
                      {{ row.name }}
                    </span>
                  </div>
                  <div v-else>
                    <el-tag type="info">
                      {{ row.id }}
                    </el-tag>
                    <span class="ml-2 text-base text-primary">
                      {{ row.name }}
                    </span>
                  </div>
                </div>
                <!-- 物品行 -->
              </template>
            </el-table-column>
            <el-table-column label="数量" width="180px">
              <template #default="{ row }">
                <el-input-number
                  style="width: 96%"
                  :controls="true"
                  v-if="!row.children"
                  v-model="row.count"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60px">
              <template #header>
                <el-button
                  class="mr-2"
                  title="清空所有"
                  type="danger"
                  plain
                  size="small"
                  @click="clearCart"
                  >清空
                </el-button>
              </template>
              <template #default="{ row }">
                <el-button
                  v-if="!row.children"
                  title="移除"
                  type="danger"
                  plain
                  circle
                  :icon="DeleteFilled"
                  @click="removeFromCart(row)"
                />
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>
    <template #footer>
      <!-- <el-button class="float-left" type="success" size="large" plain>
        GM 请求快捷导入
      </el-button> -->
      <el-button @click="cancel" size="large">取 消</el-button>
      <el-button type="primary" @click="confirm" size="large"> 确定 </el-button>
    </template>
  </el-dialog>
</template>
