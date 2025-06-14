<template>
  <div class="page-container">
    <div class="auth-card">
      <h2>注册</h2>
      <form @submit.prevent="handleRegister" class="auth-form">
        <input type="text" v-model="username" placeholder="用户名" required />
        <input type="email" v-model="email" placeholder="邮箱" required />
        <input type="password" v-model="password" placeholder="密码" required />
        <input type="password" v-model="confirmPassword" placeholder="重复密码" required />
        <span v-if="passwordMismatch" class="error-text">两次输入的密码不一致</span>
        <button type="submit">注册</button>
      </form>
      <button class="secondary-button" @click="$router.push('/login')">返回登录</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { API_BASE_URL } from '@/utils/api';

const username = ref('');
const email = ref('');
const password = ref('');
const confirmPassword = ref('');
const router = useRouter();

const passwordMismatch = computed(() => password.value !== confirmPassword.value);

const handleRegister = async () => {
  if (passwordMismatch.value) {
    alert('请确保两次输入的密码一致');
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/users`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: username.value,
        email: email.value,
        password: password.value,
      }),
    });

    if (!response.ok) {
      if (response.status === 400) {
        const errorData = await response.json();
        alert(errorData.detail || '注册失败，请检查您的信息');
      } else {
        throw new Error('未知错误');
      }
      return;
    }

    alert('注册成功！');
    router.push('/login');
  } catch (error) {
    console.error(error);
    alert(error.message);
  }
};
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

.auth-card {
  background: white;
  padding: 2.5rem;
  border-radius: 12px;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 360px;
  text-align: center;
}

.auth-card h2 {
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
  color: #333;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1rem;
}

input {
  padding: 0.75rem;
  font-size: 1rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  box-sizing: border-box;
}

button {
  padding: 0.75rem;
  font-size: 1rem;
  border: none;
  border-radius: 6px;
  width: 100%;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

button[type='submit'] {
  background-color: #007bff;
  color: white;
}

button[type='submit']:hover {
  background-color: #0056b3;
}

.secondary-button {
  background-color: #28a745;
  color: white;
  width: 100%;
  padding: 0.75rem;
  font-size: 1rem;
}

.secondary-button:hover {
  background-color: #218838;
}

.error-text {
  color: red;
  font-size: 0.875rem;
  margin-top: -0.5rem;
  margin-bottom: 0.5rem;
}
</style>
