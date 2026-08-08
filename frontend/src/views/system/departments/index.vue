<script setup lang="ts">
import { ref, reactive, onMounted, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { getDepartmentList, createDepartment, updateDepartment, deleteDepartment } from "@/api/departments";
import { handleTree } from "@/utils/tree";

const loading = ref(false);
const list = ref<any[]>([]);
const dialogVisible = ref(false);
const dialogTitle = ref("新增部门");

const deptTree = computed(() => handleTree(list.value, "id", "parent_id", "children"));

const form = reactive({ id: 0, code: "", name: "", parent_id: null as number | null, sort_order: 0, description: "" });
const formRef = ref<FormInstance>();

const rules: FormRules = {
  code: [{ required: true, message: "请输入部门编码", trigger: "blur" }],
  name: [{ required: true, message: "请输入部门名称", trigger: "blur" }],
};

async function load() {
  loading.value = true;
  try {
    const res = await getDepartmentList();
    if (res.code === 0) list.value = res.data?.items ?? [];
    else ElMessage.error(res.message || "加载部门列表失败");
  } finally { loading.value = false; }
}

function openCreate() {
  dialogTitle.value = "新增部门";
  Object.assign(form, { id: 0, code: "", name: "", parent_id: null, sort_order: 0, description: "" });
  dialogVisible.value = true;
}

function openEdit(row: any) {
  dialogTitle.value = "编辑部门";
  Object.assign(form, {
    id: row.id, code: row.code, name: row.name,
    parent_id: row.parent_id, sort_order: row.sort_order,
    description: row.description,
  });
  dialogVisible.value = true;
}

async function handleSubmit() {
  if (!formRef.value) return;
  try {
    await formRef.value.validate();
    const data: any = {
      name: form.name,
      parent_id: form.parent_id ?? null,
      sort_order: form.sort_order,
      description: form.description || null,
    };
    if (form.id) {
      await updateDepartment(form.id, data);
      ElMessage.success("更新成功");
    } else {
      await createDepartment({ ...data, code: form.code });
      ElMessage.success("创建成功");
    }
    dialogVisible.value = false;
    load();
  } catch (err: any) {
    if (err?.message) ElMessage.error(err.message);
  }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除部门 "${row.name}"？`, "提示", { type: "warning" });
    const res: any = await deleteDepartment(row.id);
    if (res.code === 0) { ElMessage.success(res.message ?? "已删除"); load(); }
    else { ElMessage.error(res.message || "删除失败"); }
  } catch { /* 用户取消或拦截器已弹 toast */ }
}

function getDescendantIds(nodeId: number): Set<number> {
  const ids = new Set<number>();
  const visited = new Set<number>();
  const walk = (items: any[]) => {
    for (const item of items) {
      if (visited.has(item.id)) continue;
      visited.add(item.id);
      if (item.parent_id === nodeId) {
        ids.add(item.id);
        walk(list.value);
      }
    }
  };
  walk(list.value);
  return ids;
}

function parentOptions(currentId = 0) {
  const excludeIds = getDescendantIds(currentId);
  excludeIds.add(currentId);
  return list.value.filter((m: any) => !excludeIds.has(m.id)).map((m: any) => ({ label: m.name, value: m.id }));
}

onMounted(load);
</script>

<template>
  <div>
    <el-button v-perms="['department:create']" type="primary" style="margin-bottom: 12px" @click="openCreate">新增部门</el-button>

    <el-table v-loading="loading" :data="deptTree" border stripe row-key="id" :tree-props="{ children: 'children' }">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="code" label="编码" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="sort_order" label="排序" width="80" />
      <el-table-column prop="description" label="描述" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button v-perms="['department:update']" type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button v-perms="['department:delete']" type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="550px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item v-if="!form.id" label="编码" prop="code">
          <el-input v-model="form.code" />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="父部门">
          <el-select v-model="form.parent_id" clearable placeholder="顶级部门">
            <el-option v-for="o in parentOptions(form.id)" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" />
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
