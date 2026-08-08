<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { getUserList, createUser, updateUser, patchUser, deleteUser, hardDeleteUser } from "@/api/users";
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

// "active" | "disabled" | "all"
const statusFilter = ref<"active" | "disabled" | "all">("active");

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
    const params: any = { page: page.value, page_size: pageSize.value };
    if (statusFilter.value === "active") params.is_active = true;
    else if (statusFilter.value === "disabled") params.is_active = false;
    // "all" 不传 is_active，查全部
    const res = await getUserList(params);
    if (res.code === 0) { list.value = res.data?.items ?? []; total.value = res.data?.total ?? 0; }
    else { ElMessage.error(res.message || "加载用户列表失败"); }
  } finally { loading.value = false; }
}

function onStatusChange(val: "active" | "disabled" | "all") {
  statusFilter.value = val;
  page.value = 1;
  load();
}

async function loadRoles() {
  try {
    const [rRes, dRes] = await Promise.all([getRoleList(), getDepartmentList()]);
    if (rRes.code === 0) roleOptions.value = rRes.data?.items ?? [];
    if (dRes.code === 0) deptOptions.value = dRes.data?.items ?? [];
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
  try {
    await formRef.value.validate();
    const data: any = { display_name: form.display_name, phone: form.phone || null, role_ids: form.role_ids, department_id: form.department_id ?? null, is_active: form.is_active };
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
  } catch (err: any) {
    if (err?.message) { ElMessage.error(err.message); }
  }
}

async function handleDisable(row: any) {
  try {
    const action = row.is_active ? "禁用" : "启用";
    await ElMessageBox.confirm(`确认${action}用户 "${row.username}"？`, "提示", { type: "warning" });
    if (row.is_active) {
      // 禁用：调用 DELETE（软删除）
      const res: any = await deleteUser(row.id);
      if (res.code === 0) { ElMessage.success(res.message || "已禁用"); load(); }
      else { ElMessage.error(res.message || "操作失败"); }
    } else {
      // 重新启用：调用 PATCH
      const res: any = await patchUser(row.id, { is_active: true });
      if (res.code === 0) { ElMessage.success("已启用"); load(); }
      else { ElMessage.error(res.message || "操作失败"); }
    }
  } catch { /* 用户取消或拦截器已弹 toast */ }
}

async function handleHardDelete(row: any) {
  try {
    await ElMessageBox.confirm(
      `确认彻底删除用户 "${row.username}"？此操作不可恢复！`,
      "危险操作",
      { type: "error", confirmButtonText: "彻底删除", cancelButtonText: "取消" },
    );
    const res: any = await hardDeleteUser(row.id);
    if (res.code === 0) { ElMessage.success(res.message || "已彻底删除"); load(); }
    else { ElMessage.error(res.message || "删除失败"); }
  } catch { /* 用户取消或拦截器已弹 toast */ }
}

function handlePageChange(p: number) { page.value = p; load(); }
onMounted(() => { load(); loadRoles(); });
</script>

<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px">
      <el-button v-perms="['user:create']" type="primary" @click="openCreate">新增用户</el-button>
      <el-radio-group v-model="statusFilter" size="small" @change="onStatusChange">
        <el-radio-button value="active">启用</el-radio-button>
        <el-radio-button value="disabled">已禁用</el-radio-button>
        <el-radio-button value="all">全部</el-radio-button>
      </el-radio-group>
    </div>

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
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <template v-if="row.username !== 'admin'">
            <el-button v-perms="['user:update']" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button
              v-perms="[row.is_active ? 'user:delete' : 'user:update']"
              size="small"
              :type="row.is_active ? 'warning' : 'success'"
              @click="handleDisable(row)"
            >
              {{ row.is_active ? "禁用" : "启用" }}
            </el-button>
            <el-button
              v-if="!row.is_active"
              v-perms="['user:delete']"
              type="danger"
              size="small"
              @click="handleHardDelete(row)"
            >
              删除
            </el-button>
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
