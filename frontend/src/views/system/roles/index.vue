<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getRoleList, createRole, updateRole, deleteRole } from "@/api/roles";
import { getPermissionList } from "@/api/permissions";
import { getMenuList } from "@/api/menus";
import { handleTree } from "@/utils/tree";

const loading = ref(false);
const list = ref<any[]>([]);
const dialogVisible = ref(false);
const dialogTitle = ref("新增角色");
const permOptions = ref<any[]>([]);
const menuOptions = ref<any[]>([]);

const form = reactive({ id: 0, code: "", name: "", description: "", permission_codes: [] as string[], menu_ids: [] as number[] });

const menuTreeRef = ref();

const menuTree = computed(() => handleTree(menuOptions.value, "id", "parent_id", "children"));

const resourceLabelMap: Record<string, string> = {
  user: "用户管理",
  role: "角色管理",
  menu: "菜单管理",
  permission: "权限管理",
};

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
  nextTick(() => menuTreeRef.value?.setCheckedKeys([]));
}

function openEdit(row: any) {
  dialogTitle.value = "编辑角色";
  const menuIds: number[] = row.menus?.map((m: any) => m.id) ?? [];
  const permCodes: string[] = row.permissions?.map((p: any) => p.code) ?? [];
  Object.assign(form, {
    id: row.id, code: row.code, name: row.name, description: row.description ?? "",
    permission_codes: permCodes,
    menu_ids: menuIds,
  });
  dialogVisible.value = true;
  nextTick(() => menuTreeRef.value?.setCheckedKeys(menuIds));
}

async function handleSubmit() {
  const checkedMenuIds = (menuTreeRef.value?.getCheckedKeys() as number[]) ?? [];
  const data: any = {
    name: form.name,
    description: form.description || null,
    permission_codes: form.permission_codes,
    menu_ids: checkedMenuIds,
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

function getMenuGroups(menus: any[]) {
  if (!menus?.length) return [];
  const tree = handleTree(menus, "id", "parent_id", "children");
  return tree.map((node: any) => ({
    id: node.id,
    name: node.name,
    code: node.code,
    children: node.children || [],
  }));
}

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

onMounted(() => { load(); loadOptions(); });
</script>

<template>
  <div style="padding: 20px">
    <h2>角色管理</h2>
    <el-button v-perms="['role:create']" type="primary" style="margin-bottom: 12px" @click="openCreate">新增角色</el-button>

    <el-table v-loading="loading" :data="list" border stripe style="margin-top: 16px">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="code" label="编码" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="description" label="描述" />
      <el-table-column label="权限" min-width="160">
        <template #default="{ row }">
          <template v-if="row.is_system">
            <el-tag size="small" class="group-badge" effect="plain">全部权限</el-tag>
          </template>
          <template v-else-if="row.permissions?.length">
            <div class="table-tag-group">
              <el-popover
                v-for="g in getPermGroups(row.permissions)"
                :key="g.resource"
                placement="top"
                :width="240"
                trigger="click"
              >
                <template #reference>
                  <el-tag size="small" class="group-badge" effect="plain">
                    {{ g.label }} ({{ g.count }})
                  </el-tag>
                </template>
                <div class="popover-perm-list">
                  <div class="popover-group-title">{{ g.label }}</div>
                  <div v-for="p in g.permissions" :key="p.id" class="popover-item">
                    <span class="popover-name">{{ p.name }}</span>
                    <code class="popover-code">{{ p.code }}</code>
                  </div>
                </div>
              </el-popover>
            </div>
          </template>
          <span v-else style="color: #c0c4cc">—</span>
        </template>
      </el-table-column>
      <el-table-column label="菜单" min-width="160">
        <template #default="{ row }">
          <template v-if="row.is_system">
            <el-tag size="small" class="group-badge" effect="plain">全部菜单</el-tag>
          </template>
          <template v-else-if="row.menus?.length">
            <div class="table-tag-group">
              <el-popover
                v-for="m in getMenuGroups(row.menus)"
                :key="m.id"
                placement="top"
                :width="220"
                trigger="click"
              >
                <template #reference>
                  <el-tag size="small" class="group-badge" effect="plain">
                    {{ m.name }}<template v-if="m.children.length">(+{{ m.children.length }})</template>
                  </el-tag>
                </template>
                <div class="popover-perm-list">
                  <div class="popover-group-title">{{ m.name }}</div>
                  <div class="popover-item">
                    <code class="popover-code">{{ m.code }}</code>
                  </div>
                  <template v-if="m.children.length">
                    <div class="popover-group-title" style="margin-top: 8px">子菜单</div>
                    <div v-for="c in m.children" :key="c.id" class="popover-item" style="padding-left: 12px">
                      <span class="popover-name">└ {{ c.name }}</span>
                      <code class="popover-code">{{ c.code }}</code>
                    </div>
                  </template>
                </div>
              </el-popover>
            </div>
          </template>
          <span v-else style="color: #c0c4cc">—</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button v-if="!row.is_system" v-perms="['role:update']" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="!row.is_system" v-perms="['role:delete']" type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="750px" destroy-on-close>
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
