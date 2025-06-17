<template>
  <div class="pagination">
    <button :disabled="currentPage <= 1" @click="$emit('update:currentPage', currentPage - 1)">上一页</button>
    <span>第 {{ currentPage }} / {{ totalPages }} 页</span>
    <button :disabled="currentPage >= totalPages" @click="$emit('update:currentPage', currentPage + 1)">下一页</button>
  </div>
</template>

<script setup>
const props = defineProps({
  currentPage: { type: Number, required: true },
  totalPages: { type: Number, required: true }
});
</script>

<style scoped>
.pagination {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  margin-bottom: 10px;
}
.pagination button {
  padding: 4px 14px;
  border-radius: 4px;
  border: 1px solid #1976d2;
  background: #fff;
  color: #1976d2;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}
.pagination button:disabled {
  background: #eee;
  color: #aaa;
  border-color: #ccc;
  cursor: not-allowed;
}
.pagination span {
  font-size: 15px;
  color: #333;
}
</style>
