<script setup lang="ts">
import type { MemberStatus, RoomRole } from "@/features/room/types";

const props = withDefaults(
  defineProps<{
    name: string;
    role: RoomRole;
    status: MemberStatus | "idle";
    size?: number;
  }>(),
  {
    size: 42,
  },
);

function memberInitial(name: string) {
  return name.slice(0, 1).toUpperCase();
}
</script>

<template>
  <div
    class="avatar"
    :data-role="role"
    :style="{ width: `${props.size}px`, height: `${props.size}px` }"
  >
    <span>{{ memberInitial(name) }}</span>
    <span class="statusDot" :data-status="status" />
  </div>
</template>

<style scoped>
.avatar {
  border-radius: 999px;
  position: relative;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 700;
  background: color-mix(in srgb, var(--c-surface) 74%, white);
  border: 2px solid var(--c-border);
  user-select: none;
}

.avatar[data-role="owner"] {
  border-color: #f2c14d;
}

.avatar[data-role="manager"] {
  border-color: #3dc0b3;
}

.avatar[data-role="member"] {
  border-color: color-mix(in srgb, var(--c-border) 75%, white);
}

.statusDot {
  position: absolute;
  right: -1px;
  bottom: -1px;
  width: 11px;
  height: 11px;
  border-radius: 999px;
  border: 2px solid white;
}

.statusDot[data-status="playing"] {
  background: #2fb46e;
}

.statusDot[data-status="paused"] {
  background: #dfad3f;
}

.statusDot[data-status="buffering"] {
  background: #dfad3f;
}

.statusDot[data-status="offline"] {
  background: transparent;
  border-color: #9aa8b8;
}

.statusDot[data-status="idle"] {
  background: transparent;
  border-color: #9aa8b8;
}

.statusDot[data-status="error"] {
  background: #dc4f4f;
}
</style>
