
<template>
  <div>
    <input v-model="url" placeholder="Enter m3u8 URL" />
    <button @click="load">Play</button>
    <div v-if="player">
      <button @click="toggle">{{ playing ? 'Pause' : 'Play' }}</button>
      <input type="range" :max="duration" v-model="progress" @input="seek"/>
      <div>{{ currentTime.toFixed(1) }} / {{ duration.toFixed(1) }} sec</div>
    </div>
    <video ref="video" controls style="display:none"></video>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const url = ref('')
const video = ref(null)
const player = ref(null)
const playing = ref(false)
const progress = ref(0)
const duration = ref(0)
const currentTime = ref(0)

function load() {
  if (!Hls.isSupported()) {
    alert('HLS not supported')
    return
  }
  const hls = new Hls()
  hls.loadSource(url.value)
  hls.attachMedia(video.value)
  player.value = hls
  video.value.onloadedmetadata = () => {
    duration.value = video.value.duration
  }
  video.value.ontimeupdate = () => {
    currentTime.value = video.value.currentTime
    progress.value = video.value.currentTime
  }
}

function toggle() {
  if (video.value.paused) {
    video.value.play()
    playing.value = true
  } else {
    video.value.pause()
    playing.value = false
  }
}

function seek() {
  video.value.currentTime = progress.value
}
</script>

<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
