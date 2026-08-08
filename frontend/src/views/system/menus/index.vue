<script setup lang="ts">
import { ref, reactive, onMounted, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { getMenuList, createMenu, updateMenu, deleteMenu } from "@/api/menus";
import { handleTree } from "@/utils/tree";

const loading = ref(false);
const list = ref<any[]>([]);
const dialogVisible = ref(false);
const dialogTitle = ref("新增菜单");

const menuTree = computed(() => handleTree(list.value, "id", "parent_id", "children"));

const form = reactive({ id: 0, code: "", name: "", icon: "", path: "", component: "", parent_id: null as number | null, sort_order: 0, children: [] as any[] });
const formRef = ref<FormInstance>();

const rules: FormRules = {
  code: [{ required: true, message: "请输入菜单编码", trigger: "blur" }],
  name: [{ required: true, message: "请输入菜单名称", trigger: "blur" }],
};

const childDefault = () => ({ code: "", name: "", path: "", component: "", sort_order: 0 });
function addChild() { form.children.push(childDefault()); }
function removeChild(index: number) { form.children.splice(index, 1); }

async function load() {
  loading.value = true;
  try {
    const res = await getMenuList();
    if (res.code === 0) list.value = res.data?.items ?? [];
    else ElMessage.error(res.message || "加载菜单失败");
  } finally { loading.value = false; }
}

function openCreate() {
  dialogTitle.value = "新增菜单";
  Object.assign(form, { id: 0, code: "", name: "", icon: "", path: "", component: "", parent_id: null, sort_order: 0, children: [] });
  dialogVisible.value = true;
}

function openEdit(row: any) {
  dialogTitle.value = "编辑菜单";
  Object.assign(form, { id: row.id, code: row.code, name: row.name, icon: row.icon, path: row.path, component: row.component, parent_id: row.parent_id, sort_order: row.sort_order, children: [] });
  dialogVisible.value = true;
}

async function handleSubmit() {
  if (!formRef.value) return;
  await formRef.value.validate();
  try {
    // 编辑模式：不变
    if (form.id) {
      const data: any = { name: form.name, icon: form.icon || null, path: form.path || null, component: form.component || null, parent_id: form.parent_id ?? null, sort_order: form.sort_order };
      await updateMenu(form.id, data);
      ElMessage.success("更新成功");
      dialogVisible.value = false;
      load();
      return;
    }

  // 新增模式：先校验子菜单，再创建
  // 子菜单字段校验（必须在创建父菜单之前，避免创建孤儿记录）
  for (const child of (form.children ?? [])) {
    if (!child.code?.trim()) { ElMessage.error("子菜单编码不能为空"); return; }
    if (!child.name?.trim()) { ElMessage.error("子菜单名称不能为空"); return; }
  }

  const parentData: any = {
    code: form.code, name: form.name,
    icon: form.icon || null,
    path: form.path || null,
    component: form.component || null,
    parent_id: form.parent_id ?? null, sort_order: form.sort_order,
  };
  const parentRes: any = await createMenu(parentData);
  if (parentRes.code !== 0) {
    ElMessage.error(parentRes.message || "父菜单创建失败");
    return;
  }
  if (!parentRes.data?.id) {
    ElMessage.error("父菜单创建成功但未返回 ID");
    return;
  }
  const parentId = parentRes.data.id;

  let failedCount = 0;
  for (const child of form.children) {
    const childData: any = {
      code: child.code, name: child.name,
      path: child.path || null, component: child.component || null,
      parent_id: parentId, sort_order: child.sort_order ?? 0,
    };
    try {
      const childRes: any = await createMenu(childData);
      if (childRes.code !== 0) failedCount++;
    } catch { failedCount++; }
  }

  const total = form.children.length;
  if (total === 0) ElMessage.success("创建成功");
  else if (failedCount === 0) ElMessage.success(`创建成功，含 ${total} 个子菜单`);
  else ElMessage.warning(`父菜单已创建，但 ${failedCount}/${total} 个子菜单创建失败，请手动补建`);

  dialogVisible.value = false;
  load();
  } catch { /* 拦截器已弹 toast */ }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除菜单 "${row.name}"？`, "提示", { type: "warning" });
    const res: any = await deleteMenu(row.id);
    if (res.code === 0) { ElMessage.success(res.message ?? "已删除"); load(); }
    else { ElMessage.error(res.message || "删除失败"); }
  } catch { /* 用户取消或拦截器已弹 toast */ }
}

// 父级菜单选项（排除自己）
function parentOptions(currentId = 0) {
  return list.value.filter((m: any) => m.id !== currentId).map((m: any) => ({ label: m.name, value: m.id }));
}

onMounted(load);
</script>

<template>
  <div>
    <el-button v-perms="['menu:create']" type="primary" style="margin-bottom: 12px" @click="openCreate">新增菜单</el-button>

    <el-table v-loading="loading" :data="menuTree" border stripe row-key="id" :tree-props="{ children: 'children' }">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="code" label="编码" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="icon" label="图标" width="120" />
      <el-table-column prop="path" label="路径" />
      <el-table-column prop="component" label="组件" />
      <el-table-column prop="sort_order" label="排序" width="80" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button v-perms="['menu:update']" type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button v-perms="['menu:delete']" type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="580px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item v-if="!form.id" label="编码" prop="code">
          <el-input v-model="form.code" />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="form.icon" placeholder="如 fa-solid:users" />
        </el-form-item>
        <el-form-item label="路径">
          <el-input v-model="form.path" placeholder="如 /users" />
        </el-form-item>
        <el-form-item label="组件">
          <el-input v-model="form.component" placeholder="如 system/users/index" />
        </el-form-item>
        <el-form-item label="父菜单">
          <el-select v-model="form.parent_id" clearable placeholder="顶级菜单">
            <el-option v-for="o in parentOptions(form.id)" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>

        <!-- 子菜单（仅新增模式） -->
        <template v-if="!form.id">
          <el-divider content-position="left">
            <span style="font-size: 13px; color: #606266">子菜单</span>
          </el-divider>

          <div
            v-for="(child, idx) in form.children"
            :key="idx"
            style="background: #f5f7fa; border: 1px solid #e4e7ed; border-radius: 6px; padding: 12px 16px; margin-bottom: 8px"
          >
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px">
              <span style="font-size: 13px; font-weight: 600; color: #303133">子菜单 #{{ idx + 1 }}</span>
              <el-button type="danger" size="small" text @click="removeChild(idx)">删除</el-button>
            </div>
            <el-form-item label="编码" style="margin-bottom: 12px">
              <el-input v-model="child.code" placeholder="子菜单编码" />
            </el-form-item>
            <el-form-item label="名称" style="margin-bottom: 12px">
              <el-input v-model="child.name" placeholder="子菜单名称" />
            </el-form-item>
            <el-form-item label="路径" style="margin-bottom: 12px">
              <el-input v-model="child.path" placeholder="如 /users/index" />
            </el-form-item>
            <el-form-item label="组件" style="margin-bottom: 12px">
              <el-input v-model="child.component" placeholder="如 system/users/index" />
            </el-form-item>
            <el-form-item label="排序" style="margin-bottom: 0">
              <el-input-number v-model="child.sort_order" :min="0" />
            </el-form-item>
          </div>

          <el-button type="primary" plain size="small" style="width: 100%" @click="addChild">
            + 添加子菜单
          </el-button>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>
