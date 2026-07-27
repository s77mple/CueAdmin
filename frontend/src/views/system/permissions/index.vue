<script setup lang="ts">
import { ref, onMounted } from "vue";
import { getPermissionList } from "@/api/permissions";

const loading = ref(false);
const list = ref([]);

async function load() {
  loading.value = true;
  try {
    const res = await getPermissionList();
    if (res.code === 0) list.value = res.data.items;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <el-table v-loading="loading" :data="list" border stripe>
    <el-table-column prop="id" label="ID" width="80" />
    <el-table-column prop="code" label="权限码" />
    <el-table-column prop="name" label="名称" />
    <el-table-column prop="resource" label="资源" />
    <el-table-column prop="action" label="操作" />
    <el-table-column prop="description" label="描述" />
  </el-table>
</template>
