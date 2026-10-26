<script setup lang="ts">
import { useI18n } from "vue-i18n";
import Motion from "./utils/motion";
import { useRouter } from "vue-router";
import { message } from "@/utils/message";
import { loginRules } from "./utils/rule";
import TypeIt from "@/components/ReTypeit";
import { debounce } from "@pureadmin/utils";
import { useNav } from "@/layout/hooks/useNav";
import { useEventListener } from "@vueuse/core";
import type { FormInstance } from "element-plus";
import { $t, transformI18n } from "@/plugins/i18n";
import { useLayout } from "@/layout/hooks/useLayout";
import LoginUpdate from "./components/LoginUpdate.vue";
import { getRememberedLogin, setRememberedLogin } from "./utils/remember";
import { useUserStoreHook } from "@/store/modules/user";
import { usePermissionStoreHook } from "@/store/modules/permission";
import { initRouter, getTopMenu } from "@/router/utils";
import { avatar } from "./utils/static";
import { ref, reactive, computed } from "vue";
import { useRenderIcon } from "@/components/ReIcon/src/hooks";
import { useTranslationLang } from "@/layout/hooks/useTranslationLang";
import { useDataThemeChange } from "@/layout/hooks/useDataThemeChange";

import dayIcon from "@/assets/svg/day.svg?component";
import darkIcon from "@/assets/svg/dark.svg?component";
import globalization from "@/assets/svg/globalization.svg?component";
import Lock from "~icons/ri/lock-fill";
import Check from "~icons/ep/check";
import User from "~icons/ri/user-3-fill";

defineOptions({
  name: "Login"
});

const router = useRouter();
const loading = ref(false);
const disabled = ref(false);
const ruleFormRef = ref<FormInstance>();
const currentPage = computed(() => {
  return useUserStoreHook().currentPage;
});

const { t } = useI18n();
const { initStorage } = useLayout();
initStorage();
const { dataTheme, themeMode, dataThemeChange } = useDataThemeChange();
dataThemeChange(themeMode.value);
const { title, getDropdownItemStyle, getDropdownItemClass } = useNav();
const { locale, translationCh, translationEn } = useTranslationLang();

// 表单**不预填任何账号**（原来写死 admin/admin123 是为了本机调试方便，上线后会
// 让每个打开登录页的人都看到管理员口令）。要免输就勾「记住密码」，由使用者自己选。
const savedLogin = getRememberedLogin();
const ruleForm = reactive({
  username: savedLogin?.username ?? "",
  password: savedLogin?.password ?? ""
});
const remember = ref(Boolean(savedLogin));

const onLogin = async (formEl: FormInstance | undefined) => {
  if (!formEl) return;
  if (loading.value) return; // 防止重复提交
  await formEl.validate(valid => {
    if (valid) {
      loading.value = true;
      useUserStoreHook()
        .loginByUsername({
          username: ruleForm.username,
          password: ruleForm.password
        })
        .then(() => {
          // 登录成功后才动本地存储：失败时不能把刚输的（很可能是打错的）密码存下来
          setRememberedLogin(
            remember.value
              ? { username: ruleForm.username, password: ruleForm.password }
              : null
          );
          return enterSystem();
        })
        .catch((err: Error) => {
          // 走到这里才是真正的认证失败 —— 把后端文案透出来。
          // 11001 同时覆盖「账号不存在 / 被停用」和「密码不对」，唯一的区分线索就是
          // message；原先写死通用文案、把 _err 丢掉，线上就只剩一句没用的「登录失败」。
          disabled.value = false;
          message(err?.message || t("login.pureLoginFail"), { type: "error" });
        })
        .finally(() => {
          loading.value = false;
        });
    }
  });
};

/**
 * 登录成功后的收尾：拉动态路由 → 跳转。
 *
 * ⚠️ 必须和上面的 loginByUsername 分开 catch。合在一条链上会出
 * 「提示登录失败、但 F5 刷新又能进系统」这种怪事：走到这里时 token 已经落盘、
 * 登录本身已经成功，若 initRouter / 跳转抛错，外层那条 .catch 会把它当成
 * 认证失败弹「登录失败」，而刷新走的是路由守卫（router/index.ts 的 beforeEach），
 * 另一条代码路径，不经过这里。
 *
 * 这里全程自己兜住，绝不往外抛 —— 保证外层 .catch 只处理认证失败。
 */
const enterSystem = async () => {
  disabled.value = true;
  let step = "初始化路由";
  try {
    await initRouter();
    // 落到后端返回的第一个菜单（原来硬编码 "/welcome"，示例首页已删）
    const target = getTopMenu()?.path ?? "/";
    step = `跳转 ${target}`;
    await router.push(target);
    message("登录成功", { type: "success" });
  } catch (err) {
    // 带上 step：这两步的失败原因完全不同，混在一起没法查
    console.error(`登录成功，但「${step}」失败:`, err);
    message(`登录成功，但页面初始化失败（${step}），请按 F5 刷新`, {
      type: "warning"
    });
  }
};

const immediateDebounce: any = debounce(
  formRef => onLogin(formRef),
  1000,
  true
);

useEventListener(document, "keydown", (event: KeyboardEvent) => {
  // 输入法正在组词时按 Enter 是「选候选词」，不是「提交表单」。
  // 不判这一下的话，中文输入法下敲完账号一回车就直接登录了。
  // `keyCode === 229` 是部分浏览器/输入法在组合期间的约定，`isComposing` 不够用时兜底。
  if (event.isComposing || event.keyCode === 229) return;
  if (
    ["Enter", "NumpadEnter"].includes(event.code) &&
    !disabled.value &&
    !loading.value
  )
    immediateDebounce(ruleFormRef.value);
});
</script>

<template>
  <div class="select-none">
    <div class="flex-c absolute right-5 top-3">
      <!-- 主题 -->
      <el-switch
        v-model="dataTheme"
        inline-prompt
        :active-icon="dayIcon"
        :inactive-icon="darkIcon"
        @change="dataThemeChange"
      />
      <!-- 国际化 -->
      <el-dropdown trigger="click">
        <globalization
          class="hover:text-primary hover:bg-transparent! size-5 ml-1.5 cursor-pointer outline-hidden duration-300"
        />
        <template #dropdown>
          <el-dropdown-menu class="translation">
            <el-dropdown-item
              :style="getDropdownItemStyle(locale, 'zh')"
              :class="['dark:text-white!', getDropdownItemClass(locale, 'zh')]"
              @click="translationCh"
            >
              <IconifyIconOffline
                v-show="locale === 'zh'"
                class="check-zh"
                :icon="Check"
              />
              简体中文
            </el-dropdown-item>
            <el-dropdown-item
              :style="getDropdownItemStyle(locale, 'en')"
              :class="['dark:text-white!', getDropdownItemClass(locale, 'en')]"
              @click="translationEn"
            >
              <span v-show="locale === 'en'" class="check-en">
                <IconifyIconOffline :icon="Check" />
              </span>
              English
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
    <div class="login-container">
      <div class="login-box">
        <div class="login-form">
          <img :src="avatar" class="avatar" />
          <Motion>
            <h2 class="outline-hidden">
              <TypeIt
                :options="{ strings: [title], cursor: false, speed: 100 }"
              />
            </h2>
          </Motion>

          <el-form
            v-if="currentPage === 0"
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
                    message: transformI18n($t('login.pureUsernameReg')),
                    trigger: 'blur'
                  }
                ]"
                prop="username"
              >
                <el-input
                  v-model="ruleForm.username"
                  clearable
                  :placeholder="t('login.pureUsername')"
                  :prefix-icon="useRenderIcon(User)"
                />
              </el-form-item>
            </Motion>

            <Motion :delay="150">
              <el-form-item prop="password">
                <el-input
                  v-model="ruleForm.password"
                  clearable
                  show-password
                  :placeholder="t('login.purePassword')"
                  :prefix-icon="useRenderIcon(Lock)"
                />
              </el-form-item>
            </Motion>

            <Motion :delay="200">
              <el-form-item>
                <div class="w-full flex-bc">
                  <el-checkbox v-model="remember">
                    {{ t("login.pureRememberPassword") }}
                  </el-checkbox>
                  <el-button
                    link
                    type="primary"
                    @click="useUserStoreHook().SET_CURRENTPAGE(4)"
                  >
                    {{ t("login.pureForget") }}
                  </el-button>
                </div>
                <el-button
                  class="w-full mt-4!"
                  size="default"
                  type="primary"
                  :loading="loading"
                  :disabled="disabled"
                  @click="onLogin(ruleFormRef)"
                >
                  {{ t("login.pureLogin") }}
                </el-button>
              </el-form-item>
            </Motion>
          </el-form>

          <!-- 忘记密码 -->
          <LoginUpdate v-if="currentPage === 4" />
        </div>
      </div>
    </div>
    <div
      class="w-full flex-c absolute bottom-3 text-sm text-[rgba(0,0,0,0.6)] dark:text-[rgba(220,220,242,0.8)]"
    >
      Copyright © 2026-present {{ title }}
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
  :deep(.el-dropdown-menu__item) {
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
