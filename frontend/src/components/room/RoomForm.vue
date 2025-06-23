<template>
  <form class="room-form" @submit.prevent>
    <div class="form-group">
      <label for="room-name">房间名称：</label>
      <input 
        id="room-name" 
        v-model="modelValue.name" 
        type="text" 
        class="room-input" 
        placeholder="请输入房间名称" 
        required 
        autocomplete="off"
      />
    </div>
    <div class="form-group">
      <label for="room-public">是否公开：</label>
      <input id="room-public" type="checkbox" v-model="modelValue.isPublic" />
      <span>{{ modelValue.isPublic ? '公开' : '私有' }}</span>
    </div>
  </form>
</template>

<script setup>
import { reactive, watch, toRefs } from 'vue';
import '@/styles/components/room/form.css';

const props = defineProps({
  modelValue: {
    type: Object,
    required: true
  }
});
const emit = defineEmits(['update:modelValue']);
const localForm = reactive({
  name: props.modelValue.name || '',
  isPublic: props.modelValue.isPublic ?? true
});
watch(localForm, (val) => {
  emit('update:modelValue', { ...val });
}, { deep: true });
watch(() => props.modelValue, (val) => {
  localForm.name = val.name;
  localForm.isPublic = val.isPublic;
}, { deep: true });
</script>

<style scoped>
/* Component-specific styles can be added here if needed */
</style>
