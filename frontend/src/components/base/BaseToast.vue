<template>
  <transition name="fade">
    <div v-if="visible" class="base-toast" :style="customStyle">
      {{ message }}
    </div>
  </transition>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue';
import '@/styles/components/base/toast.css';

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
/* Component-specific styles can be added here if needed */
</style>
