<template>
  <div class="avatar-upload-wrapper">
    <label for="avatar-upload">
      <img :src="modelValue" alt="avatar" class="avatar-large clickable" />
      <input id="avatar-upload" type="file" accept="image/*" @change="onAvatarChange" style="display:none" />
    </label>
    <span class="avatar-tip">点击头像上传图片</span>    <div v-if="showCropper" class="cropper-modal">
      <div class="cropper-container">
        <Cropper
          ref="cropperRef"
          :src="cropperImg"
          :aspect-ratio="1"
          :view-mode="1"
          :auto-crop-area="0.8"
          :background="true"
          :responsive="true"
          :rotatable="false"
          :zoomable="true"
          :scalable="true"
          :crop-box-movable="true"
          :crop-box-resizable="true"
          class="cropper-instance"
        />
        <div class="cropper-btn-group">
          <button type="button" class="save-button" @click="handleCrop">确定</button>
          <button type="button" class="cancel-button" @click="handleCancelCrop">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, defineProps, defineEmits } from 'vue';
import '@/styles/components/user/avatar-uploader.css';
import Cropper from 'vue-cropperjs';
import 'cropperjs/dist/cropper.css';

const props = defineProps({
  modelValue: String
});
const emit = defineEmits(['update:modelValue']);

const showCropper = ref(false);
const cropperImg = ref('');
const cropperRef = ref();

function onAvatarChange(e) {
  const file = e.target.files[0];
  if (file) {
    const reader = new FileReader();
    reader.onload = (event) => {
      cropperImg.value = event.target.result;
      showCropper.value = true;
    };
    reader.readAsDataURL(file);
  }
}

function handleCrop() {
  const canvas = cropperRef.value.getCroppedCanvas({ width: 512, height: 512 });
  if (canvas) {
    emit('update:modelValue', canvas.toDataURL('image/jpeg'));
    showCropper.value = false;
  }
}

function handleCancelCrop() {
  showCropper.value = false;
}
</script>

<style scoped>
.cropper-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  opacity: 1 !important;
}

.cropper-container {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  opacity: 1 !important;
}

.cropper-instance {
  width: 500px;
  height: 400px;
  max-width: 80vw;
  max-height: 60vh;
  opacity: 1 !important;
}

.cropper-btn-group {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.save-button,
.cancel-button {
  padding: 8px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.save-button {
  background: #28a745;
  color: white;
}

.save-button:hover {
  background: #218838;
}

.cancel-button {
  background: #dc3545;
  color: white;
}

.cancel-button:hover {
  background: #c82333;
}

/* Override cropper.js styles to fix transparency issues */
:deep(.cropper-container) {
  background-color: #f8f9fa !important;
  opacity: 1 !important;
}

:deep(.cropper-wrap-box) {
  background-color: #000 !important;
  opacity: 1 !important;
}

:deep(.cropper-canvas) {
  background-color: transparent !important;
  opacity: 1 !important;
}

:deep(.cropper-modal) {
  background-color: rgba(0, 0, 0, 0.5) !important;
  opacity: 1 !important;
}

:deep(.cropper-view-box) {
  outline: 2px solid #007bff !important;
  opacity: 1 !important;
}

:deep(.vue-cropper) {
  opacity: 1 !important;
}

@media (max-width: 768px) {
  .cropper-instance {
    width: 90vw;
    height: 70vw;
  }
  
  .cropper-container {
    padding: 15px;
    margin: 10px;
  }
}
</style>
