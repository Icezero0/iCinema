<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';

const email = ref('');
const password = ref('');
const router = useRouter();

const handleLogin = async () => {
  try {
    const response = await fetch('http://localhost:8000/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        email: email.value,
        password: password.value,
      }).toString(),
    });

    if (!response.ok) {
      throw new Error('登录失败，请检查您的邮箱和密码');
    }

    const data = await response.json();

    // console.log('Login successful:', data);
    document.cookie = `accesstoken=${data.access_token}; path=/; secure;`;
    document.cookie = `refreshtoken=${data.refresh_token}; path=/; secure;`;

    // console.log('writing cookies:', document.cookie);

    // console.log('redirecting to home page');
    router.push('/home');
  } catch (error) {
    console.error(error);
    alert(error.message);
  }
};
</script>

<template>
  <div class="page-container">
    <div class="auth-card">
      <h2>iCinema</h2>
      <form @submit.prevent="handleLogin" class="auth-form">
        <input type="email" v-model="email" placeholder="邮箱" required />
        <input type="password" v-model="password" placeholder="密码" required />
        <button type="submit">登录</button>
      </form>
      <button class="secondary-button" @click="$router.push('/register')">注册</button>
    </div>
  </div>
</template>

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

button[type="submit"] {
  background-color: #007BFF;
  color: white;
}

button[type="submit"]:hover {
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
</style>
