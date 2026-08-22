<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { PureTableBar } from "@/components/RePureTableBar";
import { getErrorCodes } from "@/api/meta";

const loading = ref(false);
const list = ref<any[]>([]);

const columns: TableColumnList = [
  { label: "错误码", slot: "code", minWidth: 120 },
  { label: "枚举名", slot: "name", minWidth: 260 },
  { label: "含义", slot: "description", minWidth: 320 },
];

/* 错误码分段 — 与后端 exceptions.py 的注释分段保持一致 */
const SEGMENTS = [
  { code: "auth",   label: "认证（登录/令牌）", min: 11000, max: 11999 },
  { code: "user",   label: "用户",             min: 12000, max: 12999 },
  { code: "role",   label: "角色",             min: 13000, max: 13999 },
  { code: "menu",   label: "菜单",             min: 14000, max: 14999 },
  { code: "perm",   label: "权限",             min: 15000, max: 15999 },
  { code: "access", label: "访问控制",         min: 16000, max: 16999 },
  { code: "common", label: "通用业务",         min: 17000, max: 17999 },
  { code: "dept",   label: "部门",             min: 18000, max: 18999 },
];

/* 构建树形数据：错误码段为父节点，具体错误码为子节点 */
const treeData = computed(() =>
  SEGMENTS.map(seg => ({
    _treeId: `seg:${seg.code}`,
    _isGroup: true,
    _label: seg.label,
    _count: list.value.filter(i => i.code >= seg.min && i.code <= seg.max).length,
    children: list.value
      .filter(i => i.code >= seg.min && i.code <= seg.max)
      .sort((a, b) => a.code - b.code)
      .map(i => ({ ...i, _treeId: `ec:${i.code}` })),
  })).filter(g => g._count > 0)
);

const pureTableRef = ref();
const treeBarRef = computed(() => {
  const el = pureTableRef.value?.getTableRef?.();
  if (!el) return null;
  return {
    data: treeData.value,
    size: "default",
    toggleRowExpansion: (row: any, expanded: boolean) => el.toggleRowExpansion(row, expanded),
  };
});

async function onSearch() {
  loading.value = true;
  try {
    const res = await getErrorCodes();
    if (res.code === 0) list.value = res.data ?? [];
    else ElMessage.error(res.message || "加载错误码字典失败");
  } finally { loading.value = false; }
}

onMounted(onSearch);
</script>

<template>
  <div>
    <PureTableBar :columns="columns" :table-ref="treeBarRef" @refresh="onSearch">
      <template #title>
        <el-tag type="info" effect="plain">共 {{ list.length }} 个错误码 · 数据来源 GET /api/v1/system/meta/error-codes</el-tag>
      </template>
      <template v-slot="{ size, dynamicColumns }">
        <pure-table
          ref="pureTableRef"
          row-key="_treeId"
          :tree-props="{ children: 'children', hasChildren: 'hasChildren', checkStrictly: false }"
          default-expand-all
          align-whole="center"
          showOverflowTooltip
          :loading="loading"
          :size="size"
          :data="treeData"
          :columns="dynamicColumns"
          :header-cell-style="{ background: 'var(--el-fill-color-light)', color: 'var(--el-text-color-primary)' }"
        >
          <template #code="{ row }">
            <template v-if="row._isGroup">
              <span class="group-label">{{ row._label }}</span>
              <el-tag size="small" round style="margin-left: 8px">{{ row._count }} 项</el-tag>
            </template>
            <span v-else class="code-cell">{{ row.code }}</span>
          </template>
          <template #name="{ row }">
            <span v-if="!row._isGroup" class="code-cell">{{ row.name }}</span>
          </template>
          <template #description="{ row }">
            <span v-if="!row._isGroup">{{ row.description }}</span>
          </template>
        </pure-table>
      </template>
    </PureTableBar>
  </div>
</template>

<style scoped>
.group-label {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}
.code-cell {
  padding-left: 16px;
  font-family: "JetBrains Mono", Consolas, monospace;
}
</style>
