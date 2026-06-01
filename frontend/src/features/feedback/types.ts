import type { Component } from "vue";

export type ContactMethodItem = {
  key: "email" | "github" | "qq";
  title: string;
  value: string;
  href: string;
  action: string;
  icon: Component;
};
