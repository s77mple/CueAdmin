<script setup lang="ts">
import { unref } from "vue";
import { useRouter } from "vue-router";

defineOptions({
  name: "Redirect"
});

const { currentRoute, replace } = useRouter();

const { params, query } = unref(currentRoute);
const { path } = params;

let _path = Array.isArray(path) ? path.join("/") : path;

// 防止开放重定向：拒绝包含协议、域名或路径遍历的恶意路径
if (
  !_path ||
  typeof _path !== "string" ||
  /^\s*https?:\/\//i.test(_path) ||
  /^\s*\/\//.test(_path) ||
  _path.includes("..")
) {
  _path = "";
}

replace({
  path: "/" + _path,
  query
});
</script>

<template>
  <div />
</template>
