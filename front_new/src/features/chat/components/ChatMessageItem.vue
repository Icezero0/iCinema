<script setup lang="ts">
import { computed } from "vue";
import RoomMemberAvatar from "@/features/room/components/RoomMemberAvatar.vue";
import { getChatEmojiLabel, getChatEmojiUrl } from "@/features/chat/emoji";
import ChatInlineMedia from "./ChatInlineMedia.vue";
import type { ChatSection } from "@/features/chat/types";

const props = defineProps<{
  author: string;
  sections: ChatSection[];
  self?: boolean;
  avatarVariant?: "default" | "room";
  role?: "owner" | "manager" | "member";
  status?: "playing" | "paused" | "buffering" | "offline" | "error" | "idle";
}>();

const isStandaloneMediaMessage = computed(() => (
  props.sections.length === 1 &&
  props.sections[0].type === "image" &&
  (props.sections[0].kind === "image" || props.sections[0].kind === "sticker")
));

function getSectionDisplayMode(section: ChatSection) {
  if (section.type !== "image") return "inline" as const;
  return isStandaloneMediaMessage.value ? "block" as const : "inline" as const;
}

function getSectionLayoutClass(section: ChatSection) {
  if (section.type !== "image") return null;
  return isStandaloneMediaMessage.value ? "section-image-block" : "section-image-inline";
}
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

      <div
        class="bubble"
        :class="{ bubbleless: isStandaloneMediaMessage }"
      >
        <span
          v-for="section in sections"
          :key="section.id"
          class="section"
          :class="[
            `section-${section.type}`,
            section.type === 'image' ? `section-image-${section.kind ?? 'image'}` : null,
            getSectionLayoutClass(section),
          ]"
        >
          <template v-if="section.type === 'text'">
            {{ section.content }}
          </template>
          <template v-else-if="section.type === 'emoji'">
            <ChatInlineMedia
              v-if="getChatEmojiUrl(section.emojiId)"
              kind="emoji"
              context="message"
              display-mode="inline"
              :src="getChatEmojiUrl(section.emojiId) || undefined"
              :alt="getChatEmojiLabel(section.emojiId)"
            />
            <span v-else>{{ getChatEmojiLabel(section.emojiId) }}</span>
          </template>
          <template v-else>
            <ChatInlineMedia
              v-if="section.src"
              :kind="(section.kind ?? 'image') as 'image' | 'sticker'"
              context="message"
              :display-mode="getSectionDisplayMode(section)"
              :src="section.src"
              :alt="section.alt"
            />
            <ChatInlineMedia
              v-else
              :kind="(section.kind ?? 'image') as 'image' | 'sticker'"
              context="message"
              :display-mode="getSectionDisplayMode(section)"
              :alt="section.alt"
            />
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
  user-select: none;
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

.bubble.bubbleless {
  padding: 0;
  border: 0;
  background: transparent;
}

.bubble::selection {
  background: rgb(59 130 246 / 0.28);
}

.bubble *::selection {
  background: rgb(59 130 246 / 0.28);
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
  white-space: normal;
}

.section-image-block {
  display: block;
}

.section-image-inline {
  display: inline;
}

.section-image-emoji {
  display: inline;
  white-space: normal;
}

.section-emoji {
  display: inline;
  white-space: normal;
}
</style>
