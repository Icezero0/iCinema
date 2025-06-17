<template>
  <img
    :src="computedSrc"
    :alt="alt || '用户头像'"
    :class="['user-avatar', customClass]"
    :style="{ width: sizePx, height: sizePx }"
    @error="onError"
    draggable="false"
  />
</template>

<script setup>
import { ref, computed } from 'vue';
import defaultAvatar from '@/assets/default_avatar.jpg';

const props = defineProps({
  src: { type: String, default: '' },
  alt: { type: String, default: '' },
  size: { type: [Number, String], default: 32 },
  customClass: { type: String, default: '' }
});

const errored = ref(false);
const computedSrc = computed(() => {
  if (errored.value || !props.src) return defaultAvatar;
  return props.src;
});
const sizePx = computed(() => typeof props.size === 'number' ? props.size + 'px' : props.size);
function onError() {
  errored.value = true;
}
</script>

<style scoped>
.user-avatar {
  border-radius: 50%;
  object-fit: cover;
  background: #fff;
  user-select: none;
  -webkit-user-drag: none;
  display: block;
}
</style>
