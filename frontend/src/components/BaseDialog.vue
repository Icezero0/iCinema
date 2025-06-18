<template>
  <div v-if="show" class="dialog-mask">
    <div class="dialog-box">
      <div class="dialog-title">{{ title }}</div>
      <div class="dialog-content">
        <slot />
      </div>
      <div class="dialog-actions">
        <button class="dialog-cancel-btn" @click="$emit('cancel')">取消</button>
        <button class="dialog-ok-btn" @click="$emit('ok')">确定</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  show: Boolean,
  title: {
    type: String,
    default: ''
  }
});
</script>

<style scoped>
.dialog-mask {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.dialog-box {
  background: #fff;
  border-radius: 8px;
  min-width: 320px;
  max-width: 90vw;
  padding: 24px 28px 18px 28px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.18);
  display: flex;
  flex-direction: column;
  align-items: stretch;
}
.dialog-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #1976d2;
}
.dialog-content {
  font-size: 15px;
  color: #333;
  margin-bottom: 24px;
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
.dialog-actions button {
  padding: 6px 18px;
  border: none;
  border-radius: 4px;
  font-size: 15px;
  cursor: pointer;
  background: #1976d2;
  color: #fff;
  transition: background 0.2s;
}
.dialog-actions button:first-child {
  background: #eee;
  color: #333;
}
.dialog-actions button:hover {
  background: #1256a2;
}
.dialog-actions button:first-child:hover {
  background: #ccc;
}
</style>
