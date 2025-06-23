<template>
  <div 
    :class="dividerClasses"
    @mousedown="startDrag"
  ></div>
</template>

<script setup>
import { computed, onBeforeUnmount } from 'vue';

const props = defineProps({
  direction: {
    type: String,
    default: 'horizontal', // 'horizontal' | 'vertical'
    validator: (value) => ['horizontal', 'vertical'].includes(value)
  },
  isDarkMode: {
    type: Boolean,
    default: false
  },  targetRef: {
    type: [Object, null],
    default: null
  },
  minSize: {
    type: Number,
    default: 200
  },
  maxSize: {
    type: Number,
    default: null
  }
});

const emit = defineEmits(['drag-start', 'dragging', 'drag-end']);

const dividerClasses = computed(() => [
  'drag-divider',
  {
    'drag-divider-horizontal': props.direction === 'horizontal',
    'drag-divider-vertical': props.direction === 'vertical',
    'dark-mode': props.isDarkMode
  }
]);

let isDragging = false;
let startPosition = 0;
let startSize = 0;

function startDrag(e) {
  // 获取实际的 DOM 元素
  const targetElement = props.targetRef?.value || props.targetRef;
  if (!targetElement) {
    return;
  }
  
  isDragging = true;
  startPosition = props.direction === 'horizontal' ? e.clientY : e.clientX;
  startSize = props.direction === 'horizontal' 
    ? targetElement.offsetHeight 
    : targetElement.offsetWidth;
  
  const cursor = props.direction === 'horizontal' ? 'row-resize' : 'col-resize';
  document.body.style.cursor = cursor;
  document.body.style.userSelect = 'none';
  
  window.addEventListener('mousemove', onDrag);
  window.addEventListener('mouseup', stopDrag);
  
  emit('drag-start', { startSize, startPosition });
}

function onDrag(e) {
  if (!isDragging) return;
  
  // 获取实际的 DOM 元素
  const targetElement = props.targetRef?.value || props.targetRef;
  if (!targetElement) return;  const currentPosition = props.direction === 'horizontal' ? e.clientY : e.clientX;
  const delta = props.direction === 'horizontal' 
    ? currentPosition - startPosition 
    : startPosition - currentPosition; // 垂直拖拽时：向右拖拽为负，向左拖拽为正，这样可以反转逻辑
  
  let newSize = Math.max(props.minSize, startSize + delta);
    // 应用最大尺寸限制
  if (props.maxSize && newSize > props.maxSize) {
    newSize = props.maxSize;
  }
  
  if (props.direction === 'horizontal') {
    targetElement.style.height = newSize + 'px';
  } else {
    targetElement.style.width = newSize + 'px';
  }
  
  emit('dragging', { newSize, delta });
}

function stopDrag() {
  isDragging = false;
  document.body.style.cursor = '';
  document.body.style.userSelect = '';
  window.removeEventListener('mousemove', onDrag);
  window.removeEventListener('mouseup', stopDrag);
  
  emit('drag-end');
}

onBeforeUnmount(() => {
  // 清理事件监听器
  window.removeEventListener('mousemove', onDrag);
  window.removeEventListener('mouseup', stopDrag);
});
</script>

<style scoped>
.drag-divider {
  position: relative;
  z-index: 2;
  margin: 0;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e0e6ed;
  transition: background 0.2s ease;
}

.drag-divider:hover {
  background: #d0d6dd;
}

.drag-divider-horizontal {
  height: 7px;
  width: 100%;
  cursor: row-resize;
  border-radius: 4px; /* 水平拖拽条保持圆角 */
}

.drag-divider-vertical {
  width: 7px;
  height: 100%;
  cursor: col-resize;
  border-radius: 0; /* 垂直拖拽条设置为直角 */
}

.drag-divider::after {
  content: '';
  display: block;
  background: #b0bec5;
  border-radius: 2px;
  transition: background 0.2s ease;
}

.drag-divider-horizontal::after {
  width: 32px;
  height: 3px;
}

.drag-divider-vertical::after {
  height: 32px;
  width: 3px;
}

/* 暗色主题 */
.drag-divider.dark-mode {
  background: #23283a;
}

.drag-divider.dark-mode:hover {
  background: #2a3045;
}

.drag-divider.dark-mode::after {
  background: #90caf9;
}
</style>
