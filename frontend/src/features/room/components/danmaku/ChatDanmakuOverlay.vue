<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { ChatDanmakuItem } from "@/features/room/danmaku/types";

const props = defineProps<{
  items: ChatDanmakuItem[];
  opacity: number;
  speed: number;
}>();

const emit = defineEmits<{
  expired: [id: string];
}>();

const distances = ref<Record<string, number>>({});
let animationFrame = 0;
let lastFrameAt = 0;

function getItemStyle(item: ChatDanmakuItem) {
  return {
    "--danmaku-lane": item.lane,
    "--danmaku-x": `${distances.value[item.id] ?? 0}px`,
    opacity: String(props.opacity),
  };
}

function getTravelDistance(item: ChatDanmakuItem) {
  return Math.max(320, window.innerWidth || 0) + item.estimatedWidth;
}

function tick(now: number) {
  const delta = lastFrameAt > 0 ? Math.min(48, now - lastFrameAt) : 0;
  lastFrameAt = now;

  if (props.items.length > 0 && delta > 0) {
    const speed = Math.max(0.5, Math.min(2, props.speed));
    const nextDistances = { ...distances.value };
    const expiredIds: string[] = [];

    props.items.forEach((item) => {
      const travelDistance = getTravelDistance(item);
      const basePixelsPerMs = travelDistance / 9000;
      const nextDistance = (nextDistances[item.id] ?? 0) + basePixelsPerMs * speed * delta;

      if (nextDistance >= travelDistance) {
        expiredIds.push(item.id);
      } else {
        nextDistances[item.id] = nextDistance;
      }
    });

    expiredIds.forEach((id) => {
      delete nextDistances[id];
      emit("expired", id);
    });

    distances.value = nextDistances;
  }

  animationFrame = window.requestAnimationFrame(tick);
}

function startAnimationLoop() {
  if (animationFrame) return;
  lastFrameAt = 0;
  animationFrame = window.requestAnimationFrame(tick);
}

function stopAnimationLoop() {
  if (!animationFrame) return;
  window.cancelAnimationFrame(animationFrame);
  animationFrame = 0;
  lastFrameAt = 0;
}

watch(
  () => props.items.map((item) => item.id),
  (ids) => {
    const idSet = new Set(ids);
    const nextDistances: Record<string, number> = {};

    ids.forEach((id) => {
      nextDistances[id] = distances.value[id] ?? 0;
    });

    distances.value = nextDistances;

    if (idSet.size > 0) {
      startAnimationLoop();
    } else {
      stopAnimationLoop();
    }
  },
  { immediate: true },
);

onMounted(() => {
  if (props.items.length > 0) {
    startAnimationLoop();
  }
});
onBeforeUnmount(stopAnimationLoop);
</script>

<template>
  <div class="danmakuOverlay" aria-hidden="true">
    <div
      v-for="item in items"
      :key="item.id"
      class="danmakuItem"
      :style="getItemStyle(item)"
    >
      <BaseAvatar
        class="danmakuAvatar"
        size="xs"
        :src="item.avatarUrl || undefined"
        :name="item.avatarName"
      />
      <span class="danmakuContent">
        <template
          v-for="(segment, index) in item.segments"
          :key="`${item.id}-${index}`"
        >
          <span v-if="segment.type === 'text'" class="danmakuText">{{ segment.text }}</span>
          <img
            v-else
            class="danmakuQface"
            :src="segment.src"
            :alt="segment.alt"
            draggable="false"
          >
        </template>
      </span>
    </div>
  </div>
</template>

<style scoped>
.danmakuOverlay {
  position: absolute;
  inset: 12px 0 auto;
  z-index: 3;
  height: min(44%, 238px);
  overflow: hidden;
  pointer-events: none;
  contain: layout paint;
}

.danmakuItem {
  position: absolute;
  top: calc(var(--danmaku-lane) * 32px);
  left: 100%;
  height: 28px;
  max-width: min(640px, 72vw);
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 3px 10px 3px 4px;
  border-radius: 999px;
  background: rgb(0 0 0 / 0.56);
  color: rgb(250 252 255 / 0.96);
  box-shadow: 0 8px 20px rgb(0 0 0 / 0.22);
  white-space: nowrap;
  will-change: transform;
  transform: translateX(calc(var(--danmaku-x) * -1));
}

.danmakuAvatar {
  flex: 0 0 auto;
}

.danmakuContent {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
  font-weight: 650;
  line-height: 1;
  text-shadow:
    0 1px 2px rgb(0 0 0 / 0.58),
    0 0 8px rgb(0 0 0 / 0.42);
}

.danmakuText {
  overflow: hidden;
  text-overflow: ellipsis;
}

.danmakuQface {
  width: 22px;
  height: 22px;
  object-fit: contain;
  vertical-align: middle;
  -webkit-user-drag: none;
}

@media (max-width: 640px) {
  .danmakuOverlay {
    top: 8px;
    height: min(46%, 180px);
  }

  .danmakuItem {
    top: calc(var(--danmaku-lane) * 30px);
    height: 26px;
    max-width: 84vw;
  }

  .danmakuContent {
    font-size: 13px;
  }

  .danmakuQface {
    width: 20px;
    height: 20px;
  }
}
</style>
