<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { getUserList, createUser, updateUser, deleteUser } from "@/api/users";
import { getRoleList } from "@/api/roles";
import { getDepartmentList } from "@/api/departments";

const loading = ref(false);
const list = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const dialogVisible = ref(false);
const dialogTitle = ref("新增用户");
const roleOptions = ref<any[]>([]);
const deptOptions = ref<any[]>([]);

const form = reactive({ id: 0, username: "", password: "", display_name: "", phone: "", is_active: true, role_ids: [] as number[], department_id: null as number | null });
const formRef = ref<FormInstance>();

const rules = reactive<FormRules>({
  username: [
    { required: true, message: "请输入用户名", trigger: "blur" },
    { min: 3, message: "用户名至少 3 个字符", trigger: "blur" },
    {
      validator: (_rule, value, callback) => {
        if (value !== value.trim()) {
          callback(new Error("用户名不允许首尾包含空格"));
        } else {
          callback();
        }
      },
      trigger: ["blur", "change"],
    },
  ],
  password: [
    { validator: (_rule, value, callback) => {
      if (!form.id && !value) callback(new Error("请输入密码"));
      else if (value && value.length < 6) callback(new Error("密码至少 6 个字符"));
      else callback();
    }, trigger: "blur" },
  ],
  display_name: [
    { required: true, message: "请输入显示名", trigger: "blur" },
  ],
});

async function load() {
  loading.value = true;
  try {
    const res = await getUserList({ page: page.value, page_size: pageSize.value });
    if (res.code === 0) { list.value = res.data.items; total.value = res.data.total; }
  } finally { loading.value = false; }
}

async function loadRoles() {
  try {
    const [rRes, dRes] = await Promise.all([getRoleList(), getDepartmentList()]);
    if (rRes.code === 0) roleOptions.value = rRes.data.items;
    if (dRes.code === 0) deptOptions.value = dRes.data.items;
  } catch { /* 无权限或网络错误则跳过 */ }
}

function openCreate() {
  dialogTitle.value = "新增用户";
  Object.assign(form, { id: 0, username: "", password: "", display_name: "", phone: "", is_active: true, role_ids: [], department_id: null });
  dialogVisible.value = true;
}

function openEdit(row: any) {
  dialogTitle.value = "编辑用户";
  Object.assign(form, { id: row.id, username: row.username, password: "", display_name: row.display_name, phone: row.phone ?? "", is_active: row.is_active, role_ids: row.roles?.map((r: any) => r.id) ?? [], department_id: row.department_id ?? null });
  dialogVisible.value = true;
}

async function handleSubmit() {
  if (!formRef.value) return;
  await formRef.value.validate();
  const data: any = { display_name: form.display_name, phone: form.phone || null, role_ids: form.role_ids, department_id: form.department_id, is_active: form.is_active };
  if (form.id) {
    data.username = form.username.trim();
    const res = await updateUser(form.id, data);
    if (res.code !== 0) { ElMessage.error(res.message || "更新失败"); return; }
    ElMessage.success("更新成功");
  } else {
    data.username = form.username.trim(); data.password = form.password;
    const res = await createUser(data);
    if (res.code !== 0) { ElMessage.error(res.message || "创建失败"); return; }
    ElMessage.success("创建成功");
  }
  dialogVisible.value = false;
  load();
}

async function handleDelete(id: number, username: string) {
  try {
    await ElMessageBox.confirm(`确认禁用用户 "${username}"？`, "提示", { type: "warning" });
    await deleteUser(id);
    ElMessage.success("已禁用");
    load();
  } catch { /* 用户取消或拦截器已弹 toast */ }
}

function handlePageChange(p: number) { page.value = p; load(); }
onMounted(() => { load(); loadRoles(); });
</script>

<template>
  <div>
    <el-button v-perms="['user:create']" type="primary" style="margin-bottom: 12px" @click="openCreate">新增用户</el-button>

    <el-table v-loading="loading" :data="list" border stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="display_name" label="显示名" />
      <el-table-column prop="phone" label="手机号" />
      <el-table-column label="部门">
        <template #default="{ row }">
          {{ deptOptions.find((d: any) => d.id === row.department_id)?.name ?? "—" }}
        </template>
      </el-table-column>
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
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item v-if="!form.id" label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="显示名" prop="display_name">
          <el-input v-model="form.display_name" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="form.department_id" clearable placeholder="请选择部门">
            <el-option v-for="d in deptOptions" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
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
