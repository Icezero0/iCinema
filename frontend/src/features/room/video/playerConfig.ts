export type RoomPlayerConfig = {
  readyRecoveryBufferAheadSeconds: number;
  readyConfirmDelayMs: number;
  bufferRangeEpsilonSeconds: number;
  hlsStartupGapToleranceSeconds: number;
  endOfMediaEpsilonSeconds: number;
  stallingToErrorMs: number;
  stallingProgressEpsilonSeconds: number;
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
  readyRecoveryBufferAheadSeconds: 10,
  readyConfirmDelayMs: 180,
  bufferRangeEpsilonSeconds: 0.05,
  hlsStartupGapToleranceSeconds: 0.25,
  endOfMediaEpsilonSeconds: 0.3,
  stallingToErrorMs: 30_000,
  stallingProgressEpsilonSeconds: 0.25,
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
