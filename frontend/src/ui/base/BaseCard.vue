<template>
  <div class="card"><slot /></div>
</template>

<style scoped>
.card {
  border: 1px solid var(--c-border);
  border-radius: var(--r-2);
  padding: var(--s-3);
  background: var(--c-surface);
}
</style>
