<script setup lang="ts">
import { computed, ref, watch } from "vue";

type AvatarSize = "xs" | "sm" | "md" | "lg";
type AvatarShape = "circle" | "square" | "rounded";
type AvatarFit = "scale-down" | "contain" | "cover";

const props = withDefaults(
  defineProps<{
    src?: string;
    name?: string;
    alt?: string;

    // 尺寸：只用语义档位，保证全站一致
    size?: AvatarSize;

    // 形状：圆 / 方 / 圆角方
    shape?: AvatarShape;

    // 边框：不传或为 0 => 无边框
    borderWidth?: number; // px
    borderColor?: string;

    // 图片显示策略：默认“先缩小，不裁剪”
    // - scale-down：图片大就缩小，小就保持原样（最符合你的描述）
    // - contain：总是等比完整显示（可能出现留白）
    // - cover：填满容器（会裁掉部分）
    fit?: AvatarFit;

    loading?: "lazy" | "eager";
    interactive?: boolean;
  }>(),
  {
    size: "sm",
    shape: "circle",
    fit: "scale-down",
    loading: "lazy",
    interactive: false,
  }
);

const SIZE_MAP: Record<AvatarSize, number> = {
  xs: 24,
  sm: 32,
  md: 40,
  lg: 48,
};

const errored = ref(false);

watch(
  () => props.src,
  () => {
    errored.value = false;
  }
);

const showImg = computed(() => !!props.src && !errored.value);

const sizePx = computed(() => SIZE_MAP[props.size]);

const hasBorder = computed(() => (props.borderWidth ?? 0) > 0);

const rootStyle = computed(() => ({
  width: `${sizePx.value}px`,
  height: `${sizePx.value}px`,
}));

const maskStyle = computed(() => ({
  borderWidth: hasBorder.value ? `${props.borderWidth}px` : undefined,
  borderStyle: hasBorder.value ? "solid" : undefined,
  borderColor: hasBorder.value ? (props.borderColor ?? "var(--c-border)") : undefined,
}));

const imgStyle = computed(() => ({
  objectFit: props.fit,
}));

const label = computed(() => props.alt || props.name || "avatar");

const initial = computed(() => {
  const s = (props.name ?? "").trim();
  return (s[0] ?? "U").toUpperCase();
});

function onImgError() {
  errored.value = true;
}
</script>

<template>
  <!-- 外层：不裁剪（保证 badge 不会被切掉） -->
  <div
    class="avatar"
    :class="[{ interactive }]"
    :style="rootStyle"
    role="img"
    :aria-label="label"
  >
    <!-- 内层 mask：负责形状 +（必要时）裁剪 -->
    <div class="mask" :class="`shape-${shape}`" :style="maskStyle">
      <img
        v-if="showImg"
        class="img"
        :src="src"
        :alt="label"
        :loading="loading"
        decoding="async"
        :style="imgStyle"
        @error="onImgError"
      />

      <slot v-else name="fallback">
        <span class="fallback">{{ initial }}</span>
      </slot>
    </div>

    <!-- badge 放外层，不受 mask 的 overflow 影响 -->
    <slot name="badge" />
  </div>
</template>

<style scoped>
/* 外层只负责占位与交互，不做裁剪 */
.avatar {
  position: relative;
  display: inline-grid;
  place-items: center;
}

/* 内层 mask 才是“真正的头像壳” */
.mask {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;

  background: color-mix(in srgb, var(--c-surface) 74%, white);
  color: var(--c-text);
}

/* 形状 + 裁剪策略
   - square：不需要裁剪（overflow: visible）
   - rounded/circle：要裁剪成对应形状（overflow: hidden）
*/
.mask.shape-square {
  border-radius: 0;
  overflow: visible;
}

.mask.shape-rounded {
  border-radius: var(--r-3);
  overflow: hidden;
}

.mask.shape-circle {
  border-radius: 999px;
  overflow: hidden;
}

/* 图片：
   - width/height 100% 保证不会撑爆容器
   - object-fit 由 props.fit 决定（默认 scale-down：先缩小）
*/
.img {
  width: 100%;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
  display: block;
}

/* fallback */
.fallback {
  font-size: 0.75rem;
  font-weight: 700;
  line-height: 1;
  color: var(--c-text);
}

/* 可选交互态 */
.avatar.interactive {
  cursor: pointer;
}
.avatar.interactive:focus-visible .mask {
  outline: 2px solid var(--c-border);
  outline-offset: 2px;
}
</style>
