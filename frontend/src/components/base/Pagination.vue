<template>
  <div class="pagination">
    <button :disabled="currentPage <= 1" @click="$emit('update:currentPage', currentPage - 1)">上一页</button>
    <span>第 {{ currentPage }} / {{ totalPages }} 页</span>
    <button :disabled="currentPage >= totalPages" @click="$emit('update:currentPage', currentPage + 1)">下一页</button>
  </div>
</template>

<script setup>
import '@/styles/components/base/pagination.css';

const props = defineProps({
  currentPage: { type: Number, required: true },
  totalPages: { type: Number, required: true }
});
</script>

<style scoped>
/* Component-specific styles can be added here if needed */
</style>
