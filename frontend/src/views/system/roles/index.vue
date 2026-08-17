<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus } from "@element-plus/icons-vue";
import type { FormInstance, FormRules } from "element-plus";
import type { PaginationProps } from "@pureadmin/table";
import { PureTableBar } from "@/components/RePureTableBar";
import { getRoleList, createRole, updateRole, deleteRole } from "@/api/roles";
import { getPermissionList } from "@/api/permissions";
import { getMenuList } from "@/api/menus";
import { handleTree } from "@/utils/tree";
import { ErrorCode } from "@/constants/error-code";

const loading = ref(false);
const list = ref<any[]>([]);
const pagination = reactive<PaginationProps>({ total: 0, pageSize: 20, currentPage: 1, background: true });
const dialogVisible = ref(false);
const dialogTitle = ref("新增角色");
const permOptions = ref<any[]>([]);
const menuOptions = ref<any[]>([]);

const form = reactive({ id: 0, code: "", name: "", description: "", permission_codes: [] as string[], menu_ids: [] as number[] });
const formRef = ref<FormInstance>();

// 服务端唯一性冲突（13002 角色编码已存在）→ 字段级标红
const fieldErrors = reactive({ code: "" });

// 页面级单一 popover（virtual-ref 锚定被点击的标签）：表格单元格内不再渲染 el-popover，
// 避免折叠侧边栏导致列宽重算时 ElTableBody 无限递归更新（见 columns 注释）
const groupDetail = reactive({
  visible: false,
  ref: null as HTMLElement | null,
  kind: "perm" as "perm" | "menu",
  title: "",
  permissions: [] as any[],
  menu: null as any,
});

function openPermDetail(group: any, e: MouseEvent) {
  groupDetail.kind = "perm";
  groupDetail.title = group.label;
  groupDetail.permissions = group.permissions;
  groupDetail.ref = e.currentTarget as HTMLElement;
  groupDetail.visible = true;
}

function openMenuDetail(m: any, e: MouseEvent) {
  groupDetail.kind = "menu";
  groupDetail.title = m.name;
  groupDetail.menu = m;
  groupDetail.ref = e.currentTarget as HTMLElement;
  groupDetail.visible = true;
}

const rules: FormRules = {
  code: [{ required: true, message: "请输入角色编码", trigger: "blur" }],
  name: [{ required: true, message: "请输入角色名称", trigger: "blur" }],
};

const menuTreeRef = ref();

const menuTree = computed(() => handleTree(menuOptions.value, "id", "parent_id", "children"));

const resourceLabelMap: Record<string, string> = {
  user: "用户管理",
  role: "角色管理",
  menu: "菜单管理",
  permission: "权限管理",
  department: "部门管理",
};

const columns: TableColumnList = [
  { label: "ID", prop: "id", width: 80 },
  { label: "编码", prop: "code" },
  { label: "名称", prop: "name" },
  { label: "描述", prop: "description" },
  { label: "权限", slot: "perms", minWidth: 160 },
  { label: "菜单", slot: "menus", minWidth: 160 },
  { label: "操作", slot: "operation", width: 180, fixed: "right" },
];

const permissionGroups = computed(() => {
  const groups: Record<string, any[]> = {};
  for (const p of permOptions.value) {
    const r = p.resource || "other";
    if (!groups[r]) groups[r] = [];
    groups[r].push(p);
  }
  return Object.entries(groups).map(([resource, perms]) => ({
    resource,
    label: resourceLabelMap[resource] || resource,
    permissions: perms,
  }));
});

async function onSearch() {
  loading.value = true;
  try {
    const res = await getRoleList({ page: pagination.currentPage, page_size: pagination.pageSize });
    if (res.code === 0) { list.value = res.data?.items ?? []; pagination.total = res.data?.total ?? 0; }
    else ElMessage.error(res.message || "加载角色列表失败");
  } finally { loading.value = false; }
}

function handleSizeChange(val: number) { pagination.pageSize = val; pagination.currentPage = 1; onSearch(); }
function handleCurrentChange(val: number) { pagination.currentPage = val; onSearch(); }

// 懒加载：首次打开弹窗时才请求，之后复用缓存
const optionsLoaded = ref(false);

async function loadOptions() {
  if (optionsLoaded.value) return;
  try {
    const [pRes, mRes] = await Promise.all([getPermissionList(), getMenuList()]);
    if (pRes.code === 0) permOptions.value = pRes.data?.items ?? [];
    else ElMessage.warning("权限数据加载失败");
    if (mRes.code === 0) menuOptions.value = mRes.data?.items ?? [];
    else ElMessage.warning("菜单数据加载失败");
    optionsLoaded.value = true;
  } catch {
    ElMessage.warning("加载选项数据失败，请检查网络连接");
  }
}

async function openCreate() {
  dialogTitle.value = "新增角色";
  Object.assign(form, { id: 0, code: "", name: "", description: "", permission_codes: [], menu_ids: [] });
  fieldErrors.code = "";
  dialogVisible.value = true;
  await loadOptions();
  nextTick(() => menuTreeRef.value?.setCheckedKeys([]));
}

async function openEdit(row: any) {
  dialogTitle.value = "编辑角色";
  const menuIds: number[] = row.menus?.map((m: any) => m.id) ?? [];
  const permCodes: string[] = row.permissions?.map((p: any) => p.code) ?? [];
  Object.assign(form, {
    id: row.id, code: row.code, name: row.name, description: row.description ?? "",
    permission_codes: permCodes,
    menu_ids: menuIds,
  });
  fieldErrors.code = "";
  dialogVisible.value = true;
  await loadOptions();
  nextTick(() => menuTreeRef.value?.setCheckedKeys(menuIds));
}

async function handleSubmit() {
  if (!formRef.value) return;
  // 每次提交前清空字段级错误：el-form-item 的 error 是 watch 属性，
  // 同值重复赋值不会触发显示，否则连续提交相同编码时错误只会出现一次
  fieldErrors.code = "";
  try {
    await formRef.value.validate();
    const checkedMenuIds = (menuTreeRef.value?.getCheckedKeys() as number[]) ?? [];
    const data: any = {
      name: form.name,
      description: form.description || null,
      permission_codes: form.permission_codes,
      menu_ids: checkedMenuIds,
    };
    if (form.id) {
      const res: any = await updateRole(form.id, data);
      if (res.code !== 0) { ElMessage.error(res.message || "更新失败"); return; }
      ElMessage.success("更新成功");
    } else {
      const res: any = await createRole({ ...data, code: form.code });
      if (res.code !== 0) {
        if (res.code === ErrorCode.ROLE_CODE_EXISTS) {
          fieldErrors.code = res.message || "角色编码已存在";
          return;
        }
        ElMessage.error(res.message || "创建失败");
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

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除角色 "${row.name}"？`, "提示", { type: "warning" });
    const res: any = await deleteRole(row.id);
    if (res.code === 0) { ElMessage.success(res.message || "已删除"); onSearch(); }
    else { ElMessage.error(res.message || "删除失败"); }
  } catch { /* 用户取消或拦截器已弹 toast */ }
}

function getPermGroups(permissions: any[]) {
  if (!permissions?.length) return [];
  const groups: Record<string, any[]> = {};
  for (const p of permissions) {
    const r = p.resource || p.code?.split(":")[0] || "other";
    if (!groups[r]) groups[r] = [];
    groups[r].push(p);
  }
  return Object.entries(groups).map(([resource, perms]) => ({
    resource,
    label: resourceLabelMap[resource] || resource,
    count: perms.length,
    permissions: perms,
  }));
}

// 与 departments/menus 页一致：树在 computed 里预构建，模板只做读取。
// handleTree 会原地给节点挂 children，因此建树前先浅克隆一层，避免改写表格响应式行数据，
// 否则渲染期改动数据会被模板依赖捕获，导致 ElTableBody 无限递归更新。
function buildMenuGroups(menus: any[]) {
  if (!menus?.length) return [];
  const tree = handleTree(
    menus.map(m => ({ ...m, children: undefined })),
    "id",
    "parent_id",
    "children"
  );
  return tree.map((node: any) => ({
    id: node.id,
    name: node.name,
    code: node.code,
    children: node.children || []
  }));
}

// 每个角色的菜单分组标签，随列表变化一次性预计算（不在单元格渲染期重复建树）
const menuGroupsByRole = computed(() => {
  const map: Record<number, any[]> = {};
  for (const row of list.value) {
    if (row.menus?.length) map[row.id] = buildMenuGroups(row.menus);
  }
  return map;
});

function isGroupAllChecked(resource: string): boolean {
  const group = permissionGroups.value.find(g => g.resource === resource);
  if (!group) return false;
  return group.permissions.every((p: any) => form.permission_codes.includes(p.code));
}

function isGroupIndeterminate(resource: string): boolean {
  const group = permissionGroups.value.find(g => g.resource === resource);
  if (!group) return false;
  const checked = group.permissions.filter((p: any) => form.permission_codes.includes(p.code));
  return checked.length > 0 && checked.length < group.permissions.length;
}

function toggleGroup(resource: string) {
  const group = permissionGroups.value.find(g => g.resource === resource);
  if (!group) return;
  const codes = group.permissions.map((p: any) => p.code);
  if (isGroupAllChecked(resource)) {
    form.permission_codes = form.permission_codes.filter(c => !codes.includes(c));
  } else {
    form.permission_codes = [...new Set([...form.permission_codes, ...codes])];
  }
}

onMounted(() => { onSearch(); });
</script>

<template>
  <div>
    <PureTableBar :columns="columns" @refresh="onSearch">
      <template #title>
        <el-button v-perms="['role:create']" type="primary" :icon="Plus" @click="openCreate">新增角色</el-button>
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
          <template #perms="{ row }">
            <template v-if="row.is_system">
              <el-tag size="small" class="group-badge" effect="plain">全部权限</el-tag>
            </template>
            <template v-else-if="row.permissions?.length">
              <div class="table-tag-group">
                <el-tag
                  v-for="g in getPermGroups(row.permissions)"
                  :key="g.resource"
                  size="small"
                  class="group-badge"
                  effect="plain"
                  @click="openPermDetail(g, $event)"
                >
                  {{ g.label }} ({{ g.count }})
                </el-tag>
              </div>
            </template>
            <span v-else style="color: #c0c4cc">—</span>
          </template>
          <template #menus="{ row }">
            <template v-if="row.is_system">
              <el-tag size="small" class="group-badge" effect="plain">全部菜单</el-tag>
            </template>
            <template v-else-if="row.menus?.length">
              <div class="table-tag-group">
                <el-tag
                  v-for="m in menuGroupsByRole[row.id] || []"
                  :key="m.id"
                  size="small"
                  class="group-badge"
                  effect="plain"
                  @click="openMenuDetail(m, $event)"
                >
                  {{ m.name }}<template v-if="m.children.length">(+{{ m.children.length }})</template>
                </el-tag>
              </div>
            </template>
            <span v-else style="color: #c0c4cc">—</span>
          </template>
          <template #operation="{ row }">
            <el-button v-if="!row.is_system" v-perms="['role:update']" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="!row.is_system" v-perms="['role:delete']" type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </pure-table>
      </template>
    </PureTableBar>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="750px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item v-if="!form.id" label="编码" prop="code" :error="fieldErrors.code">
          <el-input v-model="form.code" @input="fieldErrors.code = ''" />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
        <el-form-item label="权限">
          <div class="perm-group-list">
            <div v-for="group in permissionGroups" :key="group.resource" class="perm-group-card">
              <div class="perm-group-title">
                <el-checkbox
                  :model-value="isGroupAllChecked(group.resource)"
                  :indeterminate="isGroupIndeterminate(group.resource)"
                  @change="toggleGroup(group.resource)"
                >
                  {{ group.label }}
                </el-checkbox>
              </div>
              <div class="perm-group-items">
                <el-checkbox-group v-model="form.permission_codes">
                  <el-checkbox v-for="p in group.permissions" :key="p.code" :label="p.code">
                    {{ p.name }}
                  </el-checkbox>
                </el-checkbox-group>
              </div>
            </div>
          </div>
          <div v-if="permOptions.length === 0" style="color: #999; font-size: 13px">暂无权限数据</div>
        </el-form-item>
        <el-form-item label="菜单">
          <div class="menu-tree-wrapper">
            <el-tree
              ref="menuTreeRef"
              :data="menuTree"
              show-checkbox
              check-strictly
              node-key="id"
              default-expand-all
              :props="{ label: 'name', children: 'children' }"
              empty-text="暂无菜单数据"
            />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 页面级单一 popover：不在表格单元格内渲染 el-popover（折叠重算列宽时会触发 ElTableBody 无限递归），
         点击权限/菜单标签后用 virtual-ref 锚定到该标签打开 -->
    <el-popover
      v-model:visible="groupDetail.visible"
      :virtual-ref="groupDetail.ref"
      virtual-triggering
      placement="top"
      :width="240"
      trigger="click"
    >
      <div class="popover-perm-list">
        <div class="popover-group-title">{{ groupDetail.title }}</div>
        <template v-if="groupDetail.kind === 'perm'">
          <div v-for="p in groupDetail.permissions" :key="p.id" class="popover-item">
            <span class="popover-name">{{ p.name }}</span>
            <code class="popover-code">{{ p.code }}</code>
          </div>
        </template>
        <template v-else>
          <div class="popover-item">
            <code class="popover-code">{{ groupDetail.menu?.code }}</code>
          </div>
          <template v-if="groupDetail.menu?.children?.length">
            <div class="popover-group-title" style="margin-top: 8px">子菜单</div>
            <div v-for="c in groupDetail.menu.children" :key="c.id" class="popover-item" style="padding-left: 12px">
              <span class="popover-name">└ {{ c.name }}</span>
              <code class="popover-code">{{ c.code }}</code>
            </div>
          </template>
        </template>
      </div>
    </el-popover>
  </div>
</template>

<style scoped>
.perm-group-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.perm-group-card {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 12px 16px;
}

.perm-group-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 8px;
  padding-bottom: 0;
  border-bottom: 1px solid #e4e7ed;
}

.perm-group-items {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 20px;
}

.menu-tree-wrapper {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 8px 12px;
  max-height: 350px;
  overflow-y: auto;
  width: 100%;
}

/* 表格内分组标签 */
.table-tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  cursor: pointer;
}

.group-badge {
  cursor: pointer;
  font-weight: 500;
  --el-tag-bg-color: #f5f5f5;
  --el-tag-border-color: #d0d5dd;
  --el-tag-text-color: #344054;
}

/* popover 内权限/菜单列表 */
.popover-perm-list {
  max-height: 260px;
  overflow-y: auto;
}

.popover-group-title {
  font-size: 12px;
  font-weight: 600;
  color: #909399;
  margin: 8px 0 4px;
  padding-bottom: 2px;
  border-bottom: 1px solid #ebeef5;
}

.popover-group-title:first-child {
  margin-top: 0;
}

.popover-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 0;
  font-size: 13px;
}

.popover-code {
  font-size: 12px;
  color: #909399;
  background: #f5f7fa;
  padding: 1px 6px;
  border-radius: 3px;
  font-family: monospace;
}

.popover-name {
  color: #303133;
}

</style>
