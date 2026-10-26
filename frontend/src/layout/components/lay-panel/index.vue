<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { emitter } from "@/utils/mitt";
import { onClickOutside } from "@vueuse/core";
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useDataThemeChange } from "@/layout/hooks/useDataThemeChange";
import { useUserStoreHook } from "@/store/modules/user";
import CloseIcon from "~icons/ep/close";

const target = ref(null);
const show = ref<Boolean>(false);

const iconClass = computed(() => {
  return [
    "size-5.5",
    "flex-c",
    "outline-hidden",
    "rounded-sm",
    "cursor-pointer",
    "transition-colors",
    "hover:bg-[#0000000f]",
    "dark:hover:bg-[#ffffff1f]",
    "dark:hover:text-[#ffffffd9]"
  ];
});

const { t } = useI18n();
const { onReset } = useDataThemeChange();

/**
 * 直接退出：走 store 的 logOut()，它会调后端 `/auth/logout` 把 token 拉黑。
 *
 * ⚠️ 与下面的「清空缓存」不是一回事：`onReset` 只删本地 token + 清空 localStorage，
 * **不通知后端** —— 那个 token 在自然过期前仍然有效。真要退出登录（尤其是公用电脑），
 * 用这个。
 */
const onLogout = () => useUserStoreHook().logOut();

onClickOutside(target, (event: any) => {
  if (event.clientX > target.value.offsetLeft) return;
  show.value = false;
});

onMounted(() => {
  emitter.on("openPanel", () => {
    show.value = true;
  });
});

onBeforeUnmount(() => {
  // 解绑`openPanel`公共事件，防止多次触发
  emitter.off("openPanel");
});
</script>

<template>
  <div :class="{ show }">
    <div class="right-panel-background" />
    <div ref="target" class="right-panel bg-bg_color">
      <div
        class="flex-bc py-3 px-5 border-0 border-l border-solid border-(--pure-border-color)"
      >
        <h4 class="dark:text-white">
          {{ t("panel.pureSystemSet") }}
        </h4>
        <span
          v-tippy="{
            content: t('panel.pureCloseSystemSet'),
            placement: 'bottom-start',
            zIndex: 41000
          }"
          :class="iconClass"
        >
          <IconifyIconOffline
            class="dark:text-white"
            width="18px"
            height="18px"
            :icon="CloseIcon"
            @click="show = !show"
          />
        </span>
      </div>
      <el-scrollbar
        class="border-y border-l border-r-0 border-solid border-(--pure-border-color) h-[calc(100vh-104px)]!"
      >
        <slot />
      </el-scrollbar>

      <div
        class="flex justify-end p-3 border-0 border-l border-solid border-(--pure-border-color)"
      >
        <el-button type="primary" text bg @click="onLogout">
          {{ t("buttons.pureLoginOut") }}
        </el-button>
        <el-button
          v-tippy="{
            content: t('panel.pureClearCacheAndToLogin'),
            placement: 'left-start',
            zIndex: 41000
          }"
          type="danger"
          text
          bg
          @click="onReset"
        >
          {{ t("panel.pureClearCache") }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.right-panel-background {
  position: fixed;
  top: 0;
  left: 0;
  z-index: -1;
  background: rgb(0 0 0 / 20%);
  opacity: 0;
  transition: opacity 0.3s cubic-bezier(0.7, 0.3, 0.1, 1);
}

.right-panel {
  position: fixed;
  top: 0;
  right: 0;
  z-index: 40000;
  width: 100%;
  max-width: 280px;
  box-shadow: 0 0 15px 0 rgb(0 0 0 / 5%);
  transform: translate(100%);
  transition: all 0.25s cubic-bezier(0.7, 0.3, 0.1, 1);
}

.show {
  transition: all 0.3s cubic-bezier(0.7, 0.3, 0.1, 1);

  .right-panel-background {
    z-index: 20000;
    width: 100%;
    height: 100%;
    opacity: 1;
  }

  .right-panel {
    transform: translate(0);
  }
}
</style>
