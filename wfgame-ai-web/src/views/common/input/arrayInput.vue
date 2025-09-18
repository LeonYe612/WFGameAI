<script lang="ts" setup>
import { nextTick, ref, watch } from "vue";
import { ElInput } from "element-plus";
import { Plus } from "@element-plus/icons-vue";

defineOptions({
  name: "ArrayInput"
});

const props = defineProps({
  modelValue: {
    type: Array,
    required: true
  },
  type: {
    type: String,
    default: "number" // number | text
  },
  disabled: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(["update:modelValue"]);
const inputValue = ref("");
const arr = ref(props.modelValue || []);

const inputVisible = ref(false);
const InputRef = ref<InstanceType<typeof ElInput>>();

const handleRemove = (item: any) => {
  arr.value.splice(arr.value.indexOf(item), 1);
  // emit("update:modelValue", arr);
};

const showInput = () => {
  inputVisible.value = true;
  nextTick(() => {
    InputRef.value!.input!.focus();
  });
};

const handleInputConfirm = () => {
  if (inputValue.value) {
    if (props.type === "number") {
      arr.value.push(Number(inputValue.value));
    } else if (props.type === "text") {
      arr.value.push(inputValue.value);
    }
  }
  inputVisible.value = false;
  inputValue.value = "";
};

// const clear = () => {
//   arr.value = [];
//   // emit("update:modelValue", arr);
// };

watch(
  () => props.modelValue,
  () => {
    emit("update:modelValue", arr.value);
  },
  { immediate: true }
);
</script>

<template>
  <el-tag
    v-for="(item, index) in arr"
    :key="index"
    type="info"
    class="mx-1 mt-1"
    :closable="!props.disabled"
    :disable-transitions="false"
    @close="handleRemove(item)"
    plain
  >
    {{ item }}
  </el-tag>
  <el-input
    v-if="inputVisible"
    :type="props.type"
    ref="InputRef"
    v-model="inputValue"
    class="ml-1"
    @keyup.enter="handleInputConfirm"
    @blur="handleInputConfirm"
    style="width: 60px"
  />
  <el-button
    v-else
    :disabled="props.disabled"
    class="ml-1 mt-1"
    :icon="Plus"
    size="small"
    @click="showInput"
  />
  <!-- <el-button
    v-if="arr.length > 0"
    class="ml-1 mt-1"
    :icon="Delete"
    size="small"
    @click="clear"
  /> -->
</template>
