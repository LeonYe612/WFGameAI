<script lang="ts" setup>
import { ref } from "vue";
import { FormInstance } from "element-plus";
import { listTeam, editTeam } from "@/api/team";
import { clone } from "@pureadmin/utils";
import { formRules } from "../utils/rules";
import { ReEdit } from "@/components/ReEdit";
import { superRequest } from "@/utils/request";
import FileIcon from "@/assets/svg/file.svg?component";
import TeamIcon from "@/assets/svg/team.svg?component";

defineOptions({
  name: "SysTeamManagementEdit"
});
const emit = defineEmits(["fetch-data"]);

const ruleFormRef = ref<FormInstance>();
const defaultFormData = ref({
  parent_id: 0,
  genre: 1,
  name: "",
  queue: 0
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
  titleExt: "目录/团队",
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
        apiFunc: editTeam,
        apiParams: { ...formData.value },
        enableSucceedMsg: true,
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

const filterCatelogOnly = function (data: any[]) {
  const arr = data.filter(item => item.genre == 1);
  arr.forEach(item => {
    if (item.children?.length) {
      item.children = filterCatelogOnly(item.children);
    }
  });
  return arr;
};

const fetchData = async () => {
  await superRequest({
    apiFunc: listTeam,
    onSucceed: data => {
      // 仅保留[目录类型]
      treeData.value = [
        {
          id: 0,
          parent_id: 0,
          name: "根目录",
          genre: 1,
          children: filterCatelogOnly(data)
        }
      ];
    }
  });
};

const showLable = (data: any) => {
  return data.name;
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
        <el-form-item label="类型选择" prop="genre">
          <el-radio-group v-model="formData.genre">
            <el-radio :label="1" border>
              <div class="flex items-center">
                <el-icon :size="20">
                  <FileIcon />
                </el-icon>
                <span class="text-yellow-500 ms-1">目录</span>
              </div>
            </el-radio>
            <el-radio :label="2" border>
              <div class="flex items-center">
                <el-icon :size="20">
                  <TeamIcon />
                </el-icon>
                <span class="text-blue-400 ms-1">团队</span>
              </div>
            </el-radio>
          </el-radio-group>
        </el-form-item>
      </el-row>
      <el-row>
        <el-form-item label="所属目录">
          <el-tree-select
            v-model="formData.parent_id"
            check-strictly
            clearable
            :data="treeData"
            default-expand-all
            highlight-current
            :props="{
              children: 'children',
              label: showLable,
              value: 'id'
            }"
            :render-after-expand="false"
            style="width: 255px"
          />
        </el-form-item>
      </el-row>
      <el-row>
        <el-form-item
          :label="`${formData.genre == 1 ? '目录' : '团队'}名称`"
          prop="name"
        >
          <el-input v-model.trim="formData.name" style="width: 255px" />
        </el-form-item>
      </el-row>
      <el-row>
        <el-form-item prop="queue">
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
            v-model="formData.queue"
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
