<script setup lang="ts">
import RoomMemberAvatar from "@/features/room/components/RoomMemberAvatar.vue";
import { getChatEmojiLabel, getChatEmojiUrl } from "@/features/chat/emoji";
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
        <span
          v-for="section in sections"
          :key="section.id"
          class="section"
          :class="[
            `section-${section.type}`,
            section.type === 'image' ? `section-image-${section.kind ?? 'image'}` : null,
          ]"
        >
          <template v-if="section.type === 'text'">
            {{ section.content }}
          </template>
          <template v-else-if="section.type === 'emoji'">
            <img
              v-if="getChatEmojiUrl(section.emojiId)"
              class="inlineImage inlineImage-emoji"
              :src="getChatEmojiUrl(section.emojiId) || undefined"
              :alt="getChatEmojiLabel(section.emojiId)"
            >
            <span v-else>{{ getChatEmojiLabel(section.emojiId) }}</span>
          </template>
          <template v-else>
            <img
              v-if="section.src"
              class="inlineImage"
              :class="`inlineImage-${section.kind ?? 'image'}`"
              :src="section.src"
              :alt="section.alt"
            >
            <div v-else class="imagePlaceholder">
              <span class="imageLabel">{{ section.alt }}</span>
            </div>
          </template>
        </span>
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
  line-height: 1.6;
}

.section {
  font-size: 13px;
  color: var(--c-text);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.section-image-image,
.section-image-sticker {
  display: block;
  margin-top: 8px;
}

.section-image-emoji {
  display: inline;
  white-space: normal;
}

.section-emoji {
  display: inline;
  white-space: normal;
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

.inlineImage {
  display: block;
  width: min(100%, 280px);
  max-width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--c-primary) 18%, var(--c-border));
}

.inlineImage-emoji {
  display: inline-block;
  width: 1.35em;
  height: 1.35em;
  margin: 0 0.12em 0 0.08em;
  aspect-ratio: auto;
  object-fit: contain;
  border: 0;
  border-radius: 0;
  background: transparent;
  vertical-align: -0.24em;
}

.inlineImage-sticker {
  width: min(100%, 160px);
  aspect-ratio: 1;
  object-fit: contain;
  background: color-mix(in srgb, var(--c-surface) 88%, white);
}

.imageLabel {
  font-size: 12px;
  color: var(--c-text-muted);
}
</style>
