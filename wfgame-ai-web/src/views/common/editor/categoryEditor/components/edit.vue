<script lang="ts" setup>
import { ref } from "vue";
import { FormInstance } from "element-plus";
import { categoryApi } from "@/api/scripts";
import { clone } from "@pureadmin/utils";
import { formRules } from "../utils/rules";
import { ReEdit } from "@/components/ReEdit";
import { superRequest } from "@/utils/request";

defineOptions({
  name: "CatalogManagementEdit"
});
const emit = defineEmits(["fetch-data"]);

const ruleFormRef = ref<FormInstance>();
const defaultFormData = ref({
  id: null,
  parent: null,
  name: "",
  sort_order: 0
});

const formVisible = ref(false);
const formData = ref(clone(defaultFormData, true));
const title = ref("");
const isAdd = ref(false);
const submitLoading = ref(false);

const { showEdit, closeDialog, closeDialogSimple } = ReEdit({
  defaultFormData: defaultFormData,
  formData: formData,
  formVisible: formVisible,
  isAdd: isAdd,
  ruleFormRef: ruleFormRef,
  title: title,
  titleExt: "目录",
  doneFn: () => {
    emit("fetch-data");
  }
});

const treeData = ref<any>();

const submitForm = async (formEl: FormInstance | undefined) => {
  if (!formEl) return;
  await formEl.validate(async valid => {
    if (valid) {
      if (!formData.value.parent) {
        formData.value.parent = null;
      }
      await superRequest({
        apiFunc: isAdd.value ? categoryApi.create : categoryApi.update,
        apiParams: formData.value,
        enableSucceedMsg: true,
        onBeforeRequest: () => {
          submitLoading.value = true;
        },
        onSucceed: () => {
          closeDialog();
        },
        onCompleted: () => {
          submitLoading.value = false;
        }
      });
    }
  });
};

const showEditWithParent = (pid: number) => {
  if (pid >= 0) {
    showEdit({ parent: pid });
  }
};

// 查询Edit下单目录的选项列表
const fetchData = async () => {
  await superRequest({
    apiFunc: categoryApi.tree,
    onSucceed: data => {
      // 仅保留[目录类型]
      treeData.value = [
        {
          id: 0,
          parent: null,
          name: "根目录",
          children: data
        }
      ];
    }
  });
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
    width="500px"
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
        <el-form-item label="所属目录">
          <el-tree-select
            v-model="formData.parent"
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
            style="width: 255px"
          />
        </el-form-item>
      </el-row>
      <el-row>
        <el-form-item label="目录名称" prop="name">
          <el-input v-model.trim="formData.name" style="width: 255px" />
        </el-form-item>
      </el-row>
      <el-row>
        <el-form-item prop="sort_order">
          <template #label>
            <div class="flex" style="align-items: center">
              <el-tooltip
                class="box-item"
                content="排序权重"
                effect="dark"
                placement="top"
              >
                <IconifyIconOnline icon="material-symbols:help-outline" />
              </el-tooltip>
              <label>排序</label>
            </div>
          </template>
          <el-input-number
            v-model="formData.sort_order"
            :min="0"
            :step="5"
            style="width: 255px"
          />
        </el-form-item>
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
