<script setup lang="ts">
import { ref, onMounted } from "vue";
import { getMenuList } from "@/api/menus";

const loading = ref(false);
const list = ref([]);

async function load() {
  loading.value = true;
  try {
    const res = await getMenuList();
    if (res.code === 0) list.value = res.data.items;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <el-table v-loading="loading" :data="list" border stripe row-key="id">
    <el-table-column prop="id" label="ID" width="80" />
    <el-table-column prop="code" label="编码" />
    <el-table-column prop="name" label="名称" />
    <el-table-column prop="icon" label="图标" width="120" />
    <el-table-column prop="path" label="路径" />
    <el-table-column prop="sort_order" label="排序" width="80" />
  </el-table>
</template>
