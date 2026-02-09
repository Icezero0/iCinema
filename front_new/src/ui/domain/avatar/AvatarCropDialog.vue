<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { Cropper } from "vue-advanced-cropper";
import "vue-advanced-cropper/dist/style.css";

import BaseDialog from "@/ui/base/BaseDialog.vue";
import BaseCard from "@/ui/base/BaseCard.vue";
import BaseButton from "@/ui/base/BaseButton.vue";

const { t } = useI18n();

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    file: File | null;
    title: string;

    outputSize?: number; // avatar 建议 512
    outputMime?: "image/jpeg" | "image/png";
    outputQuality?: number;

    closeOnOverlay?: boolean;
  }>(),
  {
    outputSize: 512,
    outputMime: "image/jpeg",
    outputQuality: 0.9,
    closeOnOverlay: false,
  },
);

const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
  (e: "done", dataUrl: string): void;
  (e: "cancel"): void;
}>();

const cropperRef = ref<any>(null);
const imageSrc = ref<string>("");

let objectUrl = "";

function close() {
  emit("update:modelValue", false);
}

function cleanup() {
  if (objectUrl) {
    URL.revokeObjectURL(objectUrl);
    objectUrl = "";
  }
  imageSrc.value = "";
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) {
      cleanup();
      return;
    }
    if (!props.file) return;

    cleanup();
    objectUrl = URL.createObjectURL(props.file);
    imageSrc.value = objectUrl;
  },
);

onBeforeUnmount(() => cleanup());

function onCancel() {
  emit("cancel");
  close();
}

function rotateLeft() {
  cropperRef.value?.rotate(-90);
}
function rotateRight() {
  cropperRef.value?.rotate(90);
}
function reset() {
  cropperRef.value?.reset();
}

function usePhoto() {
  const result = cropperRef.value?.getResult();
  if (!result?.canvas) return;

  const canvas = result.canvas;
  const out = document.createElement("canvas");
  out.width = props.outputSize;
  out.height = props.outputSize;

  const ctx = out.getContext("2d");
  if (!ctx) return;

  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(canvas, 0, 0, out.width, out.height);

  const dataUrl = out.toDataURL(props.outputMime, props.outputQuality);
  emit("done", dataUrl);
  close();
}
</script>

<template>
  <BaseDialog
    :modelValue="modelValue"
    :closeOnOverlay="closeOnOverlay"
    :closeOnEsc="true"
    :maxWidth="760"
    ariaLabel="Avatar crop dialog"
    @update:modelValue="(v) => emit('update:modelValue', v)"
    @close="onCancel"
  >
    <BaseCard class="card">
      <div class="top">
        <div class="title">{{ title }}</div>
      </div>

      <div class="cropArea">
        <Cropper
          ref="cropperRef"
          class="cropper"
          :src="imageSrc"
          :stencil-props="{ aspectRatio: 1 }"
          :transformations="true"
          :auto-zoom="true"
          :wheel-resize="true"
          :background="false"
          :resize-image="false"
          :default-size="
            ({
              imageSize,
            }: {
              imageSize: { width: number; height: number };
            }) => ({
              width: imageSize.width,
              height: imageSize.height,
            })
          "
        />
      </div>

      <div class="toolbar">
        <BaseButton variant="default" @click="rotateLeft">⟲</BaseButton>
        <BaseButton variant="default" @click="rotateRight">⟳</BaseButton>
        <BaseButton variant="default" @click="reset">
          {{ t("profile.crop.reset") }}
        </BaseButton>

        <div class="spacer" />

        <BaseButton variant="default" @click="onCancel">
          {{ t("common.cancel") }}
        </BaseButton>
        <BaseButton variant="primary" @click="usePhoto">
          {{ t("profile.crop.use") }}
        </BaseButton>
      </div>
    </BaseCard>
  </BaseDialog>
</template>

<style scoped>
.card {
  padding: 16px;
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  border-radius: 16px;
  box-shadow: var(--shadow-lg, 0 10px 30px rgb(0 0 0 / 0.18));
}

.top {
  display: flex;
  justify-content: center;
  padding: 4px 0 12px;
}

.title {
  font-size: 14px;
  font-weight: 650;
  color: var(--c-text);
}

.cropArea {
  height: 460px;
  border: 1px solid var(--c-border);
  border-radius: 14px;
  overflow: hidden;
  background: var(--c-bg);
  box-shadow: inset 0 0 0 1px var(--c-border);
}

.cropper {
  width: 100%;
  height: 100%;
}

.cropper :deep(.vue-advanced-cropper__background) {
  background: color-mix(in srgb, var(--c-surface) 80%, var(--c-bg)) !important;
}

.cropper :deep(.vue-advanced-cropper__background-pattern) {
  opacity: 0.28 !important;
  filter: saturate(0.6);
}

.cropper :deep(.vue-advanced-cropper__foreground) {
  background: rgb(0 0 0 / 0.38) !important;
}

.toolbar {
  margin-top: 12px;
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.spacer {
  flex: 1;
}
</style>
