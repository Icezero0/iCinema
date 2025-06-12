<template>
  <div class="page-container">
    <form class="profile-form">
      <h2>个人资料</h2>
      <div class="form-group">
        <div class="avatar-upload-wrapper">
          <label for="avatar-upload">
            <img :src="avatarUrl" alt="avatar" class="avatar-large clickable" />
            <input id="avatar-upload" type="file" accept="image/*" @change="onAvatarChange" style="display:none" />
          </label>
          <span class="avatar-tip">点击头像上传图片</span>
        </div>
      </div>
      <div class="form-group">
        <label>用户名<span v-if="usernameInput !== username">*</span></label>
        <input
          type="text"
          v-model="usernameInput"
          @blur="validateUsername"
          :placeholder="usernameError ? usernameError : '请输入用户名'"
          :class="{'input-error-border': usernameError}"
        />
      </div>
      <div class="form-group">
        <label>邮箱</label>
        <input type="text" :value="email" readonly disabled class="email-disabled" />
      </div>
      <div class="button-group">
        <button class="save-button" type="button" @click="handleSave" :disabled="!isModified">保存</button>
        <button class="cancel-button" type="button" @click="handleCancel">取消</button>
      </div>
    </form>

    <!-- 裁剪头像的对话框 -->
    <div v-if="showCropper" class="cropper-modal">
      <div class="cropper-container">
        <Cropper
          ref="cropperRef"
          :src="cropperImg"
          :aspect-ratio="1"
          :view-mode="1"
          :auto-crop-area="1"
          :background="false"
          :responsive="true"
          :rotatable="false"
          :zoomable="true"
          style="width:320px;height:320px;"
        />
        <div class="cropper-btn-group">
          <button type="button" class="save-button" @click="handleCrop">确定</button>
          <button type="button" class="cancel-button" @click="handleCancelCrop">取消</button>
        </div>
      </div>
    </div>

    <!-- 自定义确认弹窗 -->
    <div v-if="showConfirm" class="custom-confirm-modal">
      <div class="custom-confirm-box">
        <div class="custom-confirm-title">确认保存</div>
        <div class="custom-confirm-content">确定要保存更改吗？</div>
        <div class="custom-confirm-btns">
          <button class="save-button" @click="handleConfirmOk">确定</button>
          <button class="cancel-button" @click="handleConfirmCancel">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import defaultAvatar from '@/assets/default_avatar.jpg';
import Cropper from 'vue-cropperjs';
import 'cropperjs/dist/cropper.css';

const router = useRouter();
const username = ref('');
const usernameInput = ref('');
const avatarUrl = ref(defaultAvatar);
const email = ref('');
const showCropper = ref(false);
const cropperImg = ref('');
const cropperRef = ref();
const usernameError = ref('');
const showConfirm = ref(false); // 控制自定义弹窗显示
let savePending = false; // 防止重复提交

// 用户头像缓存key
const AVATAR_CACHE_KEY = 'icinema_avatar_url';

// 初始化时优先从localStorage读取缓存头像
const cachedAvatar = localStorage.getItem(AVATAR_CACHE_KEY);
if (cachedAvatar) {
  avatarUrl.value = cachedAvatar;
}

onMounted(async () => {
  try {
    const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
    if (!accessToken) return;
    const response = await fetch('http://localhost:8000/users/me', {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });
    if (response.ok) {
      const data = await response.json();
      username.value = data.username || 'unknown_user';
      usernameInput.value = username.value;
      if (data.icon_path) {
        avatarUrl.value = `http://localhost:8000${data.icon_path}`;
      } else {
        avatarUrl.value = data.avatar || defaultAvatar;
      }
      // 更新缓存
      localStorage.setItem(AVATAR_CACHE_KEY, avatarUrl.value);
      email.value = data.email || '';
    }
  } catch (e) {
    alert('获取用户信息失败，请稍后再试。');
    console.error('Error fetching user info:', e);
  }
});

function onAvatarChange(e) {
  const file = e.target.files[0];
  if (file) {
    const reader = new FileReader();
    reader.onload = (event) => {
      cropperImg.value = event.target.result;
      showCropper.value = true;
    };
    reader.readAsDataURL(file);
  }
}

function handleCrop() {
  // 获取裁剪后的canvas
  let canvas = cropperRef.value.getCroppedCanvas();
  if (canvas) {
    let targetWidth = 512;
    let targetHeight = 512;
    if (canvas.width > targetWidth || canvas.height > targetHeight) {
      const tmpCanvas = document.createElement('canvas');
      tmpCanvas.width = targetWidth;
      tmpCanvas.height = targetHeight;
      const ctx = tmpCanvas.getContext('2d');
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, targetWidth, targetHeight);
      ctx.drawImage(canvas, 0, 0, targetWidth, targetHeight);
      avatarUrl.value = tmpCanvas.toDataURL('image/jpeg');
    } else {
      avatarUrl.value = canvas.toDataURL('image/jpeg');
    }
    // 裁剪后立即缓存
    localStorage.setItem(AVATAR_CACHE_KEY, avatarUrl.value);
    showCropper.value = false;
  }
}

function handleCancelCrop() {
  showCropper.value = false;
}

function handleCancel() {
  router.push('/home');
}

function validateUsername() {
  if (!usernameInput.value.trim()) {
    usernameError.value = '用户名不能为空';
  } else {
    usernameError.value = '';
  }
}

function handleSave() {
  validateUsername();
  if (usernameError.value) {
    return;
  }
  showConfirm.value = true;
}

async function doSave() {
  if (savePending) return;
  savePending = true;
  const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
  if (!accessToken) {
    alert('未登录，无法保存');
    showConfirm.value = false;
    savePending = false;
    return;
  }
  // 构建 FormData
  const formData = new FormData();
  formData.append('email', email.value);
  if (usernameInput.value !== username.value) {
    formData.append('username', usernameInput.value);
  }
  // 判断头像是否需要提交，仅当头像为本地base64格式（即用户刚裁剪过）时才提交
  if (avatarUrl.value.startsWith('data:image/')) {
    formData.append('avatar_base64', avatarUrl.value);
  }
  try {
    const response = await fetch('http://localhost:8000/users/me', {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        // 不要设置 Content-Type，浏览器会自动设置 multipart/form-data
      },
      body: formData,
    });
    if (response.ok) {
      // 保存成功后缓存头像
      localStorage.setItem(AVATAR_CACHE_KEY, avatarUrl.value);
      if (formData.has('username')) {
        username.value = usernameInput.value;
      }
      router.push('/home');
    } else {
      const err = await response.json().catch(() => ({}));
      alert('保存失败：' + (err.detail || response.statusText));
    }
  } catch (e) {
    alert('保存失败，请稍后再试。');
    console.error('Error saving profile:', e);
  } finally {
    showConfirm.value = false;
    savePending = false;
  }
}

function handleConfirmOk() {
  doSave();
}
function handleConfirmCancel() {
  showConfirm.value = false;
}

const isModified = computed(() => {
  // 用户名变动
  if (usernameInput.value !== username.value) return true;
  // 头像变动：与 doSave 逻辑保持一致，仅当头像为本地 base64（即裁剪过）才算变动
  if (avatarUrl.value.startsWith('data:image/')) return true;
  return false;
});
</script>

<style scoped>
.page-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(to bottom, #e6f5f3, #c8e6e0);
  padding: 1rem;
}

.profile-form {
  background: white;
  padding: 2.5rem 2rem;
  border-radius: 12px;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 800px;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  align-items: center;
}

h2 {
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
  color: #007BFF;
}

.form-group {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
}

.form-group label {
  font-size: 1rem;
  color: #555;
  margin-bottom: 0.25rem;
}

.form-group input {
  padding: 0.75rem;
  font-size: 1rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  width: 100%;
  background: #f8fafc;
  color: #333;
}

.avatar-upload-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}

.avatar-large {
  width: 256px;
  height: 256px;
  border-radius: 12px;
  object-fit: cover;
  border: 2px solid #eee;
  background: #fff;
  margin: 0.5rem 0;
  display: block;
  transition: box-shadow 0.2s;
}

.avatar-large.clickable {
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.avatar-large.clickable:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}

.avatar-tip {
  font-size: 0.9rem;
  color: #888;
  margin-top: 0.25rem;
}

.button-group {
  display: flex;
  flex-direction: row;
  gap: 1rem;
  width: 100%;
  justify-content: center;
}

.save-button {
  padding: 0.75rem;
  font-size: 1rem;
  border: none;
  border-radius: 6px;
  width: 100px;
  background-color: #007bff;
  color: white;
  cursor: pointer;
  transition: background-color 0.3s ease;
}
.save-button:hover {
  background-color: #0056b3;
}
.save-button:disabled {
  background-color: #b3d1f7 !important;
  color: #e6e6e6 !important;
  cursor: not-allowed !important;
  opacity: 0.7;
  box-shadow: none;
}

.cancel-button {
  padding: 0.75rem;
  font-size: 1rem;
  border: none;
  border-radius: 6px;
  width: 100px;
  background-color: #6c757d;
  color: white;
  cursor: pointer;
  transition: background-color 0.3s ease;
}
.cancel-button:hover {
  background-color: #495057;
}

.email-disabled {
  background: #f0f0f0 !important;
  color: #aaa !important;
  cursor: not-allowed;
}

.cropper-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  opacity: 1;
}

.cropper-container {
  background: #fff;
  border-radius: 10px;
  padding: 2rem 2rem 1rem 2rem;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.cropper-btn-group {
  display: flex;
  gap: 1.5rem;
  margin-top: 1.5rem;
  justify-content: center;
}

.input-error-border {
  border-color: red !important;
  color: red;
}
::placeholder {
  color: #bbb;
}
.input-error-border::placeholder {
  color: red;
}

.custom-confirm-modal {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}
.custom-confirm-box {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
  padding: 2rem 2.5rem 1.5rem 2.5rem;
  min-width: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.custom-confirm-title {
  font-size: 1.2rem;
  color: #007bff;
  font-weight: bold;
  margin-bottom: 1rem;
}
.custom-confirm-content {
  font-size: 1rem;
  color: #444;
  margin-bottom: 1.5rem;
}
.custom-confirm-btns {
  display: flex;
  gap: 2rem;
  justify-content: center;
}
</style>
