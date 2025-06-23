<template>
  <div class="page-container">
    <form class="profile-form">
      <h2>个人资料</h2>
      <div class="form-group avatar-center">
        <AvatarUploader v-model="avatarUrl" />
      </div>
      <div class="form-group">
        <label>用户名<span v-if="usernameInput !== username">*</span></label>        <input
          type="text"
          v-model="usernameInput"
          @blur="validateUsername"
          :placeholder="usernameError ? usernameError : '请输入用户名'"
          :class="{'input-error-border': usernameError}"
          autocomplete="new-username"
        />
      </div>
      <div class="form-group">
        <label>邮箱</label>
        <input type="text" :value="email" readonly disabled class="email-disabled" />
      </div>
      <div class="form-group">
        <label>新密码</label>
        <input 
          type="password" 
          v-model="newPassword" 
          placeholder="不修改" 
          autocomplete="new-password"
        />
      </div>
      <div class="form-group">
        <label style="display: flex; align-items: center; min-height: 1.5em;">
          确认新密码
          <span v-if="confirmPassword && newPassword && confirmPassword !== newPassword" class="password-error-tip">*密码不一致</span>
          <span v-else class="password-error-tip" style="visibility:hidden;">不一致</span>
        </label>
        <input 
          type="password" 
          v-model="confirmPassword" 
          placeholder="不修改" 
          autocomplete="new-password"
        />
      </div>
      <div class="button-group">
        <button class="save-button" type="button" @click="handleSave" :disabled="!isModified">保存</button>
        <button class="cancel-button" type="button" @click="handleCancel">取消</button>
      </div>
    </form>
    <CustomConfirm
      :show="showConfirm"
      title="确认保存"
      content="确定要保存更改吗？"
      @ok="handleConfirmOk"
      @cancel="handleConfirmCancel"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import defaultAvatar from '@/assets/default_avatar.jpg';
import AvatarUploader from '@/components/user/AvatarUploader.vue';
import CustomConfirm from '@/components/base/CustomConfirm.vue';
import { useMyUserInfo } from '@/composables/useUserInfo.js';
import { API_BASE_URL, getImageUrl } from '@/utils/api';

const router = useRouter();
const usernameInput = ref('');
const usernameError = ref('');
const showConfirm = ref(false); // 控制自定义弹窗显示
let savePending = false; // 防止重复提交

const { username, avatarUrl, email, fetchUserInfo } = useMyUserInfo();


onMounted(async () => {
  // 如果sessionStorage有缓存，则不请求后端
  if (username && avatarUrl && email) {
    usernameInput.value = username.value;
    return;
  }
  await fetchUserInfo();
});

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
  // 构建 JSON 数据
  const payload = {
    email: email.value
  };
  if (usernameInput.value !== username.value) {
    payload.username = usernameInput.value;
  }
  // 判断头像是否需要提交，仅当头像为本地base64格式（即用户刚裁剪过）时才提交
  if (avatarUrl.value.startsWith('data:image/')) {
    payload.avatar_base64 = avatarUrl.value;
  }
  // 新密码逻辑：如有输入则加入 password 字段
  if (newPassword.value && confirmPassword.value && newPassword.value === confirmPassword.value) {
    payload.password = newPassword.value;
  }
  try {
    const response = await fetch(`${API_BASE_URL}/users/me`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (response.ok) {
      const userResp = await response.json();
      if (payload.username) {
        username.value = usernameInput.value;
      }
      newPassword.value = '';
      confirmPassword.value = '';
      // 保存成功后再请求一次 /users/me 并刷新缓存，确保缓存与后端同步
      await fetchUserInfo();
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
  // 新密码逻辑：新密码和确认新密码都不为空且一致时可保存
  if (
    newPassword.value &&
    confirmPassword.value &&
    newPassword.value === confirmPassword.value
  ) {
    return true;
  }
  return false;
});

const oldPassword = ref("");
const newPassword = ref("");
const confirmPassword = ref("");
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
  background: linear-gradient(120deg, #fbeee6 0%, #e6eaf5 100%);
  /* 参考主页用户卡片的渐变色 */
  padding: 2.5rem 2rem;
  border-radius: 18px;
  box-shadow: 0 8px 32px rgba(0, 80, 180, 0.10), 0 1.5px 8px rgba(0,0,0,0.06);
  width: 100%;
  max-width: 800px;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  align-items: center;
  border: 1.5px solid #e0eaff;
  /* 轻微描边 */
}

h2 {
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
  color: #007BFF;
  font-weight: bold;
  text-shadow: 0 2px 8px rgba(0,0,0,0.10);
}

.form-group {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
}

.form-group.avatar-center {
  align-items: center;
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

.password-error-tip {
  color: #e53935;
  font-size: 0.85em;
  margin-left: 10px;
  font-weight: normal;
  vertical-align: middle;
}
</style>
