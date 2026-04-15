import { createI18n } from "vue-i18n";
import en from "./locales/en";
import zhCN from "./locales/zh-CN";

/** 语言枚举：后续加语言只需要扩展这里 + messages */
export const LOCALES = ["en", "zh-CN"] as const;
export type Locale = (typeof LOCALES)[number];

/**
 * 菜单渲染用的选项（可扩展）
 * - value: locale code
 * - label: UI 显示名称（不强制 i18n，语言名一般固定即可）
 */
export const LOCALE_OPTIONS: ReadonlyArray<{ value: Locale; label: string }> = [
  { value: "en", label: "English" },
  { value: "zh-CN", label: "中文" },
] as const;

const STORAGE_KEY = "locale";

/**
 * 规则：
 * - 用户第一次访问：根据系统/浏览器语言决定（zh* => zh-CN；其他 => en）
 * - 用户一旦手动切换：写入 localStorage，之后以 localStorage 为准
 */
function detectInitialLocale(): Locale {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === "en" || saved === "zh-CN") return saved;

  const nav = (navigator.language || "").toLowerCase();
  if (nav.startsWith("zh")) return "zh-CN";

  return "en";
}

export const i18n = createI18n({
  legacy: false,
  locale: detectInitialLocale(),
  fallbackLocale: "en",
  messages: {
    en,
    "zh-CN": zhCN,
  },
});

/** 获取当前语言（组件内用） */
export function getLocale(): Locale {
  return i18n.global.locale.value as Locale;
}

/** 设置语言：更新 i18n + 持久化 + 同步 html lang */
export function setLocale(locale: Locale) {
  i18n.global.locale.value = locale;
  localStorage.setItem(STORAGE_KEY, locale);
  document.documentElement.lang = locale;
}
