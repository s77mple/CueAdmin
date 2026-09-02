<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus } from "@element-plus/icons-vue";
import type { FormInstance, FormRules } from "element-plus";
import { PureTableBar } from "@/components/RePureTableBar";
import {
  getPermissionList,
  getPermission,
  createPermission,
  updatePermission,
  deletePermission
} from "@/api/system/permissions";
import type { Permission } from "@/api/system/types";
import { ErrorCode } from "@/constants/error-code";

const loading = ref(false);
const list = ref<Permission[]>([]);
const dialogVisible = ref(false);
const dialogTitle = ref("新增权限");

const form = reactive({
  id: 0,
  code: "",
  name: "",
  resource: "",
  action: "",
  description: ""
});
const formRef = ref<FormInstance>();

// 服务端唯一性冲突（15002 权限码已存在）→ 字段级标红
const fieldErrors = reactive({ code: "" });

const rules: FormRules = {
  code: [{ required: true, message: "请输入权限编码", trigger: "blur" }],
  name: [{ required: true, message: "请输入权限名称", trigger: "blur" }],
  resource: [{ required: true, message: "请输入资源标识", trigger: "blur" }],
  action: [{ required: true, message: "请输入操作标识", trigger: "blur" }]
};

const resourceLabelMap: Record<string, string> = {
  user: "用户管理",
  role: "角色管理",
  menu: "菜单管理",
  permission: "权限管理",
  department: "部门管理"
};

const columns: TableColumnList = [
  { label: "权限码", slot: "code", minWidth: 150 },
  { label: "名称", slot: "name" },
  { label: "操作", slot: "action", width: 100 },
  { label: "描述", slot: "description" },
  { label: "管理", slot: "operation", width: 180, fixed: "right" }
];

/* 构建树形数据：resource 分组为父节点，权限为子节点 */
const treeData = computed(() => {
  const groups: Record<string, any[]> = {};
  for (const p of list.value) {
    const r = p.resource || "other";
    if (!groups[r]) groups[r] = [];
    groups[r].push(p);
  }
  return Object.entries(groups)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([resource, perms]) => ({
      _treeId: `res:${resource}`,
      resource,
      _isGroup: true,
      _label: resourceLabelMap[resource] || resource,
      _count: perms.length,
      children: perms
        .sort((a, b) => (a.action || "").localeCompare(b.action || ""))
        .map((p: any) => ({ ...p, _treeId: `perm:${p.id}` }))
    }));
});

const pureTableRef = ref();
const treeBarRef = computed(() => {
  const el = pureTableRef.value?.getTableRef?.();
  if (!el) return null;
  return {
    data: treeData.value,
    size: "default",
    toggleRowExpansion: (row: any, expanded: boolean) =>
      el.toggleRowExpansion(row, expanded)
  };
});

async function onSearch() {
  loading.value = true;
  try {
    const res = await getPermissionList();
    if (res.code === 0) list.value = res.data?.items ?? [];
    else ElMessage.error(res.message || "加载权限列表失败");
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  dialogTitle.value = "新增权限";
  Object.assign(form, {
    id: 0,
    code: "",
    name: "",
    resource: "",
    action: "",
    description: ""
  });
  fieldErrors.code = "";
  dialogVisible.value = true;
}

async function openEdit(row: Permission) {
  dialogTitle.value = "编辑权限";
  const res = await getPermission(row.id);
  if (res.code !== 0) {
    ElMessage.error(res.message || "加载权限详情失败");
    return;
  }
  const detail = res.data!;
  Object.assign(form, {
    id: detail.id,
    code: detail.code,
    name: detail.name,
    resource: detail.resource,
    action: detail.action,
    description: detail.description ?? ""
  });
  fieldErrors.code = "";
  dialogVisible.value = true;
}

/** 保存失败：唯一性冲突（权限码已存在）标红字段，其余走 toast */
function onSaveFail(res: any, fallback: string) {
  if (res.code === ErrorCode.PERM_CODE_EXISTS) {
    fieldErrors.code = res.message || "权限编码已存在";
    return;
  }
  ElMessage.error(res.message || fallback);
}

async function handleSubmit() {
  if (!formRef.value) return;
  // 每次提交前清空字段级错误：el-form-item 的 error 是 watch 属性，
  // 同值重复赋值不会触发显示，否则连续提交相同编码时错误只会出现一次
  fieldErrors.code = "";
  try {
    await formRef.value.validate();
    const data = {
      code: form.code,
      name: form.name,
      resource: form.resource,
      action: form.action,
      description: form.description || null
    };
    if (form.id) {
      const res = await updatePermission(form.id, data);
      if (res.code !== 0) {
        onSaveFail(res, "更新失败");
        return;
      }
      ElMessage.success("更新成功");
    } else {
      const res = await createPermission(data);
      if (res.code !== 0) {
        onSaveFail(res, "创建失败");
        return;
      }
      ElMessage.success("创建成功");
    }
    dialogVisible.value = false;
    onSearch();
  } catch (err: any) {
    if (err?.message) ElMessage.error(err.message);
  }
}

async function handleDelete(row: Permission) {
  try {
    await ElMessageBox.confirm(`确认删除权限 "${row.name}"？`, "提示", {
      type: "warning"
    });
    const res = await deletePermission(row.id);
    if (res.code === 0) {
      ElMessage.success(res.message || "已删除");
      onSearch();
    } else {
      ElMessage.error(res.message || "删除失败");
    }
  } catch {
    /* 用户取消或拦截器已弹 toast */
  }
}

onMounted(onSearch);
</script>

<template>
  <div>
    <PureTableBar
      :columns="columns"
      :table-ref="treeBarRef"
      @refresh="onSearch"
    >
      <template #title>
        <el-button
          v-perms="['permission:create']"
          type="primary"
          :icon="Plus"
          @click="openCreate"
          >新增权限</el-button
        >
      </template>
      <template v-slot="{ size, dynamicColumns }">
        <pure-table
          ref="pureTableRef"
          row-key="_treeId"
          :tree-props="{
            children: 'children',
            hasChildren: 'hasChildren',
            checkStrictly: false
          }"
          default-expand-all
          align-whole="center"
          showOverflowTooltip
          :loading="loading"
          :size="size"
          :data="treeData"
          :columns="dynamicColumns"
          :header-cell-style="{
            background: 'var(--el-fill-color-light)',
            color: 'var(--el-text-color-primary)'
          }"
        >
          <template #code="{ row }">
            <template v-if="row._isGroup">
              <span class="group-row-label">{{ row._label }}</span>
              <el-tag size="small" round style="margin-left: 8px"
                >{{ row._count }} 项</el-tag
              >
            </template>
            <span v-else style="padding-left: 16px">{{ row.code }}</span>
          </template>
          <template #name="{ row }">
            <span v-if="!row._isGroup">{{ row.name }}</span>
          </template>
          <template #action="{ row }">
            <span v-if="!row._isGroup">{{ row.action }}</span>
          </template>
          <template #description="{ row }">
            <span v-if="!row._isGroup">{{ row.description }}</span>
          </template>
          <template #operation="{ row }">
            <template v-if="!row._isGroup">
              <el-button
                v-perms="['permission:update']"
                size="small"
                @click="openEdit(row)"
                >编辑</el-button
              >
              <el-button
                v-perms="['permission:delete']"
                type="danger"
                size="small"
                @click="handleDelete(row)"
                >删除</el-button
              >
            </template>
          </template>
        </pure-table>
      </template>
    </PureTableBar>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="权限码" prop="code" :error="fieldErrors.code">
          <el-input
            v-model="form.code"
            placeholder="如 user:list"
            @input="fieldErrors.code = ''"
          />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="资源" prop="resource">
          <el-input v-model="form.resource" />
        </el-form-item>
        <el-form-item label="操作" prop="action">
          <el-input v-model="form.action" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.group-row-label {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
</style>
