export type BilibiliLoginStatus = Readonly<{
  loggedIn: boolean;
  name: string;
  mid: number | null;
  avatarUrl: string | null;
}>;

export type BilibiliVideoInfo = Readonly<{
  bvid: string;
  title: string;
  coverUrl: string | null;
  description: string;
  uploader: string;
  durationSeconds: number;
  pages: ReadonlyArray<Readonly<{
    page: number;
    cid: number;
    title: string;
    durationSeconds: number;
  }>>;
}>;

export type BilibiliLocalMedia = Readonly<{
  bvid: string;
  cid: number;
  page: number;
  duration: number;
  mpd: string;
}>;

declare global {
  interface Window {
    icinemaBilibili?: Readonly<{
      status: (accessToken: string) => Promise<BilibiliLoginStatus>;
      login: (accessToken: string) => Promise<{ opened: true }>;
      logout: (accessToken: string) => Promise<BilibiliLoginStatus>;
      videoInfo: (accessToken: string, bvid: string) => Promise<BilibiliVideoInfo>;
      resolve: (accessToken: string, bvid: string, cid: number) => Promise<BilibiliLocalMedia>;
      onLoginComplete: (callback: (event: { userId: number }) => void) => () => void;
    }>;
  }
}

export const bilibiliDesktop = window.icinemaBilibili;
