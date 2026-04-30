export type RoomPlayerConfig = {
  readyBufferAheadSeconds: number;
  readyConfirmDelayMs: number;
  bufferRangeEpsilonSeconds: number;
  endOfMediaEpsilonSeconds: number;
  stallingToErrorMs: number;
  bufferedSeekSettleMs: number;
  hls: {
    enableWorker: boolean;
    lowLatencyMode: boolean;
    maxBufferLength: number;
    maxMaxBufferLength: number;
    backBufferLength: number;
    maxBufferSize: number;
  };
};

export const ROOM_PLAYER_CONFIG: RoomPlayerConfig = {
  readyBufferAheadSeconds: 1.5,
  readyConfirmDelayMs: 180,
  bufferRangeEpsilonSeconds: 0.05,
  endOfMediaEpsilonSeconds: 0.3,
  stallingToErrorMs: 30_000,
  bufferedSeekSettleMs: 420,
  hls: {
    enableWorker: true,
    lowLatencyMode: false,
    maxBufferLength: 300,
    maxMaxBufferLength: 600,
    backBufferLength: 10,
    maxBufferSize: 0,
  },
};
