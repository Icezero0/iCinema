<template>
  <main class="auth">
    <div class="container">
      <router-view />
    </div>
  </main>
</template>

<style scoped>
.auth {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: var(--c-bg);
  position: relative;
  overflow: hidden;
}

.auth::before {
  content: "";
  position: absolute;
  inset: -20%;
  pointer-events: none;
  z-index: 0;

  background:
    radial-gradient(700px 420px at 18% 22%, rgba(0,0,0,0.09), transparent 60%),
    radial-gradient(800px 460px at 82% 28%, rgba(0,0,0,0.06), transparent 62%),
    linear-gradient(180deg, rgba(0,0,0,0.03), transparent 40%);
}

:global([data-theme="dark"]) .auth::before {
  background:
    radial-gradient(600px 400px at 15% 20%, rgba(255,255,255,0.07), transparent 60%),
    radial-gradient(700px 420px at 85% 30%, rgba(255,255,255,0.05), transparent 62%),
    linear-gradient(180deg, rgba(255,255,255,0.03), transparent 40%);
}
</style>
