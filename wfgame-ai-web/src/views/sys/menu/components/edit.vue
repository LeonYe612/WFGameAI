<script lang="ts" setup>
import { ref } from "vue";
import { FormInstance } from "element-plus";
import { listMenu, editMenu } from "@/api/system";
import { clone } from "@pureadmin/utils";
import { formRules } from "../utils/rules";
import { ReEdit } from "@/components/ReEdit";
import { superRequest } from "@/utils/request";

defineOptions({
  name: "SysMenuManagementEdit"
});

const genreOptions = [
  {
    desc: "菜单",
    value: 1,
    nameProp: "唯一标识",
    nameTip:
      "首字母大写, 一定要与 vue 页面文件 defineOptions 的 name 对应起来, 示例: SysUserManagement",
    pathProp: "菜单路由",
    pathTip: "定义前端路由地址(必须以/开头), 示例：/sys/users/index"
  },
  {
    desc: "操作",
    value: 2,
    nameProp: "唯一标识",
    nameTip: "操作权限(按钮等)的唯一标识, 请以Act开头命名, 如: ActMenuEdit",
    pathProp: "操作路由",
    pathTip: "标识此操作权限所在位置, 示例：/sys/menus/index/ActMenuEdit"
  },
  {
    desc: "外链",
    value: 3,
    nameProp: "外链地址",
    nameTip:
      "外链地址(请以http:// | https:// 开头, 非iframe模式), 示例: https://www.baidu.com",
    pathProp: "外链路由",
    pathTip: "对应前端路由(必须以 / 开头) 不同的外链path不要重复"
  },
  {
    desc: "接口",
    value: 4,
    nameProp: "唯一标识",
    nameTip: "后端接口访问权限的唯一标识, 请以Api开头命名, 如: ApiMenuList",
    pathProp: "接口地址",
    pathTip: "对应后端接口api地址, 示例：/sys/menus/list"
  }
];

const emit = defineEmits(["fetch-data"]);
const ruleFormRef = ref<FormInstance>();
const defaultFormData = ref({
  parent_id: 0,
  genre: 1,
  path: "",
  queue: 0,
  meta: {
    title: "",
    showLink: true,
    keepAlive: true,
    showParent: true
  }
});

const formVisible = ref(false);
const formData = ref(clone(defaultFormData, true));
const title = ref("");
const isAdd = ref(false);

const { showEdit, closeDialog, closeDialogSimple } = ReEdit({
  defaultFormData: defaultFormData,
  formData: formData,
  formVisible: formVisible,
  isAdd: isAdd,
  ruleFormRef: ruleFormRef,
  title: title,
  titleExt: "权限",
  doneFn: () => {
    emit("fetch-data");
  }
});

const treeData = ref<any>();

const submitForm = async (formEl: FormInstance | undefined) => {
  if (!formEl) return;
  await formEl.validate(async valid => {
    if (valid) {
      await superRequest({
        apiFunc: editMenu,
        apiParams: formData.value,
        onSucceed: () => {
          closeDialog();
        }
      });
    }
  });
};

const showEditWithParent = (pid: number) => {
  if (pid >= 0) {
    showEdit({ parent_id: pid });
  }
};

const fetchData = async () => {
  await superRequest({
    apiFunc: listMenu,
    onSucceed: data => {
      treeData.value = [
        {
          id: 0,
          parent_id: 0,
          meta: {
            title: "顶级"
          },
          children: data
        }
      ];
    }
  });
};

const showLable = (data: any) => {
  return data.meta?.title;
};

defineExpose({
  showEdit,
  showEditWithParent,
  fetchData
});
</script>

<template>
  <el-dialog
    v-model="formVisible"
    :title="title"
    width="1000px"
    :before-close="closeDialogSimple"
    :draggable="true"
  >
    <el-form
      ref="ruleFormRef"
      :rules="formRules"
      label-width="100px"
      :model="formData"
      size="large"
      status-icon
    >
      <el-row>
        <el-col :span="10">
          <el-form-item label="上级菜单">
            <el-tree-select
              v-model="formData.parent_id"
              check-strictly
              clearable
              :data="treeData"
              default-expand-all
              :props="{
                children: 'children',
                label: showLable,
                value: 'id'
              }"
              :render-after-expand="false"
              style="width: 255px"
            />
          </el-form-item>
        </el-col>
        <el-col :span="14">
          <el-form-item label="权限类型" prop="genre">
            <el-radio-group v-model="formData.genre">
              <el-radio
                v-for="item in genreOptions"
                :key="item.value"
                :label="item.value"
                border
                >{{ item.desc }}</el-radio
              >
            </el-radio-group>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row>
        <el-col :span="10">
          <el-form-item label="权限标题" prop="meta.title">
            <el-input v-model.trim="formData.meta.title" style="width: 255px" />
          </el-form-item>
        </el-col>
        <el-col :span="14">
          <el-form-item prop="meta.showLink">
            <template #label>
              <div class="flex" style="align-items: center">
                <el-tooltip
                  class="box-item"
                  content="是否将其隐藏"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>可见性</label>
              </div>
            </template>
            <el-radio-group v-model="formData.meta.showLink">
              <el-radio :label="true" border>显示</el-radio>
              <el-radio :label="false" border>隐藏</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row>
        <el-col :span="10">
          <el-form-item prop="name">
            <template #label>
              <span>
                <div class="flex" style="align-items: center">
                  <el-tooltip
                    class="box-item"
                    :content="genreOptions[formData.genre - 1].nameTip"
                    effect="dark"
                    placement="top"
                  >
                    <IconifyIconOnline icon="material-symbols:help-outline" />
                  </el-tooltip>
                  <span>{{ genreOptions[formData.genre - 1].nameProp }}</span>
                </div>
              </span>
            </template>
            <el-input
              v-model.trim="formData.name"
              :disabled="false"
              style="width: 255px"
            />
          </el-form-item>
        </el-col>
        <el-col :span="14">
          <el-form-item prop="path">
            <template #label>
              <span>
                <div class="flex" style="align-items: center">
                  <el-tooltip
                    class="box-item"
                    :content="genreOptions[formData.genre - 1].pathTip"
                    effect="dark"
                    placement="top"
                  >
                    <IconifyIconOnline icon="material-symbols:help-outline" />
                  </el-tooltip>
                  <span>{{ genreOptions[formData.genre - 1].pathProp }}</span>
                </div>
              </span>
            </template>
            <el-input v-model.trim="formData.path" style="width: 400px" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-divider />
      <el-row>
        <el-col :span="10">
          <el-form-item label="组件路径">
            <el-input
              v-model.trim="formData.component"
              clearable
              style="width: 255px"
              placeholder="选填"
            />
          </el-form-item>
        </el-col>
        <el-col :span="14">
          <el-form-item
            v-show="[1, 3].includes(formData.genre)"
            label="是否缓存"
            prop="meta.keepAlick"
          >
            <el-radio-group v-model="formData.meta.keepAlive">
              <el-radio :label="true" border>是</el-radio>
              <el-radio :label="false" border>否</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row>
        <el-col :span="10">
          <el-form-item prop="meta.icon">
            <template #label>
              <div class="flex" style="align-items: center">
                <el-tooltip
                  class="box-item"
                  content="请访问 https://icones.js.org/ 查询"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>图标</label>
              </div>
            </template>
            <el-input
              v-model.trim="formData.meta.icon"
              clearable
              style="width: 255px"
              placeholder="选填"
            />
          </el-form-item>
        </el-col>
        <el-col :span="14">
          <el-form-item v-show="[1, 3].includes(formData.genre)">
            <template #label>
              <div class="flex" style="align-items: center">
                <el-tooltip
                  class="box-item"
                  content="当下级菜单只有一个的时候是否显示父级菜单"
                  effect="dark"
                  placement="top"
                >
                  <IconifyIconOnline icon="material-symbols:help-outline" />
                </el-tooltip>
                <label>显示父级</label>
              </div>
            </template>
            <el-radio-group v-model="formData.meta.showParent">
              <el-radio :label="true" border>是</el-radio>
              <el-radio :label="false" border>否</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row>
        <el-col :span="10">
          <el-form-item label="排序" prop="queue">
            <el-input-number v-model="formData.queue" :min="0" :step="5" />
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>

    <template #footer>
      <el-button @click="closeDialogSimple" size="large">取消</el-button>
      <el-button type="primary" @click="submitForm(ruleFormRef)" size="large">
        确定
      </el-button>
    </template>
  </el-dialog>
</template>
