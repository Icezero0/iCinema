<script setup>
// 清除登录相关功能
</script>

<template>
  <router-view />
</template>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 100vh; 
  width: 100vw;
  padding: 2rem;
  background: linear-gradient(to bottom, #f0f4f8, #d9e2ec);
}

header {
  text-align: center;
  font-family: 'Arial', sans-serif;
  color: #333;
}

.auth-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  width: 300px;
  padding: 2rem;
  background: white;
  border-radius: 10px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

button {
  padding: 0.75rem 1.5rem;
  font-size: 1.2rem;
  cursor: pointer;
  border: none;
  border-radius: 5px;
  background-color: #007BFF;
  color: white;
  transition: background-color 0.3s ease;
}

button:hover {
  background-color: #0056b3;
}

button:active {
  background-color: #003f7f;
}
</style>
