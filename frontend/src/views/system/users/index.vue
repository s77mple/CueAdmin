<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus } from "@element-plus/icons-vue";
import type { FormInstance, FormRules } from "element-plus";
import type { PaginationProps } from "@pureadmin/table";
import { PureTableBar } from "@/components/RePureTableBar";
import { getUserList, createUser, updateUser, patchUser, deleteUser, hardDeleteUser } from "@/api/users";
import { ErrorCode } from "@/constants/error-code";
import { useDictStoreHook } from "@/store/modules/dictionary";

const loading = ref(false);
const list = ref<any[]>([]);
const pagination = reactive<PaginationProps>({ total: 0, pageSize: 20, currentPage: 1, background: true });
const dialogVisible = ref(false);
const dialogTitle = ref("新增用户");
const dictStore = useDictStoreHook();

// "active" | "disabled" | "all"
const statusFilter = ref<"active" | "disabled" | "all">("active");

const form = reactive({ id: 0, username: "", password: "", display_name: "", phone: "", is_active: true, role_ids: [] as number[], department_id: null as number | null });
const formRef = ref<FormInstance>();

// 服务端唯一性冲突（12002 用户名已存在）→ 字段级标红
const fieldErrors = reactive({ username: "" });

const rules = reactive<FormRules>({
  username: [
    { required: true, message: "请输入用户名", trigger: "blur" },
    { min: 3, message: "用户名至少 3 个字符", trigger: "blur" },
    // 首尾空格校验已注释：后端 field_validator 会拦截，前端不再重复校验
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
    { required: true, message: "请输入密码", trigger: "blur" },
    { validator: (_rule, value, callback) => {
      if (value && value.length < 6) callback(new Error("密码至少 6 个字符"));
      else callback();
    }, trigger: "blur" },
  ],
  display_name: [
    { required: true, message: "请输入显示名", trigger: "blur" },
  ],
});

const columns: TableColumnList = [
  { label: "ID", prop: "id", width: 80 },
  { label: "用户名", prop: "username" },
  { label: "显示名", prop: "display_name" },
  { label: "手机号", prop: "phone" },
  { label: "部门", slot: "department" },
  { label: "状态", slot: "status", width: 100 },
  { label: "创建时间", prop: "created_at", width: 180 },
  { label: "操作", slot: "operation", width: 220, fixed: "right" },
];

async function onSearch() {
  loading.value = true;
  try {
    const params: any = { page: pagination.currentPage, page_size: pagination.pageSize };
    if (statusFilter.value === "active") params.is_active = true;
    else if (statusFilter.value === "disabled") params.is_active = false;
    // "all" 不传 is_active，查全部
    const res = await getUserList(params);
    if (res.code === 0) { list.value = res.data?.items ?? []; pagination.total = res.data?.total ?? 0; }
    else { ElMessage.error(res.message || "加载用户列表失败"); }
  } finally { loading.value = false; }
}

function handleSizeChange(val: number) { pagination.pageSize = val; pagination.currentPage = 1; onSearch(); }
function handleCurrentChange(val: number) { pagination.currentPage = val; onSearch(); }

function onStatusChange(val: "active" | "disabled" | "all") {
  statusFilter.value = val;
  pagination.currentPage = 1;
  onSearch();
}

function openCreate() {
  dialogTitle.value = "新增用户";
  Object.assign(form, { id: 0, username: "", password: "", display_name: "", phone: "", is_active: true, role_ids: [], department_id: null });
  fieldErrors.username = "";
  dialogVisible.value = true;
}

function openEdit(row: any) {
  dialogTitle.value = "编辑用户";
  Object.assign(form, { id: row.id, username: row.username, password: "", display_name: row.display_name, phone: row.phone ?? "", is_active: row.is_active, role_ids: row.roles?.map((r: any) => r.id) ?? [], department_id: row.department_id ?? null });
  fieldErrors.username = "";
  dialogVisible.value = true;
}

/** 保存失败：唯一性冲突（用户名已存在）标红字段，其余走 toast */
function onSaveFail(res: any, fallback: string) {
  if (res.code === ErrorCode.USERNAME_ALREADY_EXISTS) {
    fieldErrors.username = res.message || "用户名已存在";
    return;
  }
  else if (res.code === ErrorCode.VALIDATION_ERROR) {
    ElMessage.error(res.message || "表单验证失败，请检查输入");
    console.log("表单验证失败：", res);
    return;
  }
  ElMessage.error(res.message || fallback);
}

async function handleSubmit() {
  if (!formRef.value) return;
  // 每次提交前清空上次的字段级错误：el-form-item 的 error 是 watch 属性，
  // 同值重复赋值不会触发显示，否则连续提交相同用户名时错误只会出现一次
  fieldErrors.username = "";
  try {
    await formRef.value.validate();
    const data: any = { display_name: form.display_name, phone: form.phone || null, role_ids: form.role_ids, department_id: form.department_id ?? null, is_active: form.is_active };
    if (form.id) {
      data.username = form.username.trim();
      const res = await updateUser(form.id, data);
      if (res.code !== 0) { onSaveFail(res, "更新失败"); return; }
      ElMessage.success("更新成功");
    } else {
      data.username = form.username; data.password = form.password;
      const res = await createUser(data);
      if (res.code !== 0) { onSaveFail(res, "创建失败"); return; }
      ElMessage.success("创建成功");
    }
    dialogVisible.value = false;
    onSearch();
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
      if (res.code === 0) { ElMessage.success(res.message || "已禁用"); onSearch(); }
      else { ElMessage.error(res.message || "操作失败"); }
    } else {
      // 重新启用：调用 PATCH
      const res: any = await patchUser(row.id, { is_active: true });
      if (res.code === 0) { ElMessage.success("已启用"); onSearch(); }
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
    if (res.code === 0) { ElMessage.success(res.message || "已彻底删除"); onSearch(); }
    else { ElMessage.error(res.message || "删除失败"); }
  } catch { /* 用户取消或拦截器已弹 toast */ }
}

onMounted(() => { onSearch(); dictStore.loadAll(); });
</script>

<template>
  <div>
    <PureTableBar :columns="columns" @refresh="onSearch">
      <template #title>
        <el-button v-perms="['user:create']" type="primary" :icon="Plus" @click="openCreate">新增用户</el-button>
      </template>
      <template #buttons>
        <el-radio-group v-model="statusFilter" size="small" @change="onStatusChange">
          <el-radio-button value="active">启用</el-radio-button>
          <el-radio-button value="disabled">已禁用</el-radio-button>
          <el-radio-button value="all">全部</el-radio-button>
        </el-radio-group>
      </template>
      <template v-slot="{ size, dynamicColumns }">
        <pure-table
          row-key="id"
          align-whole="center"
          showOverflowTooltip
          :loading="loading"
          :size="size"
          :data="list"
          :columns="dynamicColumns"
          :pagination="{ ...pagination, size }"
          :header-cell-style="{ background: 'var(--el-fill-color-light)', color: 'var(--el-text-color-primary)' }"
          @page-size-change="handleSizeChange"
          @page-current-change="handleCurrentChange"
        >
          <template #department="{ row }">
            {{ dictStore.departments.find((d: any) => d.id === row.department_id)?.name ?? "—" }}
          </template>
          <template #status="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">{{ row.is_active ? "启用" : "禁用" }}</el-tag>
          </template>
          <template #operation="{ row }">
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
        </pure-table>
      </template>
    </PureTableBar>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username" :error="fieldErrors.username">
          <el-input v-model="form.username" @input="fieldErrors.username = ''" />
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
          <el-select v-model="form.department_id" clearable placeholder="请选择部门"
            @visible-change="visible => { if (visible) dictStore.loadAll(true) }">
            <el-option v-for="d in dictStore.departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role_ids" multiple placeholder="请选择角色"
            @visible-change="visible => { if (visible) dictStore.loadAll(true) }">
            <el-option v-for="r in dictStore.roles" :key="r.id" :label="r.name" :value="r.id" />
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
