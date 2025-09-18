<script setup lang="ts">
import {
  ref,
  toRaw,
  reactive,
  watch,
  onMounted,
  onBeforeUnmount,
  nextTick
} from "vue";
import Motion from "./utils/motion";
import { useRouter } from "vue-router";
import { message } from "@/utils/message";
import { loginRules } from "./utils/rule";

import TypeIt from "@/components/ReTypeit";

import { useNav } from "@/layout/hooks/useNav";
import type { FormInstance } from "element-plus";

import { useLayout } from "@/layout/hooks/useLayout";
import { useUserStoreHook } from "@/store/modules/user";
import { initRouter, getTopMenu } from "@/router/utils";
import { bg, avatar, illustration } from "./utils/static";

import { useRenderIcon } from "@/components/ReIcon/src/hooks";

import { useDataThemeChange } from "@/layout/hooks/useDataThemeChange";

import dayIcon from "@/assets/svg/day.svg?component";
import darkIcon from "@/assets/svg/dark.svg?component";
import Lock from "@iconify-icons/ri/lock-fill";
import User from "@iconify-icons/ri/user-3-fill";
import Info from "@iconify-icons/ri/information-line";

defineOptions({
  name: "Login"
});

const loginDay = ref(7);
const router = useRouter();
const loading = ref(false);
const checked = ref(false);
const ruleFormRef = ref<FormInstance>();

const { initStorage } = useLayout();
initStorage();
const { dataTheme, dataThemeChange } = useDataThemeChange();
dataThemeChange();
const { title } = useNav();

const ruleForm = reactive({
  username: "",
  password: ""
});

const onLogin = async (formEl: FormInstance | undefined) => {
  loading.value = true;
  if (!formEl) return;
  await formEl.validate((valid, fields) => {
    if (valid) {
      useUserStoreHook()
        .loginByUsername(ruleForm)
        .then(res => {
          if (res) {
            // 获取后端路由
            initRouter().then(() => {
              router.push(getTopMenu(true).path);
              message("登录成功", { type: "success" });
            });
          }
        })
        .catch(err => {
          message(err.message, { type: "error" });
          loading.value = false;
        });
    } else {
      loading.value = false;
      return fields;
    }
  });
};

/** 使用公共函数，避免`removeEventListener`失效 */
function onkeypress({ code }: KeyboardEvent) {
  if (code === "Enter") {
    onLogin(ruleFormRef.value);
  }
}

const isLogining = ref(false);
const doLoginWithTicket = async () => {
  // http://localhost:8849/#/login?next=http://localhost:8849/#/&ticket=f8085ec9ca7cb0299847879321837f8c
  // 尝试从地址栏获取 ticket 参数
  const query = router.currentRoute.value.query || {};
  const ticket = query.ticket as string;
  const next = (query.next as string) || getTopMenu(true).path;
  if (!ticket) return;

  isLogining.value = true;
  useUserStoreHook()
    .loginBySSOTicket(ticket)
    .then(res => {
      if (res) {
        // 获取后端路由
        initRouter().then(() => {
          // 使用 nextTick 确保路由完全初始化后再跳转
          nextTick(() => {
            router.push(next).catch(err => {
              console.error("路由跳转失败:", err);
              // 如果跳转失败，回退到默认页面
              router.push(getTopMenu(true).path);
            });
            message("登录成功", { type: "success" });
          });
        });
      }
    })
    .catch(err => {
      message(err.message, { type: "error" });
    })
    .finally(() => {
      isLogining.value = false;
      // 清除地址栏中的 ticket 参数，避免重复登录
      router.replace({ path: "/login" });
    });
};

const onSSOLogin = () => {
  // 跳转 / 目录自动触发 SSO 登录
  router.push("/");
};

onMounted(() => {
  doLoginWithTicket();
  window.document.addEventListener("keypress", onkeypress);
});

onBeforeUnmount(() => {
  window.document.removeEventListener("keypress", onkeypress);
});

watch(checked, bool => {
  useUserStoreHook().SET_ISREMEMBERED(bool);
});
watch(loginDay, value => {
  useUserStoreHook().SET_LOGINDAY(value);
});
</script>

<template>
  <div class="select-none">
    <img :src="bg" class="wave" />
    <div class="flex-c absolute right-5 top-3">
      <!-- 主题 -->
      <el-switch
        v-model="dataTheme"
        inline-prompt
        :active-icon="dayIcon"
        :inactive-icon="darkIcon"
        @change="dataThemeChange"
      />
    </div>
    <div class="login-container">
      <div class="img flex justify-center items-center">
        <component :is="toRaw(illustration)" />
      </div>
      <div class="login-box">
        <div class="login-form">
          <avatar class="avatar" />
          <Motion>
            <h2 class="outline-none">
              <TypeIt
                :values="[title]"
                :cursor="false"
                :speed="150"
                className="text-gray-400"
              />
            </h2>
          </Motion>

          <el-form
            v-if="true"
            v-loading="isLogining"
            element-loading-text="努力登录中..."
            ref="ruleFormRef"
            :model="ruleForm"
            :rules="loginRules"
            size="large"
          >
            <Motion :delay="100" v-if="false">
              <el-form-item
                :rules="[
                  {
                    required: true,
                    message: '请输入账号',
                    trigger: 'blur'
                  }
                ]"
                prop="username"
              >
                <el-input
                  clearable
                  v-model="ruleForm.username"
                  placeholder="账号"
                  :prefix-icon="useRenderIcon(User)"
                />
              </el-form-item>
            </Motion>

            <Motion :delay="150" v-if="false">
              <el-form-item prop="password">
                <el-input
                  clearable
                  show-password
                  v-model="ruleForm.password"
                  placeholder="密码"
                  :prefix-icon="useRenderIcon(Lock)"
                />
              </el-form-item>
            </Motion>

            <Motion :delay="250" v-if="false">
              <el-form-item>
                <div class="w-full h-[20px] flex justify-between items-center">
                  <el-checkbox v-model="checked">
                    <span class="flex">
                      <select
                        v-model="loginDay"
                        :style="{
                          width: loginDay < 10 ? '10px' : '16px',
                          outline: 'none',
                          background: 'none',
                          appearance: 'none'
                        }"
                      >
                        <option value="1">1</option>
                        <option value="7">7</option>
                        <option value="30">30</option>
                      </select>
                      {{ "天内免登录" }}
                      <el-tooltip
                        effect="dark"
                        placement="top"
                        content="勾选并登录后，规定天数内无需输入用户名和密码会自动登入系统"
                      >
                        <IconifyIconOffline :icon="Info" class="ml-1" />
                      </el-tooltip>
                    </span>
                  </el-checkbox>
                  <!-- <el-button
                    link
                    type="primary"
                    @click="useUserStoreHook().SET_CURRENTPAGE(4)"
                    >忘记密码</el-button
                  > -->
                </div>
                <el-button
                  class="w-full mt-4"
                  size="large"
                  type="primary"
                  :loading="loading"
                  plain
                  @click="onLogin(ruleFormRef)"
                >
                  登 录
                </el-button>
              </el-form-item>
            </Motion>

            <Motion :delay="250">
              <el-form-item>
                <el-button
                  class="w-full mt-4"
                  size="large"
                  type="primary"
                  :loading="loading"
                  plain
                  @click="onSSOLogin()"
                >
                  SSO 登 录
                </el-button>
              </el-form-item>
            </Motion>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import url("@/style/login.css");
</style>

<style lang="scss" scoped>
:deep(.el-input-group__append, .el-input-group__prepend) {
  padding: 0;
}

.translation {
  ::v-deep(.el-dropdown-menu__item) {
    padding: 5px 40px;
  }

  .check-zh {
    position: absolute;
    left: 20px;
  }

  .check-en {
    position: absolute;
    left: 20px;
  }
}
</style>
