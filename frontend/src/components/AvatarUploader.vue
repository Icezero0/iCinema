<template>
  <div class="avatar-upload-wrapper">
    <label for="avatar-upload">
      <img :src="modelValue" alt="avatar" class="avatar-large clickable" />
      <input id="avatar-upload" type="file" accept="image/*" @change="onAvatarChange" style="display:none" />
    </label>
    <span class="avatar-tip">点击头像上传图片</span>
    <div v-if="showCropper" class="cropper-modal">
      <div class="cropper-container">
        <Cropper
          ref="cropperRef"
          :src="cropperImg"
          :aspect-ratio="1"
          :view-mode="1"
          :auto-crop-area="1"
          :background="false"
          :responsive="true"
          :rotatable="false"
          :zoomable="true"
          style="width:512px;height:512px;"
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
.avatar-upload-wrapper { display: flex; flex-direction: column; align-items: center; }
.avatar-large {
  width: 256px;
  height: 256px;
  border-radius: 16px; 
  object-fit: cover;
  border: 2px solid #eee;
  background: #fff;
  margin: 0.5rem 0;
  display: block;
  box-shadow: 0 4px 24px rgba(0,0,0,0.12);
  transition: box-shadow 0.2s;
  cursor: pointer;
  user-select: none;
}
.avatar-large:hover {
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
}
.avatar-tip {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
  pointer-events: none;
  user-select: none;
}
.cropper-modal { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; opacity: 1; }
.cropper-container { background: #fff; padding: 20px; border-radius: 8px; }
.cropper-btn-group { display: flex; justify-content: space-between; margin-top: 10px; }
.save-button, .cancel-button { padding: 6px 16px; border: none; border-radius: 4px; cursor: pointer; }
.save-button { background: #4caf50; color: #fff; }
.cancel-button { background: #f44336; color: #fff; }
</style>
