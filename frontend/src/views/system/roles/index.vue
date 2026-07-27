<script setup lang="ts">
import { ref, onMounted } from "vue";
import { getRoleList } from "@/api/system";

const loading = ref(false);
const list = ref<any[]>([]);

onMounted(async () => {
  loading.value = true;
  try {
    const res: any = await getRoleList();
    list.value = res.data?.items ?? [];
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div style="padding: 20px">
    <h2>角色管理</h2>
    <el-table v-loading="loading" :data="list" border stripe style="margin-top: 16px">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="code" label="编码" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="description" label="描述" />
    </el-table>
  </div>
</template>
