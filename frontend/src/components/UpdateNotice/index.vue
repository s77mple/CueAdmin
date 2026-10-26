<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { storageLocal } from "@pureadmin/utils";
import { UPDATE_NOTICE } from "@/constants/update-notice";

/** 本地记的「已读版本」—— 与当前版本不一致就弹窗 */
const SEEN_KEY = "update-notice-seen-version";

const { t } = useI18n();
const visible = ref(false);

onMounted(() => {
  let seen: string | null = null;
  try {
    seen = storageLocal().getItem<string | null>(SEEN_KEY);
  } catch {
    // 存储被禁用 —— 当没看过处理，最坏也只是多弹一次
  }
  visible.value = seen !== UPDATE_NOTICE.version;
});

function onClosed() {
  // 点 ×、点遮罩、按 ESC 都走这里 —— 关掉就算已读，不能反复打扰
  try {
    storageLocal().setItem(SEEN_KEY, UPDATE_NOTICE.version);
  } catch {
    // 写不进去就下次再弹，不影响使用
  }
}
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="t('updateNotice.title')"
    width="520px"
    append-to-body
    @closed="onClosed"
  >
    <div class="notice-head">
      <span class="notice-version">{{ UPDATE_NOTICE.version }}</span>
      <span class="notice-date">{{ UPDATE_NOTICE.date }}</span>
    </div>
    <ul class="notice-list">
      <li v-for="(item, index) in UPDATE_NOTICE.items" :key="index">
        {{ item }}
      </li>
    </ul>
    <template #footer>
      <el-button type="primary" @click="visible = false">
        {{ t("updateNotice.confirm") }}
      </el-button>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
.notice-head {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}

.notice-version {
  padding: 2px 8px;
  font-size: 12px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-radius: 4px;
}

.notice-date {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.notice-list {
  padding-left: 18px;
  margin: 0;
  line-height: 2;
  color: var(--el-text-color-regular);
  list-style: disc;
}
</style>
