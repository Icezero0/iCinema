<template>
  <div v-if="show" class="dialog-mask">
    <div class="dialog-box">
      <div class="dialog-title">{{ title }}</div>
      <div class="dialog-content">
        <slot />
      </div>
      <div class="dialog-actions">
        <button 
          v-if="showCancel" 
          class="dialog-cancel-btn" 
          @click="$emit('cancel')"
        >
          取消
        </button>
        <button class="dialog-ok-btn" @click="$emit('ok')">{{ okText }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import '@/styles/components/base/dialog.css';

defineProps({
  show: Boolean,
  title: {
    type: String,
    default: ''
  },
  showCancel: {
    type: Boolean,
    default: true
  },
  okText: {
    type: String,
    default: '确定'
  }
});
</script>

<style scoped>
/* Component-specific styles can be added here if needed */
</style>
