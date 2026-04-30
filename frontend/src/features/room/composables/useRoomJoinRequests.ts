import { computed, ref, type ComputedRef, type Ref } from "vue";
import {
  getRoomJoinRequests,
  type RoomJoinRequest,
} from "@/infra/api/rooms.api";
import {
  approveJoinRequestById,
  rejectJoinRequestById,
} from "@/infra/api/join-requests.api";
import { useEntitiesStore } from "@/stores/entities.store";
import { formatLocalDateTime } from "@/utils/datetime";
import { getBackendErrorMessage } from "@/infra/http/client";

type UseRoomJoinRequestsOptions = {
  roomId: ComputedRef<number>;
  canManageRoomRequests: ComputedRef<boolean>;
  optimisticInviteUserIds: Ref<number[]>;
  t: (key: string) => string;
};

function extractErrorMessage(error: any, fallback: string) {
  return getBackendErrorMessage(error) || fallback;
}

export function useRoomJoinRequests(options: UseRoomJoinRequestsOptions) {
  const entitiesStore = useEntitiesStore();

  const requestsLoading = ref(false);
  const requestsError = ref("");
  const requestsLoaded = ref(false);
  const roomJoinRequests = ref<RoomJoinRequest[]>([]);
  const requestActionIds = ref<number[]>([]);

  const roomRequestItems = computed(() => roomJoinRequests.value.map((request) => {
    const isApply = request.source === "apply";
    const user = isApply ? request.initiator : request.target;

    return {
      id: request.id,
      user:
        user?.username ||
        user?.email ||
        `User #${isApply ? request.initiator_user_id : request.target_user_id}`,
      note: isApply
        ? options.t("room.requests.applyNote")
        : options.t("room.requests.inviteNote"),
      time: formatLocalDateTime(request.updated_at || request.created_at),
    };
  }));

  const pendingMemberInviteStates = computed(() => {
    const pendingStates = roomJoinRequests.value
      .filter((request) => request.status === "pending")
      .map((request) => ({
        userId:
          request.source === "apply"
            ? request.initiator_user_id
            : request.target_user_id,
        source: request.source,
      }));
    const knownPendingUserIds = new Set(pendingStates.map((state) => state.userId));
    const optimisticInviteStates = options.optimisticInviteUserIds.value
      .filter((userId) => !knownPendingUserIds.has(userId))
      .map((userId) => ({
        userId,
        source: "invite" as const,
      }));

    return [
      ...pendingStates,
      ...optimisticInviteStates,
    ];
  });

  async function fetchRoomRequests(fetchOptions?: { force?: boolean }) {
    if (!options.roomId.value || !options.canManageRoomRequests.value) {
      roomJoinRequests.value = [];
      requestsLoaded.value = false;
      requestsError.value = "";
      return;
    }

    if (requestsLoading.value) return;
    if (!fetchOptions?.force && requestsLoaded.value) return;

    requestsLoading.value = true;
    requestsError.value = "";

    try {
      const response = await getRoomJoinRequests(options.roomId.value, {
        page: 1,
        page_size: 30,
        status: "pending",
      });
      roomJoinRequests.value = response.items;
      entitiesStore.upsertJoinRequests(response.items);
      requestsLoaded.value = true;
    } catch (e: any) {
      requestsError.value = extractErrorMessage(e, options.t("room.requestsLoadFailed"));
    } finally {
      requestsLoading.value = false;
    }
  }

  function isRequestActionLoading(requestId: number) {
    return requestActionIds.value.includes(requestId);
  }

  function setRequestActionLoading(requestId: number, loading: boolean) {
    requestActionIds.value = loading
      ? [...new Set([...requestActionIds.value, requestId])]
      : requestActionIds.value.filter((id) => id !== requestId);
  }

  async function approveRequest(requestId: number) {
    setRequestActionLoading(requestId, true);
    requestsError.value = "";

    try {
      await approveJoinRequestById(requestId);
      await fetchRoomRequests({ force: true });
    } catch (e: any) {
      requestsError.value = extractErrorMessage(e, options.t("room.requestsLoadFailed"));
    } finally {
      setRequestActionLoading(requestId, false);
    }
  }

  async function rejectRequest(requestId: number) {
    setRequestActionLoading(requestId, true);
    requestsError.value = "";

    try {
      await rejectJoinRequestById(requestId);
      await fetchRoomRequests({ force: true });
    } catch (e: any) {
      requestsError.value = extractErrorMessage(e, options.t("room.requestsLoadFailed"));
    } finally {
      setRequestActionLoading(requestId, false);
    }
  }

  function resetRoomRequestsState() {
    roomJoinRequests.value = [];
    requestsLoaded.value = false;
    requestsError.value = "";
    requestActionIds.value = [];
  }

  return {
    requestsLoading,
    requestsError,
    roomJoinRequests,
    roomRequestItems,
    pendingMemberInviteStates,
    fetchRoomRequests,
    isRequestActionLoading,
    approveRequest,
    rejectRequest,
    resetRoomRequestsState,
  };
}
