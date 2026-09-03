<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus } from "@element-plus/icons-vue";
import type { FormInstance, FormRules } from "element-plus";
import type { PaginationProps } from "@pureadmin/table";
import { PureTableBar } from "@/components/RePureTableBar";
import { getPostList, getPost, createPost, updatePost, deletePost } from "@/api/system/posts";
import type { Post } from "@/api/system/types";
import { ErrorCode } from "@/constants/error-code";

const loading = ref(false);
const list = ref<Post[]>([]);
const pagination = reactive<PaginationProps>({
  total: 0,
  pageSize: 20,
  currentPage: 1,
  background: true
});
const dialogVisible = ref(false);
const dialogTitle = ref("新增岗位");

const form = reactive({
  id: 0,
  code: "",
  name: "",
  sort_order: 0,
  description: ""
});
const formRef = ref<FormInstance>();

// 服务端唯一性冲突（19002 岗位编码已存在）→ 字段级标红
const fieldErrors = reactive({ code: "" });

const rules = reactive<FormRules>({
  code: [{ required: true, message: "请输入岗位编码", trigger: "blur" }],
  name: [{ required: true, message: "请输入岗位名称", trigger: "blur" }]
});

const columns: TableColumnList = [
  { label: "ID", prop: "id", width: 80 },
  { label: "编码", prop: "code" },
  { label: "名称", prop: "name" },
  { label: "排序", prop: "sort_order", width: 90 },
  { label: "描述", prop: "description", minWidth: 200 },
  { label: "操作", slot: "operation", width: 150, fixed: "right" }
];

async function onSearch() {
  loading.value = true;
  try {
    const res = await getPostList({
      page: pagination.currentPage,
      page_size: pagination.pageSize
    });
    if (res.code === 0) {
      list.value = res.data?.items ?? [];
      pagination.total = res.data?.total ?? 0;
    } else ElMessage.error(res.message || "加载岗位列表失败");
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

async function openCreate() {
  dialogTitle.value = "新增岗位";
  Object.assign(form, {
    id: 0,
    code: "",
    name: "",
    sort_order: 0,
    description: ""
  });
  fieldErrors.code = "";
  dialogVisible.value = true;
}

async function openEdit(row: Post) {
  dialogTitle.value = "编辑岗位";
  const res = await getPost(row.id);
  if (res.code !== 0) {
    ElMessage.error(res.message || "加载岗位详情失败");
    return;
  }
  const detail = res.data!;
  Object.assign(form, {
    id: detail.id,
    code: detail.code,
    name: detail.name,
    sort_order: detail.sort_order,
    description: detail.description ?? ""
  });
  fieldErrors.code = "";
  dialogVisible.value = true;
}

async function handleSubmit() {
  if (!formRef.value) return;
  // 每次提交前清空字段级错误：el-form-item 的 error 是 watch 属性，
  // 同值重复赋值不会触发显示，否则连续提交相同编码时错误只会出现一次
  fieldErrors.code = "";
  try {
    await formRef.value.validate();
    const data = {
      name: form.name,
      sort_order: form.sort_order,
      description: form.description || null
    };
    if (form.id) {
      const res = await updatePost(form.id, data);
      if (res.code !== 0) {
        ElMessage.error(res.message || "更新失败");
        return;
      }
      ElMessage.success("更新成功");
    } else {
      const res = await createPost({ ...data, code: form.code });
      if (res.code !== 0) {
        if (res.code === ErrorCode.POST_CODE_EXISTS) {
          fieldErrors.code = res.message || "岗位编码已存在";
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

async function handleDelete(row: Post) {
  try {
    await ElMessageBox.confirm(`确认删除岗位 "${row.name}"？`, "提示", {
      type: "warning"
    });
    const res = await deletePost(row.id);
    if (res.code === 0) {
      ElMessage.success(res.message || "已删除");
      onSearch();
    } else {
      ElMessage.error(res.message || "删除失败");
    }
  } catch {
    /* 用户取消或拦截器已弹 toast */
  }
}

onMounted(() => {
  onSearch();
});
</script>

<template>
  <div>
    <PureTableBar :columns="columns" @refresh="onSearch">
      <template #title>
        <el-button
          v-perms="['post:create']"
          type="primary"
          :icon="Plus"
          @click="openCreate"
          >新增岗位</el-button
        >
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
          <template #operation="{ row }">
            <el-button
              v-perms="['post:update']"
              size="small"
              @click="openEdit(row)"
              >编辑</el-button
            >
            <el-button
              v-perms="['post:delete']"
              type="danger"
              size="small"
              @click="handleDelete(row)"
              >删除</el-button
            >
          </template>
        </pure-table>
      </template>
    </PureTableBar>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="480px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item
          v-if="!form.id"
          label="编码"
          prop="code"
          :error="fieldErrors.code"
        >
          <el-input v-model="form.code" @input="fieldErrors.code = ''" />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" />
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
