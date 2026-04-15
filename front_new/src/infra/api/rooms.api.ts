import { http } from "@/infra/http/client";

export type Room = {
  id: number;
  name: string;
  owner_id: number;
  is_public: boolean | null;
  config: string | null;
};

export async function getRoomById(roomId: number) {
  const { data } = await http.get<Room>(`/rooms/${roomId}`);
  return data;
}