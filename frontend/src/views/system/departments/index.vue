<script setup lang="ts">
import { ref, reactive, onMounted, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus } from "@element-plus/icons-vue";
import type { FormInstance, FormRules } from "element-plus";
import { PureTableBar } from "@/components/RePureTableBar";
import { getDepartmentList, createDepartment, updateDepartment, deleteDepartment } from "@/api/departments";
import { handleTree } from "@/utils/tree";
import { ErrorCode } from "@/constants/error-code";

const loading = ref(false);
const list = ref<any[]>([]);
const dialogVisible = ref(false);
const dialogTitle = ref("新增部门");

const deptTree = computed(() => handleTree(list.value, "id", "parent_id", "children"));

const columns: TableColumnList = [
  { label: "ID", prop: "id", width: 80 },
  { label: "编码", prop: "code" },
  { label: "名称", prop: "name" },
  { label: "排序", prop: "sort_order", width: 80 },
  { label: "描述", prop: "description" },
  { label: "操作", slot: "operation", width: 180, fixed: "right" },
];

const pureTableRef = ref();
const treeBarRef = computed(() => {
  const el = pureTableRef.value?.getTableRef?.();
  if (!el) return null;
  return {
    data: deptTree.value,
    size: "default",
    toggleRowExpansion: (row: any, expanded: boolean) => el.toggleRowExpansion(row, expanded),
  };
});

const form = reactive({ id: 0, code: "", name: "", parent_id: null as number | null, sort_order: 0, description: "" });
const formRef = ref<FormInstance>();

// 服务端唯一性冲突（18002 部门编码已存在）→ 字段级标红
const fieldErrors = reactive({ code: "" });

const rules: FormRules = {
  code: [{ required: true, message: "请输入部门编码", trigger: "blur" }],
  name: [{ required: true, message: "请输入部门名称", trigger: "blur" }],
};

async function onSearch() {
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
  fieldErrors.code = "";
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
  // 每次提交前清空字段级错误：el-form-item 的 error 是 watch 属性，
  // 同值重复赋值不会触发显示，否则连续提交相同编码时错误只会出现一次
  fieldErrors.code = "";
  try {
    await formRef.value.validate();
    const data: any = {
      name: form.name,
      parent_id: form.parent_id ?? null,
      sort_order: form.sort_order,
      description: form.description || null,
    };
    if (form.id) {
      const res: any = await updateDepartment(form.id, data);
      if (res.code !== 0) { ElMessage.error(res.message || "更新失败"); return; }
      ElMessage.success("更新成功");
    } else {
      const res: any = await createDepartment({ ...data, code: form.code });
      if (res.code !== 0) {
        if (res.code === ErrorCode.DEPT_CODE_EXISTS) {
          fieldErrors.code = res.message || "部门编码已存在";
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
    await ElMessageBox.confirm(`确认删除部门 "${row.name}"？`, "提示", { type: "warning" });
    const res: any = await deleteDepartment(row.id);
    if (res.code === 0) { ElMessage.success(res.message ?? "已删除"); onSearch(); }
    else { ElMessage.error(res.message || "删除失败"); }
  } catch { /* 用户取消或拦截器已弹 toast */ }
}

function getDescendantIds(nodeId: number): Set<number> {
  const ids = new Set<number>();
  const visited = new Set<number>([nodeId]);
  const collect = (parentId: number) => {
    for (const item of list.value) {
      if (item.parent_id !== parentId || visited.has(item.id)) continue;
      visited.add(item.id);
      ids.add(item.id);
      collect(item.id);
    }
  };
  collect(nodeId);
  return ids;
}

function parentOptions(currentId = 0) {
  const excludeIds = getDescendantIds(currentId);
  excludeIds.add(currentId);
  return list.value.filter((m: any) => !excludeIds.has(m.id)).map((m: any) => ({ label: m.name, value: m.id }));
}

onMounted(onSearch);
</script>

<template>
  <div>
    <PureTableBar :columns="columns" :table-ref="treeBarRef" @refresh="onSearch">
      <template #title>
        <el-button v-perms="['department:create']" type="primary" :icon="Plus" @click="openCreate">新增部门</el-button>
      </template>
      <template v-slot="{ size, dynamicColumns }">
        <pure-table
          ref="pureTableRef"
          row-key="id"
          :tree-props="{ children: 'children', hasChildren: 'hasChildren', checkStrictly: false }"
          default-expand-all
          align-whole="center"
          showOverflowTooltip
          :loading="loading"
          :size="size"
          :data="deptTree"
          :columns="dynamicColumns"
          :header-cell-style="{ background: 'var(--el-fill-color-light)', color: 'var(--el-text-color-primary)' }"
        >
          <template #operation="{ row }">
            <el-button v-perms="['department:update']" type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button v-perms="['department:delete']" type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </pure-table>
      </template>
    </PureTableBar>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="550px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item v-if="!form.id" label="编码" prop="code" :error="fieldErrors.code">
          <el-input v-model="form.code" @input="fieldErrors.code = ''" />
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
