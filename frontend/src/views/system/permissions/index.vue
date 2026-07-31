<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getPermissionList, createPermission, updatePermission, deletePermission } from "@/api/permissions";

const loading = ref(false);
const list = ref<any[]>([]);
const dialogVisible = ref(false);
const dialogTitle = ref("新增权限");

const form = reactive({ id: 0, code: "", name: "", resource: "", action: "", description: "" });

const resourceLabelMap: Record<string, string> = {
  user: "用户管理",
  role: "角色管理",
  menu: "菜单管理",
  permission: "权限管理",
};

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
        .sort((a, b) => a.action.localeCompare(b.action))
        .map((p: any) => ({ ...p, _treeId: `perm:${p.id}` })),
    }));
});

async function load() {
  loading.value = true;
  try {
    const res = await getPermissionList();
    if (res.code === 0) list.value = res.data.items;
  } finally { loading.value = false; }
}

function openCreate() {
  dialogTitle.value = "新增权限";
  Object.assign(form, { id: 0, code: "", name: "", resource: "", action: "", description: "" });
  dialogVisible.value = true;
}

function openEdit(row: any) {
  dialogTitle.value = "编辑权限";
  Object.assign(form, { id: row.id, code: row.code, name: row.name, resource: row.resource, action: row.action, description: row.description ?? "" });
  dialogVisible.value = true;
}

async function handleSubmit() {
  const data: any = { name: form.name, resource: form.resource, action: form.action, description: form.description || null };
  if (form.id) {
    if (form.code !== list.value.find((p: any) => p.id === form.id)?.code) data.code = form.code;
    await updatePermission(form.id, data);
    ElMessage.success("更新成功");
  } else {
    await createPermission({ ...data, code: form.code });
    ElMessage.success("创建成功");
  }
  dialogVisible.value = false;
  load();
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除权限 "${row.name}"？`, "提示", { type: "warning" });
  await deletePermission(row.id);
  ElMessage.success("已删除");
  load();
}

onMounted(load);
</script>

<template>
  <div style="padding: 20px">
    <h2 style="margin-top: 0">权限管理</h2>

    <el-button v-perms="['permission:create']" type="primary" style="margin-bottom: 12px" @click="openCreate">新增权限</el-button>

    <el-table
      v-loading="loading"
      :data="treeData"
      row-key="_treeId"
      border
      stripe
      default-expand-all
      :tree-props="{ children: 'children' }"
    >
      <el-table-column prop="code" label="权限码" min-width="150">
        <template #default="{ row }">
          <template v-if="row._isGroup">
            <span class="group-row-label">{{ row._label }}</span>
            <el-tag size="small" round style="margin-left: 8px">{{ row._count }} 项</el-tag>
          </template>
          <span v-else style="padding-left: 16px">{{ row.code }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称">
        <template #default="{ row }">
          <span v-if="!row._isGroup">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="action" label="操作" width="100">
        <template #default="{ row }">
          <span v-if="!row._isGroup">{{ row.action }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述">
        <template #default="{ row }">
          <span v-if="!row._isGroup">{{ row.description }}</span>
        </template>
      </el-table-column>
      <el-table-column label="管理" width="180" fixed="right">
        <template #default="{ row }">
          <template v-if="!row._isGroup">
            <el-button v-perms="['permission:update']" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button v-perms="['permission:delete']" type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px" destroy-on-close>
      <el-form :model="form" label-width="80px">
        <el-form-item v-if="!form.id" label="权限码" required>
          <el-input v-model="form.code" placeholder="如 user:list" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="资源">
          <el-input v-model="form.resource" />
        </el-form-item>
        <el-form-item label="操作">
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
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

</style>
