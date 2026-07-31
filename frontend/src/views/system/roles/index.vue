<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getRoleList, createRole, updateRole, deleteRole } from "@/api/roles";
import { getPermissionList } from "@/api/permissions";
import { getMenuList } from "@/api/menus";

const loading = ref(false);
const list = ref<any[]>([]);
const dialogVisible = ref(false);
const dialogTitle = ref("新增角色");
const permOptions = ref<any[]>([]);
const menuOptions = ref<any[]>([]);

const form = reactive({ id: 0, code: "", name: "", description: "", permission_codes: [] as string[], menu_ids: [] as number[] });

async function load() {
  loading.value = true;
  try {
    const res = await getRoleList();
    if (res.code === 0) list.value = res.data.items;
  } finally { loading.value = false; }
}

async function loadOptions() {
  const [pRes, mRes] = await Promise.all([getPermissionList(), getMenuList()]);
  if (pRes.code === 0) permOptions.value = pRes.data.items;
  if (mRes.code === 0) menuOptions.value = mRes.data.items;
}

function openCreate() {
  dialogTitle.value = "新增角色";
  Object.assign(form, { id: 0, code: "", name: "", description: "", permission_codes: [], menu_ids: [] });
  dialogVisible.value = true;
}

function openEdit(row: any) {
  dialogTitle.value = "编辑角色";
  Object.assign(form, {
    id: row.id, code: row.code, name: row.name, description: row.description ?? "",
    permission_codes: row.permissions?.map((p: any) => p.code) ?? [],
    menu_ids: row.menus?.map((m: any) => m.id) ?? [],
  });
  dialogVisible.value = true;
}

async function handleSubmit() {
  const data: any = {
    name: form.name,
    description: form.description || null,
    permission_codes: form.permission_codes,
    menu_ids: form.menu_ids,
  };
  if (form.id) {
    await updateRole(form.id, data);
    ElMessage.success("更新成功");
  } else {
    await createRole({ ...data, code: form.code });
    ElMessage.success("创建成功");
  }
  dialogVisible.value = false;
  load();
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除角色 "${row.name}"？`, "提示", { type: "warning" });
  await deleteRole(row.id);
  ElMessage.success("已删除");
  load();
}

onMounted(() => { load(); loadOptions(); });
</script>

<template>
  <div style="padding: 20px">
    <h2>角色管理</h2>
    <el-button type="primary" style="margin-bottom: 12px" @click="openCreate">新增角色</el-button>

    <el-table v-loading="loading" :data="list" border stripe style="margin-top: 16px">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="code" label="编码" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="description" label="描述" />
      <el-table-column label="权限" min-width="200">
        <template #default="{ row }">
          <el-tag v-for="p in row.permissions" :key="p.id" size="small" style="margin: 2px">{{ p.code }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="菜单" min-width="200">
        <template #default="{ row }">
          <el-tag v-for="m in row.menus" :key="m.id" size="small" style="margin: 2px" type="success">{{ m.name }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px" destroy-on-close>
      <el-form :model="form" label-width="80px">
        <el-form-item v-if="!form.id" label="编码" required>
          <el-input v-model="form.code" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
        <el-form-item label="权限">
          <el-select v-model="form.permission_codes" multiple placeholder="选择权限">
            <el-option v-for="p in permOptions" :key="p.code" :label="`${p.code} (${p.name})`" :value="p.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="菜单">
          <el-select v-model="form.menu_ids" multiple placeholder="选择菜单">
            <el-option v-for="m in menuOptions" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>
