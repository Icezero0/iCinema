<script setup lang="ts">
import { ref, watch } from "vue";
import ChatMessageItem from "./ChatMessageItem.vue";
import ChatComposer from "./ChatComposer.vue";
import type { ChatMessage, ChatSection } from "@/features/chat/types";

const props = defineProps<{
  messages: ChatMessage[];
  sendLabel?: string;
  selfAuthor?: string;
}>();
const localMessages = ref<ChatMessage[]>([]);

function cloneMessages(messages: ChatMessage[]) {
  return messages.map((message) => ({
    ...message,
    sections: message.sections.map((section) => ({ ...section })),
  }));
}

watch(
  () => props.messages,
  (messages) => {
    localMessages.value = cloneMessages(messages);
  },
  { immediate: true },
);

function handleSend(sections: ChatSection[]) {
  if (sections.length === 0) return;

  const nextMessage: ChatMessage = {
    id: `draft-${Date.now()}`,
    author: props.selfAuthor || "You",
    self: true,
    avatarVariant: "room",
    role: "owner",
    status: "playing",
    sections,
  };

  localMessages.value = [...localMessages.value, nextMessage];
}
</script>

<template>
  <div class="panel">
    <div class="timeline">
      <ChatMessageItem
        v-for="message in localMessages"
        :key="message.id"
        :author="message.author"
        :sections="message.sections"
        :self="message.self"
        :avatar-variant="message.avatarVariant"
        :role="message.role"
        :status="message.status"
      />
    </div>

    <ChatComposer :send-label="sendLabel" @send="handleSend" />
  </div>
</template>

<style scoped>
.panel {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 6px;
  min-height: 0;
}

.timeline {
  display: grid;
  gap: 10px;
  padding-bottom: 6px;
  padding-left: 6px;
  padding-right: 6px;
  margin-left: -14px;
  margin-right: -14px;
  border-bottom: 1px solid var(--c-border);
  min-height: 0;
  overflow: auto;
}
</style>
