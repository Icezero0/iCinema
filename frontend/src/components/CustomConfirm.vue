<template>
  <div v-if="show" class="custom-confirm-modal">
    <div class="custom-confirm-box">
      <div class="custom-confirm-title">{{ title }}</div>
      <div class="custom-confirm-content">{{ content }}</div>
      <div class="custom-confirm-btns">
        <button class="save-button" @click="$emit('ok')">确定</button>
        <button class="cancel-button" @click="$emit('cancel')">取消</button>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  show: Boolean,
  title: { type: String, default: '确认操作' },
  content: { type: String, default: '' }
});
</script>

<style scoped>
.custom-confirm-modal { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.custom-confirm-box { background: #fff; padding: 24px 32px; border-radius: 8px; min-width: 260px; }
.custom-confirm-title { font-weight: bold; font-size: 18px; margin-bottom: 12px; }
.custom-confirm-content { margin-bottom: 16px; }
.custom-confirm-btns { display: flex; justify-content: flex-end; gap: 12px; }
.save-button, .cancel-button { padding: 6px 16px; border: none; border-radius: 4px; cursor: pointer; }
.save-button {
  background-color: #007bff;
  color: #fff;
}
.save-button:hover {
  background-color: #0056b3;
}
.cancel-button {
  background-color: #6c757d;
  color: #fff;
}
.cancel-button:hover {
  background-color: #495057;
}
</style>
