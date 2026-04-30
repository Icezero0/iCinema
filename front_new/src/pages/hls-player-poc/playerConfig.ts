export type HlsPocPlayerConfig = {
  readyBufferAheadSeconds: number;
  readyConfirmDelayMs: number;
  bufferRangeEpsilonSeconds: number;
  endOfMediaEpsilonSeconds: number;
  stallingToErrorMs: number;
  hls: {
    enableWorker: boolean;
    lowLatencyMode: boolean;
    maxBufferLength: number;
    maxMaxBufferLength: number;
    backBufferLength: number;
    maxBufferSize: number;
  };
};

export const HLS_POC_PLAYER_CONFIG: HlsPocPlayerConfig = {
  readyBufferAheadSeconds: 1.5,
  readyConfirmDelayMs: 180,
  bufferRangeEpsilonSeconds: 0.05,
  endOfMediaEpsilonSeconds: 0.3,
  stallingToErrorMs: 30_000,
  hls: {
    enableWorker: true,
    lowLatencyMode: false,
    maxBufferLength: 300,
    maxMaxBufferLength: 600,
    backBufferLength: 10,
    maxBufferSize: 0,
  },
};
