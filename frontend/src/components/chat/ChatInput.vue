<template>
  <div class="chat-input-area">
    <!-- Emoji选择器 - 仅PC端显示 -->
    <div v-if="showEmojiPicker && !props.isMobile" class="emoji-picker" ref="emojiPickerRef">
      <div class="emoji-header">
        <div class="emoji-categories">
          <button
            v-for="(category, key) in EMOJI_CATEGORIES"
            :key="key"
            @click="selectCategory(key)"
            :class="['category-btn', { active: activeCategory === key }]"
            :title="category.name"
          >
            {{ category.icon }}
          </button>
        </div>
      </div>
      <div class="emoji-content">
        <div class="emoji-grid">
          <button
            v-for="emojiData in currentPageEmojis"
            :key="emojiData.emoji"
            @click="insertEmoji(emojiData.emoji)"
            class="emoji-btn"
            :title="emojiData.name"
          >
            {{ emojiData.emoji }}
          </button>
        </div>
        <div v-if="totalPages > 1" class="emoji-pagination">
          <button
            @click="prevPage"
            :disabled="currentPage === 0"
            class="page-btn"
          >
            ←
          </button>
          <span class="page-info">{{ currentPage + 1 }} / {{ totalPages }}</span>
          <button
            @click="nextPage"
            :disabled="currentPage === totalPages - 1"
            class="page-btn"
          >
            →
          </button>
        </div>
      </div>
    </div>

    <div class="input-controls">
      <input 
        v-model="inputMessage"
        @keyup.enter="handleSend"
        :disabled="disabled"
        placeholder="输入消息..." 
        class="chat-input"
        ref="inputRef"
        autocomplete="off"
        autocapitalize="off"
        autocorrect="off"
        spellcheck="false"
      />
      
      <!-- Emoji按钮 - 仅PC端显示 -->
      <button 
        v-if="!props.isMobile"
        @click="toggleEmojiPicker"
        class="emoji-toggle-btn"
        :class="{ active: showEmojiPicker }"
        type="button"
        title="表情"
      >
        😊
      </button>
      
      <button 
        @click="handleSend" 
        :disabled="disabled || !inputMessage.trim()"
        class="chat-send-btn"
      >
        发送
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { EMOJI_CATEGORIES, EMOJI_PER_PAGE } from '@/utils/emoji.js';

// Props
const props = defineProps({
  disabled: {
    type: Boolean,
    default: false
  },
  isMobile: {
    type: Boolean,
    default: false
  }
});

// Emits
const emit = defineEmits(['send']);

// 响应式数据
const inputMessage = ref('');
const inputRef = ref(null);
const emojiPickerRef = ref(null);

// Emoji相关状态
const showEmojiPicker = ref(false);
const activeCategory = ref('smileys');
const currentPage = ref(0);

// 防抖相关
let categoryChangeTimeout = null;

// Computed
const currentCategoryEmojis = computed(() => {
  return EMOJI_CATEGORIES[activeCategory.value]?.emojis || [];
});

const totalPages = computed(() => {
  return Math.ceil(currentCategoryEmojis.value.length / EMOJI_PER_PAGE);
});

const currentPageEmojis = computed(() => {
  const start = currentPage.value * EMOJI_PER_PAGE;
  const end = start + EMOJI_PER_PAGE;
  return currentCategoryEmojis.value.slice(start, end);
});

// 方法
function handleSend() {
  const content = inputMessage.value.trim();
  if (!content) return;
  
  emit('send', content);
  inputMessage.value = '';
  
  // 重新聚焦输入框
  if (inputRef.value) {
    inputRef.value.focus();
  }
}

function toggleEmojiPicker() {
  showEmojiPicker.value = !showEmojiPicker.value;
}

function selectCategory(categoryKey) {
  if (activeCategory.value === categoryKey) return;
  
  // 清除之前的定时器
  if (categoryChangeTimeout) {
    clearTimeout(categoryChangeTimeout);
  }
  
  // 立即更新UI，但延迟更新计算属性
  activeCategory.value = categoryKey;
  currentPage.value = 0;
  
  // 添加轻微延迟来减少快速切换时的性能问题
  categoryChangeTimeout = setTimeout(() => {
    categoryChangeTimeout = null;
  }, 50);
}

function insertEmoji(emoji) {
  const input = inputRef.value;
  if (!input) {
    inputMessage.value += emoji;
    return;
  }

  const start = input.selectionStart;
  const end = input.selectionEnd;
  const text = inputMessage.value;
  
  inputMessage.value = text.slice(0, start) + emoji + text.slice(end);
  
  // 等待DOM更新后设置光标位置
  nextTick(() => {
    const newPosition = start + emoji.length;
    input.setSelectionRange(newPosition, newPosition);
    input.focus();
  });
}

function prevPage() {
  if (currentPage.value > 0) {
    currentPage.value--;
  }
}

function nextPage() {
  if (currentPage.value < totalPages.value - 1) {
    currentPage.value++;
  }
}

function handleClickOutside(event) {
  if (emojiPickerRef.value && !emojiPickerRef.value.contains(event.target) && 
      !event.target.closest('.emoji-toggle-btn')) {
    showEmojiPicker.value = false;
  }
}

// 生命周期
onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
  if (categoryChangeTimeout) {
    clearTimeout(categoryChangeTimeout);
  }
});

// 暴露方法给父组件
defineExpose({
  focus: () => {
    if (inputRef.value) {
      inputRef.value.focus();
    }
  },
  clear: () => {
    inputMessage.value = '';
  }
});
</script>

<style scoped>
@import '@/styles/components/chat/chat-input.css';
</style>
