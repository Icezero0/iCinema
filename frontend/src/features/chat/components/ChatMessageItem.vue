<script setup lang="ts">
import { computed } from "vue";
import RoomMemberAvatar from "@/features/room/components/RoomMemberAvatar.vue";
import { getQfaceLabel, getQfaceUrl } from "@/features/chat/emoji";
import ChatInlineMedia from "./ChatInlineMedia.vue";
import { useAssetsStore } from "@/stores/assets.store";
import type { ChatSegment } from "@/features/chat/types";
import type { MemberStatus } from "@/features/room/types";

const props = defineProps<{
  author: string;
  avatarUrl?: string | null;
  segments: ChatSegment[];
  self?: boolean;
  showAvatar?: boolean;
  showAuthor?: boolean;
  avatarVariant?: "default" | "room";
  role?: "owner" | "manager" | "member";
  status?: MemberStatus;
}>();

const assetsStore = useAssetsStore();
const firstSegment = computed(() => props.segments[0] ?? null);

const isStandaloneMediaMessage = computed(() => (
  props.segments.length === 1 &&
  firstSegment.value?.type === "media" &&
  (firstSegment.value.kind === "image" || firstSegment.value.kind === "sticker")
));

function getSegmentDisplayMode(segment: ChatSegment) {
  if (segment.type !== "media") return "inline" as const;
  return isStandaloneMediaMessage.value ? "block" as const : "inline" as const;
}

function getSegmentLayoutClass(segment: ChatSegment) {
  if (segment.type !== "media") return null;
  return isStandaloneMediaMessage.value ? "segment-media-block" : "segment-media-inline";
}

function getQfaceDisplayUrl(emojiId: string) {
  return assetsStore.getAssetDisplayUrl("qface", emojiId) || getQfaceUrl(emojiId);
}
</script>

<template>
  <div class="messageRow" :class="{ self, compact: showAvatar === false }">
    <RoomMemberAvatar
      v-if="showAvatar !== false && avatarVariant === 'room'"
      class="avatar"
      :name="author"
      :src="avatarUrl"
      :role="role ?? 'member'"
      :status="status ?? 'idle'"
      :size="32"
    />
    <BaseAvatar
      v-else-if="showAvatar !== false"
      class="avatar"
      size="sm"
      :src="avatarUrl || undefined"
      :name="author"
    />
    <div v-else class="avatarSpacer" aria-hidden="true" />

    <div class="content" :class="{ compact: showAuthor === false }">
      <div v-if="showAuthor !== false" class="author">{{ author }}</div>

      <div
        class="bubble"
        :class="{ bubbleless: isStandaloneMediaMessage }"
      >
        <span
          v-for="segment in segments"
          :key="segment.id"
          class="segment"
          :class="[
            `segment-${segment.type}`,
            segment.type === 'media' ? `segment-media-${segment.kind}` : null,
            getSegmentLayoutClass(segment),
          ]"
        >
          <template v-if="segment.type === 'text'">
            {{ segment.content }}
          </template>
          <template v-else-if="segment.type === 'emoji'">
            <ChatInlineMedia
              v-if="getQfaceDisplayUrl(segment.emojiId)"
              kind="emoji"
              context="message"
              display-mode="inline"
              :src="getQfaceDisplayUrl(segment.emojiId) || undefined"
              :alt="getQfaceLabel(segment.emojiId)"
              :emoji-id="segment.emojiId"
              :animated="segment.animated"
            />
            <span v-else>{{ getQfaceLabel(segment.emojiId) }}</span>
          </template>
          <template v-else>
            <ChatInlineMedia
              v-if="segment.src"
              :kind="segment.kind"
              context="message"
              :display-mode="getSegmentDisplayMode(segment)"
              :asset-id="segment.assetId"
              :src="segment.src"
              :alt="segment.alt"
            />
            <ChatInlineMedia
              v-else
              :kind="segment.kind"
              context="message"
              :display-mode="getSegmentDisplayMode(segment)"
              :asset-id="segment.assetId"
              :alt="segment.alt"
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
  align-items: end;
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

.avatarSpacer {
  flex: 0 0 auto;
  width: var(--avatar-size);
  height: 1px;
}

.content {
  flex: 0 1 auto;
  display: grid;
  gap: 6px;
  max-width: min(calc(100% - ((var(--avatar-size) * 2) + var(--avatar-gap))), 420px);
  align-items: start;
  justify-items: start;
}

.content.compact {
  gap: 0;
}

.messageRow.self .content {
  justify-items: end;
}

.author {
  font-size: 12px;
  line-height: 1.2;
  color: var(--c-text-muted);
  padding: 0 2px;
  user-select: none;
}

.bubble {
  box-sizing: border-box;
  width: fit-content;
  max-width: 100%;
  padding: 9px 11px;
  border-radius: 16px;
  border: 1px solid var(--c-border);
  background: color-mix(in srgb, var(--c-surface) 74%, var(--c-bg));
  line-height: 1.6;
  justify-self: start;
}

.messageRow.self .bubble {
  justify-self: end;
}

.bubble.bubbleless {
  padding: 0;
  border: 0;
  background: transparent;
  line-height: 0;
}

.bubble::selection {
  background: rgb(59 130 246 / 0.28);
}

.bubble *::selection {
  background: rgb(59 130 246 / 0.28);
}

.segment {
  font-size: 13px;
  color: var(--c-text);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.segment-media-image,
.segment-media-sticker {
  white-space: normal;
}

.segment-media-block {
  display: block;
  line-height: 0;
}

.segment-media-inline {
  display: inline;
}

.segment-emoji {
  display: inline;
  white-space: normal;
}
</style>
