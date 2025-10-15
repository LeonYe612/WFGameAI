<script setup lang="ts">
import { ref } from "vue";
import ScriptEditor from "@/views/common/editor/scriptEditor/index.vue";
const ScriptEditorRef = ref<InstanceType<typeof ScriptEditor> | null>(null);
const handleEdit = () => {
  /**
   * 调用子组件的方法
   * edit: (id?: number, mode?: "_dialog" | "_blank" | "_self")
   * id: 脚本ID，传入则编辑已有脚本，不传则新建脚本
   * mode: 编辑模式, 默认值为"_dialog"
   *    "_dialog"表示在对话框中编辑
   *    "_blank"表示在新标签页中打开
   *    "_self"表示在当前标签页中打开
   * 你可以通过 props传递 mode参数静态设置编辑模式
   * 也可以在调用 edit方法时动态传递 mode参数
   */
  ScriptEditorRef.value?.edit(1, "_dialog"); // 传入 ID，编辑已有脚本
};
const onSave = () => {
  console.log("保存成功后的回调");
};
</script>
<template>
  <div>
    <div @click="handleEdit">触发编辑组件显示</div>
    <ScriptEditor ref="ScriptEditorRef" mode="_dialog" @save="onSave" />
  </div>
</template>
