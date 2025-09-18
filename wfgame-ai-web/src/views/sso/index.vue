<script setup lang="ts">
import { ref, reactive, watch, onMounted, onBeforeUnmount } from "vue";
import Motion from "./utils/motion";
import { message } from "@/utils/message";
import { loginRules } from "./utils/rule";

import TypeIt from "@/components/ReTypeit";
import type { FormInstance } from "element-plus";

import { useLayout } from "@/layout/hooks/useLayout";
import { useUserStoreHook } from "@/store/modules/user";
import ssoImg from "@/assets/login/sso.png";
import bee from "@/assets/login/bee.png";

import { useRenderIcon } from "@/components/ReIcon/src/hooks";

import { useDataThemeChange } from "@/layout/hooks/useDataThemeChange";

import dayIcon from "@/assets/svg/day.svg?component";
import darkIcon from "@/assets/svg/dark.svg?component";
import Lock from "@iconify-icons/ri/lock-fill";
import User from "@iconify-icons/ri/user-3-fill";
import Info from "@iconify-icons/ri/information-line";
import { storageLocal } from "@pureadmin/utils";
import { ssoLogin } from "@/api/sso";
import { ElMessageBox } from "element-plus";

defineOptions({
  name: "Login"
});

const loginDay = ref(7);
const loading = ref(false);
const checked = ref(false);
const ruleFormRef = ref<FormInstance>();

const { initStorage } = useLayout();
initStorage();
const { dataTheme, dataThemeChange } = useDataThemeChange();
dataThemeChange();

const ruleForm = reactive({
  username: "",
  password: ""
});

const LOCAL_KEY = "wf-sso-ticket";

const getRedirectParam = () => {
  const urlParams = new URL(window.location.href).searchParams;
  const redirect = urlParams.get("redirect");
  return redirect ? decodeURIComponent(redirect) : "";
};

const doLogin = (
  data: {
    username?: string;
    password?: string;
    ticket?: string;
    redirect?: string;
  },
  onSucceed: Function = () => {}
) => {
  // 1. 当前url中的必须携带 redirect 参数
  data.redirect = getRedirectParam();
  if (!data.redirect) {
    message("请传递认证成功后的跳转地址 redirect !", {
      type: "error"
    });
    return;
  }
  ssoLogin(data)
    .then(res => {
      if (res?.code > 0) {
        switch (res.code) {
          case 10002:
            message("跳转地址 redirect 必须是一个有效的URL", { type: "error" });
            break;
          default:
            message(res.msg || "sso认证失败, 请稍后再试！", { type: "error" });
            break;
        }
      } else if (res?.code === 0) {
        storageLocal().setItem(LOCAL_KEY, res.data?.ticket || "");
        message("sso认证成功, 正在跳转...", { type: "success" });
        window.location.href = res.data?.redirect;
        onSucceed && onSucceed();
      }
    })
    .catch(() => {
      message("sso认证请求失败, 请稍后再试！", { type: "error" });
    });
};

const handleLoginClick = async (formEl: FormInstance | undefined) => {
  loading.value = true;
  if (!formEl) return;
  await formEl.validate(valid => {
    try {
      if (!valid) return;
      doLogin({
        username: ruleForm.username,
        password: ruleForm.password
      });
      // 2. 请求 sso Login API
    } catch (error) {
      message("sso认证出错：", { type: "error" });
    } finally {
      loading.value = false;
    }
  });
};

/** 使用公共函数，避免`removeEventListener`失效 */
function onkeypress({ code }: KeyboardEvent) {
  if (code === "Enter") {
    handleLoginClick(ruleFormRef.value);
  }
}

const cookieLoginLoading = ref(false);
function loginWithCookie() {
  const ticket = storageLocal().getItem(LOCAL_KEY) as string;
  if (!ticket) return;
  const redirect = getRedirectParam();
  if (!redirect) return;

  // 尝试自动登录的条件
  // 1. 本地存在 ticket
  // 2. 当前url中的必须携带 redirect 参数
  ElMessageBox.confirm("检测到历史登录凭证，是否自动登录？", "自动登录提示", {
    confirmButtonText: "是",
    cancelButtonText: "否",
    type: "warning"
  })
    .then(() => {
      cookieLoginLoading.value = true;
      message("正在自动登录...", { type: "warning" });
      setTimeout(() => {
        doLogin({ ticket }, () => {
          cookieLoginLoading.value = false;
        });
      }, 1000);
    })
    .catch(() => {
      // 用户取消自动登录，无需处理
    });
}

onMounted(() => {
  loginWithCookie();
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
  <div class="sso-page">
    <div class="sso-main">
      <div class="sso-img-bg">
        <img :src="ssoImg" class="sso-img" />
      </div>
      <div class="sso-login-card">
        <div class="flex justify-center items-center flex-col w-full">
          <img :src="bee" class="w-14 h-14" />
          <Motion>
            <h3 class="login-title">
              <TypeIt
                :values="['玩蜂 | SSO认证中心']"
                :cursor="false"
                :speed="150"
                className="text-yellow-400"
              />
            </h3>
          </Motion>

          <el-form
            v-loading="cookieLoginLoading"
            element-loading-text="自动登录中..."
            ref="ruleFormRef"
            :model="ruleForm"
            :rules="loginRules"
            size="large"
          >
            <Motion :delay="100">
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
                  style="width: 240px"
                  clearable
                  v-model="ruleForm.username"
                  placeholder="账号"
                  :prefix-icon="useRenderIcon(User)"
                />
              </el-form-item>
            </Motion>

            <Motion :delay="150">
              <el-form-item prop="password">
                <el-input
                  style="width: 240px"
                  clearable
                  show-password
                  v-model="ruleForm.password"
                  placeholder="密码"
                  :prefix-icon="useRenderIcon(Lock)"
                />
              </el-form-item>
            </Motion>

            <Motion :delay="250">
              <el-form-item>
                <div
                  v-if="false"
                  class="w-full h-[20px] flex justify-between items-center"
                >
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
                  type="warning"
                  :loading="loading"
                  plain
                  @click="handleLoginClick(ruleFormRef)"
                >
                  登 录
                </el-button>
              </el-form-item>
            </Motion>
          </el-form>
        </div>
      </div>
    </div>
    <div class="theme-switch" v-if="false">
      <el-switch
        v-model="dataTheme"
        inline-prompt
        :active-icon="dayIcon"
        :inactive-icon="darkIcon"
        @change="dataThemeChange"
      />
    </div>
  </div>
</template>

<style scoped>
.sso-page {
  min-height: 100vh;
  background: #f6f7fb;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.sso-main {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 48px;
  width: 100%;
  max-width: 1100px;
  padding: 40px 20px;
}
.sso-img-bg {
  flex: 0 0 400px;
  background: #f0f1f5;
  border-radius: 20px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04);
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 400px;
  min-height: 400px;
}
.sso-img {
  width: 400px;
  height: 420px;
  object-fit: contain;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  background: #fff;
}
.sso-login-card {
  flex: 0 0 400px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  padding: 40px 32px;
  min-width: 400px;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.login-title {
  width: 100%;
  font-size: 1.6rem;
  font-weight: 600;
  margin: 18px 0 20px 0;
  text-align: center;
  letter-spacing: 1px;
  color: #222;
  display: flex;
  align-items: center;
  justify-content: center;
}
.theme-switch {
  position: absolute;
  top: 32px;
  right: 48px;
  z-index: 10;
}
@media (max-width: 900px) {
  .sso-main {
    flex-direction: column;
    gap: 32px;
    max-width: 100vw;
    padding: 24px 8px;
  }
  .sso-img-bg {
    min-width: 220px;
    min-height: 220px;
    padding: 8px;
    flex: unset;
  }
  .sso-img {
    width: 120px;
    height: 120px;
  }
  .sso-login-card {
    padding: 24px 8px;
    min-width: 220px;
    max-width: 100vw;
    flex: unset;
  }
}
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
