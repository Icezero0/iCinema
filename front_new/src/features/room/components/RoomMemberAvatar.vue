<script setup lang="ts">
import type { MemberStatus, RoomRole } from "@/features/room/types";

const props = withDefaults(
  defineProps<{
    name: string;
    src?: string | null;
    role: RoomRole;
    status: MemberStatus;
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
    <BaseAvatar
      class="avatarInner"
      :src="src || undefined"
      :name="name"
      :alt="name"
      shape="circle"
      fit="cover"
      :style="{ width: `${props.size}px`, height: `${props.size}px` }"
    >
      <template #fallback>
        <span>{{ memberInitial(name) }}</span>
      </template>
    </BaseAvatar>
    <span class="statusDot" :data-status="status" />
  </div>
</template>

<style scoped>
.avatar {
  position: relative;
  display: grid;
  place-items: center;
}

.avatarInner {
  border-radius: 999px;
  font-size: 13px;
  border: 2px solid var(--c-border);
  user-select: none;
}

.avatar[data-role="owner"] .avatarInner {
  border-color: #f2c14d;
}

.avatar[data-role="manager"] .avatarInner {
  border-color: #3dc0b3;
}

.avatar[data-role="member"] .avatarInner {
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

.statusDot[data-status="idle"],
.statusDot[data-status="ready"] {
  background: #2fb46e;
}

.statusDot[data-status="stalling"] {
  background: #dfad3f;
}

.statusDot[data-status="offline"] {
  background: transparent;
  border-color: #9aa8b8;
}

.statusDot[data-status="error"] {
  background: #dc4f4f;
}
</style>
