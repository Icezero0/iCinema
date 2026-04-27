<script setup lang="ts">
import ChatPanel from "@/features/chat/components/ChatPanel.vue";
import type { ChatMessage, ChatSegment } from "@/features/chat/types";

defineProps<{
  roomKey: number;
  messages: ChatMessage[];
  sendLabel: string;
  loading?: boolean;
  sending?: boolean;
  loadingHistory?: boolean;
  hasOlder?: boolean;
  error?: string | null;
  loadingLabel: string;
  emptyLabel: string;
  sendMessage?: (segments: ChatSegment[]) => Promise<void> | void;
}>();

const emit = defineEmits<{
  send: [segments: ChatSegment[]];
  loadOlder: [];
}>();
</script>

<template>
  <div class="panelBody chatPanelBody">
    <ChatPanel
      class="chatPanelFill"
      :room-key="roomKey"
      :messages="messages"
      :send-label="sendLabel"
      :loading="loading"
      :sending="sending"
      :loading-history="loadingHistory"
      :has-older="hasOlder"
      :error="error"
      :loading-label="loadingLabel"
      :empty-label="emptyLabel"
      :send-message="sendMessage"
      @send="emit('send', $event)"
      @load-older="emit('loadOlder')"
    />
  </div>
</template>

<style scoped>
.panelBody {
  display: grid;
  gap: 14px;
  min-height: 0;
  overflow: auto;
}

.chatPanelBody {
  grid-template-rows: minmax(0, 1fr);
  padding: 0 14px 14px;
  overflow: hidden;
}

:deep(.chatPanelFill) {
  height: 100%;
  min-height: 0;
}

@media (max-width: 720px) {
  .chatPanelBody {
    min-height: 0;
    height: 100%;
  }

  :deep(.chatPanelFill) {
    min-height: 100%;
  }
}
</style>
