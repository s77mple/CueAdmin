<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getUserList, deleteUser } from "@/api/system";

const loading = ref(false);
const list = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);

async function load() {
  loading.value = true;
  try {
    const res = await getUserList({ page: page.value, page_size: pageSize.value });
    if (res.code === 0) {
      list.value = res.data.items;
      total.value = res.data.total;
    }
  } finally {
    loading.value = false;
  }
}

async function handleDelete(id: number, username: string) {
  await ElMessageBox.confirm(`确认禁用用户 "${username}"？`, "提示", { type: "warning" });
  await deleteUser(id);
  ElMessage.success("已禁用");
  load();
}

function handlePageChange(p: number) {
  page.value = p;
  load();
}

onMounted(load);
</script>

<template>
  <div>
    <el-table v-loading="loading" :data="list" border stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="display_name" label="显示名" />
      <el-table-column prop="phone" label="手机号" />
      <el-table-column prop="is_active" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'">
            {{ row.is_active ? "启用" : "禁用" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button type="danger" size="small" :disabled="!row.is_active"
                     @click="handleDelete(row.id, row.username)">禁用</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      style="margin-top: 16px; justify-content: flex-end"
      background layout="total, prev, pager, next"
      :total="total" :page-size="pageSize" :current-page="page"
      @current-change="handlePageChange" />
  </div>
</template>
