<template>
  <div v-if="isOwner" class="room-settings card" :class="{ 'dark-mode': isDarkMode, 'mobile-mode': isMobile }">
    <h4>房间设置</h4>
    <div class="form-group">
      <label for="room-name">房间名称：</label>
      <input 
        id="room-name" 
        v-model="roomNameLocal" 
        type="text" 
        class="room-name-input" 
        autocomplete="off"
      />
      <label for="room-public-switch">公开：</label>
      <input
        id="room-public-switch"
        type="checkbox"
        v-model="isRoomPublicLocal"
        class="room-public-switch"
      />
    </div>
    <div class="room-settings-actions">
      <button class="save-btn" @click="saveRoomSettings">保存</button>
      <button class="dissolve-btn" @click="dissolveRoom">解散房间</button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { API_BASE_URL } from '@/utils/api';

// Props
const props = defineProps({
  isOwner: {
    type: Boolean,
    required: true
  },
  roomId: {
    type: [String, Number],
    required: true
  },
  roomName: {
    type: String,
    default: ''
  },
  isRoomPublic: {
    type: Boolean,
    default: false
  },  isDarkMode: {
    type: Boolean,
    default: false
  },
  isMobile: {
    type: Boolean,
    default: false
  }
});

// Emits
const emit = defineEmits([
  'room-settings-save',
  'room-dissolve',
  'show-error'
]);

// 本地状态
const roomNameLocal = ref(props.roomName);
const isRoomPublicLocal = ref(props.isRoomPublic);

// 监听 props 变化
watch(() => props.roomName, (newName) => {
  roomNameLocal.value = newName;
});

watch(() => props.isRoomPublic, (newValue) => {
  isRoomPublicLocal.value = newValue;
});

async function saveRoomSettings() {
  if (!props.roomId) return;
  
  const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
  
  try {
    const resp = await fetch(`${API_BASE_URL}/rooms/${props.roomId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({
        name: roomNameLocal.value,
        is_public: isRoomPublicLocal.value,
      })
    });    if (resp.ok) {
      // 通过父组件统一处理 toast 显示
      emit('room-settings-save', roomNameLocal.value, isRoomPublicLocal.value);
    } else {
      // 通过父组件显示错误信息
      emit('show-error', '保存房间设置失败，请稍后再试');
    }
  } catch (error) {
    emit('show-error', '保存房间设置失败，请稍后再试');
  }
}

async function dissolveRoom() {
  const ok = window.confirm('确定要解散房间吗？此操作不可撤销！');
  if (!ok) return;
  
  if (!props.roomId) return;
  
  const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
  
  try {
    const resp = await fetch(`${API_BASE_URL}/rooms/${props.roomId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });    if (resp.ok) {
      emit('room-dissolve');
    } else {
      emit('show-error', '解散房间失败，请稍后再试');
    }
  } catch (error) {
    emit('show-error', '解散房间失败，请稍后再试');
  }
}
</script>

<style scoped>
.room-settings {
  width: 100%;
  max-width: 800px;
  margin: 0 auto 24px auto;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  padding: 20px 28px 16px 28px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  border: 1px solid #e0e6ed;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #eee;
}
.room-settings.dark-mode {
  background: #23283a;
  border: 1px solid #23283a;
  box-shadow: 0 2px 12px rgba(25,118,210,0.10);
  border-top: 1px solid #23283a;
}
.room-settings h4 {
  color: #1976d2;
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 8px;
}
.room-settings.dark-mode h4 {
  color: #90caf9;
}
.form-group {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.room-name-input {
  flex: 1 1 0;
  padding: 6px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 15px;
}
.room-public-switch {
  width: 20px;
  height: 20px;
  accent-color: #1976d2;
  margin-left: 0px;
}
.room-settings-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 12px;
}
.save-btn {
  padding: 8px 24px;
  background: #1976d2;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.2s;
}
.save-btn:hover {
  background: #1256a2;
}
.dissolve-btn {
  padding: 8px 24px;
  background: #e53935;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.2s;
}
.dissolve-btn:hover {
  background: #b71c1c;
}
label {
  color: #1976d2;
  font-size: 15px;
  font-weight: 500;
}
.room-settings.dark-mode label {
  color: #90caf9;
}

/* 移动端样式 */
.room-settings.mobile-mode {
  margin: 0;
  padding: 0;
  border: none;
  box-shadow: none;
  background: transparent;
  border-radius: 0;
}

.room-settings.mobile-mode h4 {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: #333;
  border-bottom: 1px solid #f0f2f5;
  padding-bottom: 8px;
}

.room-settings.mobile-mode.dark-mode h4 {
  color: #fff;
  border-bottom-color: #3a4050;
}

.room-settings.mobile-mode .form-group {
  margin-bottom: 16px;
}

.room-settings.mobile-mode .room-name-input {
  width: 100%;
  padding: 10px 12px;
  font-size: 14px;
  border-radius: 6px;
  border: 1px solid #ddd;
  margin-bottom: 12px;
}

.room-settings.mobile-mode.dark-mode .room-name-input {
  background: #2a2f3e;
  border-color: #3a4050;
  color: #fff;
}

.room-settings.mobile-mode .room-settings-actions {
  gap: 12px;
  margin-top: 16px;
}

.room-settings.mobile-mode .save-btn,
.room-settings.mobile-mode .dissolve-btn {
  flex: 1;
  padding: 12px;
  font-size: 14px;
  border-radius: 6px;
}
</style>
