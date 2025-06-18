<template>
  <transition name="fade">
    <div v-if="visible" class="base-toast" :style="customStyle">
      {{ message }}
    </div>
  </transition>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue';
const props = defineProps({
  modelValue: Boolean,
  message: { type: String, default: '' },
  duration: { type: Number, default: 1500 }, // 毫秒
  top: { type: String, default: '40px' },
});
const emit = defineEmits(['update:modelValue']);
const visible = ref(props.modelValue);
let timer = null;

watch(() => props.modelValue, (val) => {
  visible.value = val;
  if (val) {
    clearTimeout(timer);
    timer = setTimeout(() => {
      visible.value = false;
      emit('update:modelValue', false);
    }, props.duration);
  }
});

onUnmounted(() => { clearTimeout(timer); });

const customStyle = {
  top: props.top
};
</script>

<style scoped>
.base-toast {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  min-width: 120px;
  max-width: 80vw;
  background: rgba(51,51,51,0.95);
  color: #fff;
  padding: 12px 28px;
  border-radius: 8px;
  font-size: 16px;
  text-align: center;
  z-index: 9999;
  box-shadow: 0 2px 12px rgba(0,0,0,0.18);
  pointer-events: none;
}
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
