<template>
  <div class="home-page">
    <h1>欢迎来到 iCinema</h1>
    <button @click="$router.push('/profile')">个人信息</button>
    <button @click="$router.push('/room')">进入房间</button>
  </div>
</template>

<script setup>
// 合并大厅页面内容到主页
</script>

<style scoped>
.home-page {
  text-align: center;
  padding: 2rem;
}
</style>
