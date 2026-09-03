<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus } from "@element-plus/icons-vue";
import type { FormInstance, FormRules } from "element-plus";
import type { PaginationProps } from "@pureadmin/table";
import { PureTableBar } from "@/components/RePureTableBar";
import {
  getUserList,
  getUser,
  createUser,
  updateUser,
  patchUser,
  deleteUser,
  hardDeleteUser
} from "@/api/system/users";
import type {
  UserListItem,
  RoleBrief,
  PostBrief,
  DepartmentTreeNode,
  UserListQuery
} from "@/api/system/types";
import { getRoleList } from "@/api/system/roles";
import { getPostList } from "@/api/system/posts";
import { getDepartmentTree } from "@/api/system/departments";
import { ErrorCode } from "@/constants/error-code";

const loading = ref(false);
const list = ref<UserListItem[]>([]);
const pagination = reactive<PaginationProps>({
  total: 0,
  pageSize: 20,
  currentPage: 1,
  background: true
});
const dialogVisible = ref(false);
const dialogTitle = ref("新增用户");
// 角色下拉选项：编辑时来自单查接口返回的全量角色，新增时现查
const roleOptions = ref<RoleBrief[]>([]);
// 岗位下拉选项：与角色同构（学若依 getInfo 的 posts/postIds 维度），编辑来自详情、新增现查
const postOptions = ref<PostBrief[]>([]);
// 部门树：页面初始化拉一次，左侧筛选面板 + 弹窗 tree-select 共用
const deptTree = ref<DepartmentTreeNode[]>([]);
// 左侧部门树当前选中节点，选中即过滤列表（null = 不过滤，即「全部部门」）
const selectedDeptId = ref<number | null>(null);
const deptTreeRef = ref();

// "active" | "disabled" | "all"
const statusFilter = ref<"active" | "disabled" | "all">("active");

const form = reactive({
  id: 0,
  username: "",
  password: "",
  display_name: "",
  phone: "",
  is_active: true,
  role_ids: [] as number[],
  post_ids: [] as number[],
  department_id: null as number | null
});
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
      trigger: ["blur", "change"]
    }
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    {
      validator: (_rule, value, callback) => {
        if (value && value.length < 6) callback(new Error("密码至少 6 个字符"));
        else callback();
      },
      trigger: "blur"
    }
  ],
  display_name: [{ required: true, message: "请输入显示名", trigger: "blur" }]
});

const columns: TableColumnList = [
  { label: "ID", prop: "id", width: 80 },
  { label: "用户名", prop: "username" },
  { label: "显示名", prop: "display_name" },
  { label: "手机号", prop: "phone" },
  { label: "部门", slot: "department" },
  { label: "角色", slot: "role", width: 220 },
  { label: "状态", slot: "status", width: 100 },
  { label: "创建时间", prop: "created_at", width: 180 },
  { label: "操作", slot: "operation", width: 220, fixed: "right" }
];

async function onSearch() {
  loading.value = true;
  try {
    const params: UserListQuery = {
      page: pagination.currentPage,
      page_size: pagination.pageSize
    };
    if (statusFilter.value === "active") params.is_active = true;
    else if (statusFilter.value === "disabled") params.is_active = false;
    // "all" 不传 is_active，查全部
    // 左侧部门树点选后按 dept_id 精确筛选
    if (selectedDeptId.value != null) params.dept_id = selectedDeptId.value;
    const res = await getUserList(params);
    if (res.code === 0) {
      list.value = res.data?.items ?? [];
      pagination.total = res.data?.total ?? 0;
    } else {
      ElMessage.error(res.message || "加载用户列表失败");
    }
  } finally {
    loading.value = false;
  }
}

function handleSizeChange(val: number) {
  pagination.pageSize = val;
  pagination.currentPage = 1;
  onSearch();
}
function handleCurrentChange(val: number) {
  pagination.currentPage = val;
  onSearch();
}

function onStatusChange(val: "active" | "disabled" | "all") {
  statusFilter.value = val;
  pagination.currentPage = 1;
  onSearch();
}

// 部门树整棵拉一次（来源 GET /departments/tree，学 RuoYi 的 treeselect），
// 左侧筛选面板与弹窗选择共用这份嵌套树，前端无需再拼
async function loadDeptTree() {
  try {
    const res = await getDepartmentTree();
    if (res.code === 0) deptTree.value = res.data ?? [];
  } catch {
    /* 部门树加载失败，保持空树，不影响列表 */
  }
}

// 角色下拉选项现查。必须带 page_size=100：角色列表分页默认每页 20，
// 不带参只拿回第一页，角色多了下拉会被截断
async function loadRoleOptions() {
  try {
    const res = await getRoleList({ page_size: 100 });
    if (res.code === 0) roleOptions.value = res.data?.items ?? [];
  } catch {
    /* 角色下拉加载失败，保持空，用户可重试 */
  }
}

// 岗位下拉选项现查（新增入口用；编辑直接复用详情返回的全量岗位 detail.posts）
async function loadPostOptions() {
  try {
    const res = await getPostList({ page_size: 100 });
    if (res.code === 0) postOptions.value = res.data?.items ?? [];
  } catch {
    /* 岗位下拉加载失败，保持空，用户可重试 */
  }
}

// 左侧部门树：点某个节点 → 按 dept_id 筛「该部门 + 全部子孙部门」的用户（学 RuoYi find_in_set）
function handleDeptNodeClick(data: DepartmentTreeNode) {
  selectedDeptId.value = data.id;
  pagination.currentPage = 1;
  onSearch();
}

// 点「全部部门」→ 清筛选 + 去掉树高亮，回到全量列表
function resetDeptFilter() {
  selectedDeptId.value = null;
  deptTreeRef.value?.setCurrentKey(null);
  pagination.currentPage = 1;
  onSearch();
}

async function openCreate() {
  dialogTitle.value = "新增用户";
  Object.assign(form, {
    id: 0,
    username: "",
    password: "",
    display_name: "",
    phone: "",
    is_active: true,
    role_ids: [],
    post_ids: [],
    department_id: null
  });
  fieldErrors.username = "";
  dialogVisible.value = true;
  await Promise.all([loadRoleOptions(), loadPostOptions()]);
}

async function openEdit(row: UserListItem) {
  dialogTitle.value = "编辑用户";
  const res = await getUser(row.id);
  if (res.code !== 0) {
    ElMessage.error(res.message || "加载用户详情失败");
    return;
  }
  const detail = res.data!;
  Object.assign(form, {
    id: detail.user.id,
    username: detail.user.username,
    password: "",
    display_name: detail.user.display_name,
    phone: detail.user.phone ?? "",
    is_active: detail.user.is_active,
    role_ids: detail.role_ids ?? [],
    post_ids: detail.post_ids ?? [],
    department_id: detail.user.department_id ?? null
  });
  roleOptions.value = detail.roles;
  postOptions.value = detail.posts ?? [];
  // 部门树不进用户详情：弹窗 tree-select 直接复用页面初始化拉好的 deptTree
  fieldErrors.username = "";
  dialogVisible.value = true;
}

/** 保存失败：唯一性冲突（用户名已存在）标红字段，其余走 toast */
function onSaveFail(res: any, fallback: string) {
  if (res.code === ErrorCode.USERNAME_ALREADY_EXISTS) {
    fieldErrors.username = res.message || "用户名已存在";
    return;
  } else if (res.code === ErrorCode.VALIDATION_ERROR) {
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
    if (form.id) {
      const res = await updateUser(form.id, {
        username: form.username.trim(),
        display_name: form.display_name,
        phone: form.phone || null,
        role_ids: form.role_ids,
        post_ids: form.post_ids,
        department_id: form.department_id ?? null,
        is_active: form.is_active
      });
      if (res.code !== 0) {
        onSaveFail(res, "更新失败");
        return;
      }
      ElMessage.success("更新成功");
    } else {
      const res = await createUser({
        username: form.username,
        password: form.password,
        display_name: form.display_name,
        phone: form.phone || null,
        role_ids: form.role_ids,
        post_ids: form.post_ids,
        department_id: form.department_id ?? null
      });
      if (res.code !== 0) {
        onSaveFail(res, "创建失败");
        return;
      }
      ElMessage.success("创建成功");
    }
    dialogVisible.value = false;
    onSearch();
  } catch (err: any) {
    if (err?.message) {
      ElMessage.error(err.message);
    }
  }
}

async function handleDisable(row: UserListItem) {
  try {
    const action = row.is_active ? "禁用" : "启用";
    await ElMessageBox.confirm(
      `确认${action}用户 "${row.username}"？`,
      "提示",
      { type: "warning" }
    );
    if (row.is_active) {
      // 禁用：调用 DELETE（软删除）
      const res = await deleteUser(row.id);
      if (res.code === 0) {
        ElMessage.success(res.message || "已禁用");
        onSearch();
      } else {
        ElMessage.error(res.message || "操作失败");
      }
    } else {
      // 重新启用：调用 PATCH
      const res = await patchUser(row.id, { is_active: true });
      if (res.code === 0) {
        ElMessage.success("已启用");
        onSearch();
      } else {
        ElMessage.error(res.message || "操作失败");
      }
    }
  } catch {
    /* 用户取消或拦截器已弹 toast */
  }
}

async function handleHardDelete(row: UserListItem) {
  try {
    await ElMessageBox.confirm(
      `确认彻底删除用户 "${row.username}"？此操作不可恢复！`,
      "危险操作",
      { type: "error", confirmButtonText: "彻底删除", cancelButtonText: "取消" }
    );
    const res = await hardDeleteUser(row.id);
    if (res.code === 0) {
      ElMessage.success(res.message || "已彻底删除");
      onSearch();
    } else {
      ElMessage.error(res.message || "删除失败");
    }
  } catch {
    /* 用户取消或拦截器已弹 toast */
  }
}

onMounted(() => {
  loadDeptTree();
  onSearch();
});
</script>

<template>
  <div class="users-page">
    <!-- 左侧部门树面板：点节点按部门筛用户（学 RuoYi 左树右表布局）。
         树的来源是 GET /departments/tree，与弹窗的部门选择共用同一份嵌套数据 -->
    <aside class="dept-panel">
      <div class="dept-panel__header">
        <span>部门</span>
        <el-button link type="primary" size="small" @click="resetDeptFilter">
          全部部门
        </el-button>
      </div>
      <el-tree
        ref="deptTreeRef"
        :data="deptTree"
        node-key="id"
        highlight-current
        default-expand-all
        :expand-on-click-node="false"
        :props="{ label: 'name', children: 'children' }"
        @node-click="handleDeptNodeClick"
      />
    </aside>

    <!-- 右侧表格：flex:1 撑满剩余宽度，min-width:0 防止固定宽表格把父容器撑爆 -->
    <section class="table-panel">
      <PureTableBar :columns="columns" @refresh="onSearch">
        <template #title>
          <el-button
            v-perms="['user:create']"
            type="primary"
            :icon="Plus"
            @click="openCreate"
            >新增用户</el-button
          >
        </template>
        <template #buttons>
          <el-radio-group
            v-model="statusFilter"
            size="small"
            @change="onStatusChange"
          >
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
            :header-cell-style="{
              background: 'var(--el-fill-color-light)',
              color: 'var(--el-text-color-primary)'
            }"
            @page-size-change="handleSizeChange"
            @page-current-change="handleCurrentChange"
          >
            <template #department="{ row }">
              {{ row.department?.name ?? "—" }}
            </template>
            <template #role="{ row }">
              <template v-if="row.roles?.length">
                <el-tag
                  v-for="r in row.roles"
                  :key="r.id"
                  size="small"
                  style="margin: 0 6px 4px 0"
                  >{{ r.name }}</el-tag
                >
              </template>
              <span v-else>—</span>
            </template>
            <template #status="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'danger'">{{
                row.is_active ? "启用" : "禁用"
              }}</el-tag>
            </template>
            <template #operation="{ row }">
              <template v-if="row.username !== 'admin'">
                <el-button
                  v-perms="['user:update']"
                  size="small"
                  @click="openEdit(row)"
                  >编辑</el-button
                >
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
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item
          label="用户名"
          prop="username"
          :error="fieldErrors.username"
        >
          <el-input
            v-model="form.username"
            @input="fieldErrors.username = ''"
          />
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
          <!-- 学 RuoYi：部门选项不打包进 getUser，用页面初始化拉好的 deptTree 现渲。
               node-key="id" → v-model 绑的就是部门 id；check-strictly 允许选父节点 -->
          <el-tree-select
            v-model="form.department_id"
            :data="deptTree"
            node-key="id"
            check-strictly
            :props="{ label: 'name', children: 'children' }"
            :render-after-expand="false"
            filterable
            clearable
            placeholder="请选择部门"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select
            v-model="form.role_ids"
            multiple
            placeholder="请选择角色"
          >
            <el-option
              v-for="r in roleOptions"
              :key="r.id"
              :label="r.name"
              :value="r.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="岗位">
          <!-- 与角色维度正交（学若依 getInfo 的 posts/postIds） -->
          <el-select
            v-model="form.post_ids"
            multiple
            placeholder="请选择岗位"
          >
            <el-option
              v-for="p in postOptions"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.id" label="状态">
          <el-switch
            v-model="form.is_active"
            active-text="启用"
            inactive-text="禁用"
          />
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
/* 左树右表：左侧部门树固定 220px，右侧表格弹性占满剩余 */
.users-page {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.dept-panel {
  flex-shrink: 0;
  width: 220px;
  margin-top: 4px;
  padding: 10px 6px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-bg-color);
}

.dept-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 6px;
  font-size: 14px;
  font-weight: 600;
}

.dept-panel :deep(.el-tree) {
  padding: 4px 0;
}

.table-panel {
  flex: 1;
  min-width: 0;
}
</style>
