<script setup lang="ts">
import RoomMemberAvatar from "@/features/room/components/RoomMemberAvatar.vue";
import type { ChatSection } from "@/features/chat/types";

defineProps<{
  author: string;
  sections: ChatSection[];
  self?: boolean;
  avatarVariant?: "default" | "room";
  role?: "owner" | "manager" | "member";
  status?: "playing" | "paused" | "buffering" | "offline" | "error" | "idle";
}>();
</script>

<template>
  <div class="messageRow" :class="{ self }">
    <RoomMemberAvatar
      v-if="avatarVariant === 'room'"
      class="avatar"
      :name="author"
      :role="role ?? 'member'"
      :status="status ?? 'idle'"
      :size="32"
    />
    <BaseAvatar
      v-else
      class="avatar"
      size="sm"
      :name="author"
    />

    <div class="content">
      <div class="author">{{ author }}</div>

      <div class="bubble">
        <div
          v-for="section in sections"
          :key="section.id"
          class="section"
          :class="`section-${section.type}`"
        >
          <template v-if="section.type === 'text'">
            {{ section.content }}
          </template>
          <template v-else>
            <div class="imagePlaceholder">
              <span class="imageLabel">{{ section.alt }}</span>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.messageRow {
  --avatar-size: 32px;
  --avatar-gap: 10px;
  display: flex;
  gap: var(--avatar-gap);
  align-items: start;
}

.messageRow.self {
  flex-direction: row-reverse;
  justify-content: flex-start;
}

.messageRow.self .content {
  align-items: flex-end;
}

.messageRow.self .author {
  text-align: right;
}

.messageRow.self .bubble {
  background: color-mix(in srgb, var(--c-primary) 9%, var(--c-surface));
  border-color: color-mix(in srgb, var(--c-primary) 24%, var(--c-border));
}

.avatar {
  flex: 0 0 auto;
}

.content {
  flex: 0 1 auto;
  display: grid;
  gap: 6px;
  max-width: min(calc(100% - ((var(--avatar-size) * 2) + var(--avatar-gap))), 420px);
}

.author {
  font-size: 12px;
  line-height: 1.2;
  color: var(--c-text-muted);
  padding: 0 2px;
}

.bubble {
  width: fit-content;
  max-width: 100%;
  padding: 12px;
  border-radius: 16px;
  border: 1px solid var(--c-border);
  background: color-mix(in srgb, var(--c-surface) 74%, var(--c-bg));
  display: grid;
  gap: 8px;
}

.section {
  font-size: 13px;
  color: var(--c-text);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.imagePlaceholder {
  width: min(100%, 280px);
  aspect-ratio: 4 / 3;
  border-radius: 12px;
  border: 1px dashed color-mix(in srgb, var(--c-primary) 22%, var(--c-border));
  background:
    linear-gradient(160deg, color-mix(in srgb, var(--c-surface) 82%, white), color-mix(in srgb, var(--c-surface) 72%, var(--c-bg)));
  display: grid;
  place-items: center;
}

.imageLabel {
  font-size: 12px;
  color: var(--c-text-muted);
}
</style>
