<script setup lang="ts">
import { computed, ref } from "vue";
import RoomMemberAvatar from "@/features/room/components/RoomMemberAvatar.vue";
import type { MemberStatus, RoomRole } from "@/features/room/types";

type RoomMemberPanelItem = {
  id: number;
  name: string;
  avatarUrl?: string | null;
  role: RoomRole;
  status: MemberStatus | "idle";
};

const props = defineProps<{
  members: RoomMemberPanelItem[];
  searchPlaceholder: string;
  inviteLabel: string;
  leaveRoomLabel: string;
  loading?: boolean;
  loadingLabel?: string;
  emptyLabel?: string;
}>();

const memberKeyword = ref("");

const filteredMembers = computed(() => {
  const keyword = memberKeyword.value.trim().toLowerCase();
  if (!keyword) return props.members;

  return props.members.filter((member) =>
    member.name.toLowerCase().includes(keyword),
  );
});
</script>

<template>
  <div class="membersPanel">
    <BaseInput
      v-model="memberKeyword"
      :placeholder="searchPlaceholder"
    />

    <div class="membersScrollArea">
      <div v-if="loading" class="membersFeedback">
        {{ loadingLabel || "Loading…" }}
      </div>
      <div v-else-if="filteredMembers.length === 0" class="membersFeedback">
        {{ emptyLabel || "No members yet." }}
      </div>
      <div v-else class="memberList">
        <div
          v-for="member in filteredMembers"
          :key="member.id"
          class="memberItem"
        >
          <RoomMemberAvatar
            :name="member.name"
            :src="member.avatarUrl"
            :role="member.role"
            :status="member.status"
          />
          <div class="memberMeta">
            <div class="memberName">{{ member.name }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="membersFooter">
      <BaseButton variant="primary">
        {{ inviteLabel }}
      </BaseButton>
      <BaseButton variant="danger">
        {{ leaveRoomLabel }}
      </BaseButton>
    </div>
  </div>
</template>

<style scoped>
.membersPanel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 14px;
  height: 100%;
  min-height: 0;
  align-self: stretch;
}

.membersScrollArea {
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-gutter: stable;
  padding-top: 2px;
  padding-bottom: 4px;
  padding-left: 6px;
  padding-right: 6px;
  margin-left: -14px;
  margin-right: -14px;
}

.memberList {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
}

.membersFeedback {
  min-height: 100%;
  display: grid;
  place-items: center;
  color: var(--c-text-muted);
  font-size: 13px;
  text-align: center;
  padding: 18px;
}

.memberItem {
  padding: 6px 2px 4px;
  display: grid;
  justify-items: center;
  align-content: start;
  gap: 6px;
}

.memberMeta {
  width: 100%;
  display: grid;
  justify-items: center;
}

.memberName {
  font-size: 13px;
  color: var(--c-text);
  max-width: 5em;
  margin: 0 auto;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.membersFooter {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding-top: 2px;
}

.membersFooter :deep(button) {
  width: 100%;
  justify-content: center;
}

@media (max-width: 800px) {
  .membersFooter {
    grid-template-columns: 1fr;
  }
}

</style>
