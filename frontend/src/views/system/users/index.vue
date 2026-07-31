<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getUserList, createUser, updateUser, deleteUser } from "@/api/users";
import { getRoleList } from "@/api/roles";

const loading = ref(false);
const list = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const dialogVisible = ref(false);
const dialogTitle = ref("新增用户");
const roleOptions = ref<any[]>([]);

const form = reactive({ id: 0, username: "", password: "", display_name: "", phone: "", is_active: true, role_ids: [] as number[] });
const formRef = ref();

async function load() {
  loading.value = true;
  try {
    const res = await getUserList({ page: page.value, page_size: pageSize.value });
    if (res.code === 0) { list.value = res.data.items; total.value = res.data.total; }
  } finally { loading.value = false; }
}

async function loadRoles() {
  const res = await getRoleList();
  if (res.code === 0) roleOptions.value = res.data.items;
}

function openCreate() {
  dialogTitle.value = "新增用户";
  Object.assign(form, { id: 0, username: "", password: "", display_name: "", phone: "", is_active: true, role_ids: [] });
  dialogVisible.value = true;
}

function openEdit(row: any) {
  dialogTitle.value = "编辑用户";
  Object.assign(form, { id: row.id, username: row.username, password: "", display_name: row.display_name, phone: row.phone ?? "", is_active: row.is_active, role_ids: row.roles?.map((r: any) => r.id) ?? [] });
  dialogVisible.value = true;
}

async function handleSubmit() {
  const data: any = { display_name: form.display_name, phone: form.phone || null, role_ids: form.role_ids };
  if (form.id) {
    await updateUser(form.id, data);
    ElMessage.success("更新成功");
  } else {
    data.username = form.username; data.password = form.password;
    await createUser(data);
    ElMessage.success("创建成功");
  }
  dialogVisible.value = false;
  load();
}

async function handleDelete(id: number, username: string) {
  await ElMessageBox.confirm(`确认禁用用户 "${username}"？`, "提示", { type: "warning" });
  await deleteUser(id);
  ElMessage.success("已禁用");
  load();
}

function handlePageChange(p: number) { page.value = p; load(); }
onMounted(() => { load(); loadRoles(); });
</script>

<template>
  <div>
    <el-button type="primary" style="margin-bottom: 12px" @click="openCreate">新增用户</el-button>

    <el-table v-loading="loading" :data="list" border stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="display_name" label="显示名" />
      <el-table-column prop="phone" label="手机号" />
      <el-table-column prop="is_active" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'">{{ row.is_active ? "启用" : "禁用" }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <template v-if="row.username !== 'admin'">
            <el-button v-perms="['user:update']" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button v-perms="['user:delete']" type="danger" size="small" :disabled="!row.is_active" @click="handleDelete(row.id, row.username)">禁用</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination style="margin-top: 16px; justify-content: flex-end" background layout="total, prev, pager, next"
      :total="total" :page-size="pageSize" :current-page="page" @current-change="handlePageChange" />

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px" destroy-on-close>
      <el-form ref="formRef" :model="form" label-width="80px">
        <el-form-item v-if="!form.id" label="用户名" required>
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item v-if="!form.id" label="密码" required>
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="显示名">
          <el-input v-model="form.display_name" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role_ids" multiple placeholder="请选择角色">
            <el-option v-for="r in roleOptions" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.id" label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>
