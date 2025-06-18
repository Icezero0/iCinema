<template>
  <form class="room-form" @submit.prevent>
    <div class="form-group">
      <label for="room-name">房间名称：</label>
      <input id="room-name" v-model="modelValue.name" type="text" class="room-input" placeholder="请输入房间名称" required />
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
.room-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.form-group {
  display: flex;
  align-items: center;
  gap: 10px;
}
.room-input {
  flex: 1 1 0;
  padding: 6px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 15px;
}
</style>
