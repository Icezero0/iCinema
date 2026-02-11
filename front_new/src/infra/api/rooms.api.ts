import { http } from "@/infra/http/client";

export type Room = {
  id: number;
  name: string;
  is_public: boolean;
  owner_id: number;
  created_at: string;
  is_active: boolean;
  config: any | null;
};

/**
 * GET /rooms/{id}
 */
export async function getRoomById(roomId: number) {
  const { data } = await http.get<Room>(`/rooms/${roomId}`);
  return data;
}
