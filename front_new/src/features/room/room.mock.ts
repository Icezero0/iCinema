import type { ChatMessage } from "@/features/chat/types";
import type { MemberStatus, RoomRequestMockItem, RoomRole } from "@/features/room/types";

export function sortMockMembers(
  members: {
    id: number;
    name: string;
    role: RoomRole;
    status: MemberStatus;
    online: boolean;
  }[],
) {
  return [...members].sort((a, b) => {
    if (a.online !== b.online) {
      return a.online ? -1 : 1;
    }

    const roleOrder: Record<RoomRole, number> = {
      owner: 0,
      manager: 1,
      member: 2,
    };

    if (roleOrder[a.role] !== roleOrder[b.role]) {
      return roleOrder[a.role] - roleOrder[b.role];
    }

    return a.id - b.id;
  });
}

export function createMockMembers() {
  return sortMockMembers([
    { id: 1, name: "Icezero", role: "owner" as const, status: "playing" as const, online: true },
    { id: 2, name: "Mika", role: "manager" as const, status: "paused" as const, online: true },
    { id: 3, name: "Aki", role: "member" as const, status: "buffering" as const, online: true },
    { id: 4, name: "Leo", role: "member" as const, status: "offline" as const, online: false },
    { id: 5, name: "Nina", role: "member" as const, status: "playing" as const, online: true },
    { id: 6, name: "Kaito", role: "member" as const, status: "paused" as const, online: true },
    { id: 7, name: "Yuri", role: "manager" as const, status: "buffering" as const, online: true },
    { id: 8, name: "Sora", role: "member" as const, status: "playing" as const, online: true },
    { id: 9, name: "Hana", role: "member" as const, status: "offline" as const, online: false },
    { id: 10, name: "Ren", role: "member" as const, status: "playing" as const, online: true },
    { id: 11, name: "Luna", role: "member" as const, status: "paused" as const, online: true },
    { id: 12, name: "Tao", role: "member" as const, status: "error" as const, online: true },
    { id: 13, name: "星野观影者", role: "member" as const, status: "playing" as const, online: true },
  ]);
}

export function createMockRequests(t: (key: string) => string): RoomRequestMockItem[] {
  return [
    { id: 1, user: "Rin", time: "2 min", note: t("room.mock.requestApply") },
    { id: 2, user: "Noah", time: "8 min", note: t("room.mock.requestInvite") },
    { id: 3, user: "Momo", time: "16 min", note: t("room.mock.requestApply") },
    { id: 4, user: "Ethan", time: "23 min", note: t("room.mock.requestApply") },
    { id: 5, user: "Ava", time: "31 min", note: t("room.mock.requestInvite") },
    { id: 6, user: "Kai", time: "44 min", note: t("room.mock.requestApply") },
    { id: 7, user: "Mina", time: "1 h", note: t("room.mock.requestInvite") },
    { id: 8, user: "Jules", time: "1 h", note: t("room.mock.requestApply") },
    { id: 9, user: "Yuna", time: "2 h", note: t("room.mock.requestApply") },
  ];
}

export function createMockChatMessages(t: (key: string) => string): ChatMessage[] {
  return [
    {
      id: 1,
      author: "Icezero",
      self: true,
      avatarVariant: "room" as const,
      role: "owner" as const,
      status: "playing" as const,
      sections: [{ id: "1-1", type: "text" as const, content: t("room.mock.chatLineOne") }],
    },
    {
      id: 2,
      author: "Mika",
      avatarVariant: "room" as const,
      role: "manager" as const,
      status: "paused" as const,
      sections: [
        { id: "2-1", type: "text" as const, content: t("room.mock.chatLineTwo") },
        { id: "2-2", type: "image" as const, alt: t("room.mock.chatImageAlt") },
      ],
    },
    {
      id: 3,
      author: "Aki",
      avatarVariant: "room" as const,
      role: "member" as const,
      status: "buffering" as const,
      sections: [{ id: "3-1", type: "text" as const, content: t("room.mock.chatLineThree") }],
    },
    {
      id: 4,
      author: "Nina",
      avatarVariant: "room" as const,
      role: "member" as const,
      status: "playing" as const,
      sections: [{ id: "4-1", type: "text" as const, content: "我这边已经对上时间轴了，可以继续。" }],
    },
    {
      id: 5,
      author: "Icezero",
      self: true,
      avatarVariant: "room" as const,
      role: "owner" as const,
      status: "playing" as const,
      sections: [{ id: "5-1", type: "text" as const, content: "好，那我继续往后拖 10 秒。" }],
    },
    {
      id: 6,
      author: "Yuri",
      avatarVariant: "room" as const,
      role: "manager" as const,
      status: "buffering" as const,
      sections: [{ id: "6-1", type: "text" as const, content: "我这里刚刚卡了一下，现在恢复了。" }],
    },
    {
      id: 7,
      author: "Mika",
      avatarVariant: "room" as const,
      role: "manager" as const,
      status: "paused" as const,
      sections: [
        { id: "7-1", type: "text" as const, content: "这张截图是刚刚那一帧，你们看看是不是这里开始不同步。" },
        { id: "7-2", type: "image" as const, alt: t("room.mock.chatImageAlt") },
      ],
    },
    {
      id: 8,
      author: "Icezero",
      self: true,
      avatarVariant: "room" as const,
      role: "owner" as const,
      status: "playing" as const,
      sections: [{ id: "8-1", type: "text" as const, content: "看到了，我这边先手动同步一次。" }],
    },
    {
      id: 9,
      author: "Mika",
      avatarVariant: "room" as const,
      role: "manager" as const,
      status: "paused" as const,
      sections: [
        { id: "9-1", type: "text" as const, content: "我先丢一个平台 emoji 进来，看看 APNG 在消息区能不能直接播放。" },
        {
          id: "9-2",
          type: "emoji" as const,
          emojiId: "0",
          animated: true,
        },
      ],
    },
    {
      id: 10,
      author: "Tao",
      avatarVariant: "room" as const,
      role: "member" as const,
      status: "error" as const,
      sections: [{ id: "10-1", type: "text" as const, content: "我加载报错了，可能得重新进房间。" }],
    },
  ];
}
