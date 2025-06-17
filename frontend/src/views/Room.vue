<template>
  <div class="room-page" :class="{ 'dark-mode': isDarkMode }">
    <div class="ws-status-bar-row">
      <button class="back-home-btn" @click="goHome">返回主页</button>
      <div class="ws-status-bar" :class="wsStatus">
        <span v-if="wsStatus === 'connected'">🟢 已连接</span>
        <span v-else-if="wsStatus === 'connecting'">🟡 正在连接...</span>
        <span v-else>🔴 未连接</span>
      </div>
      <div class="dark-mode-switch">
        <label>
          <input type="checkbox" v-model="isDarkMode" />
          <span>深色模式</span>
        </label>
      </div>
    </div>
    <div class="room-main">
      <!-- 视频播放区域 -->
      <div class="video-area">
        <video ref="videoRef" class="video-player" />
        <!-- 自定义控制栏 -->
        <div class="custom-video-controls">
          <button @click="togglePlay" class="play-btn">
            <span v-if="!isPlaying">
              <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" style="display:block;"><polygon points="8,5 19,12 8,19" /></svg>
            </span>
            <span v-else>
              <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" style="display:block;"><rect x="6" y="5" width="4" height="14"/><rect x="14" y="5" width="4" height="14"/></svg>
            </span>
          </button>
          <!-- 自定义进度条缓冲区可视化 -->
          <div class="video-progress-bar-wrap">
            <div class="video-buffer-bar">
              <template v-for="(range, idx) in bufferedRanges" :key="idx">
                <div class="buffered-segment" :style="{ left: range.start + '%', width: (range.end - range.start) + '%' }"></div>
              </template>
            </div>
            <div class="video-played-bar" :style="{ width: playedPercent + '%' }"></div>
            <input
              type="range"
              min="0"
              :max="duration"
              step="0.1"
              v-model.number="currentTime"
              @input="onSeek"
              class="video-progress-input"
            />
          </div>
          <span class="time-label">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
          <span class="volume-icon" style="margin-left:10px;">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" style="display:block;">
              <polygon points="3,9 3,15 7,15 12,20 12,4 7,9" />
              <path d="M16.5,12c0-1.77-1-3.29-2.5-4.03v8.06C15.5,15.29,16.5,13.77,16.5,12z" />
            </svg>
          </span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            v-model.number="volume"
            @input="onVolumeChange"
            class="volume-slider"
            title="音量"
            style="width: 80px; margin-left: 0;"
          />
        </div>
        <!-- 视频状态提示，放在播放器下方、表单上方 -->
        <div v-if="videoStatusMsg" class="video-status-msg" :class="{ loading: videoLoading }" style="width:100%;margin:10px auto 0 auto;max-width:640px;">
          {{ videoStatusMsg }}
        </div>
        <!-- 视频外链/房间设置表单，紧跟在控制栏下方 -->
        <form class="video-form">
          <div class="form-group">
            <label for="video-url">视频外链：</label>
            <input
              id="video-url"
              v-model="videoUrlInput"
              :disabled="!isOwner"
              type="text"
              placeholder="请输入视频外链地址"
              class="video-url-input"
            />
            <button
              type="button"
              class="video-url-confirm-btn"
              @click="confirmVideoUrl"
              :disabled="!isValidVideoUrl || (!isOwner && videoUrlInput !== videoUrl)"
              style="margin-left:8px;"
            >确认</button>
          </div>
        </form>
        <div v-if="isOwner" class="room-settings card">
          <h4>房间设置</h4>
          <div class="form-group">
            <label for="room-name">房间名称：</label>
            <input id="room-name" v-model="roomName" type="text" class="room-name-input" />
          </div>
          <!-- 其他设置项可继续添加 -->
        </div>
      </div>
      <!-- 消息栏 -->
      <div class="chat-bar">
        <!-- 房间成员区域 -->
        <div class="room-members-label">房间成员</div>
        <div class="room-members-bar" ref="membersBarRef">
          <template v-if="roomMembers.length > 0">
            <div v-for="member in roomMembers" :key="member.id" class="room-member-item" :class="{ owner: member.isOwner }">
              <UserAvatar :src="member.avatarUrl" :alt="member.username" size="38" class="room-member-avatar" />
              <div class="room-member-name">{{ member.username }}</div>
            </div>
          </template>
          <template v-else>
            <div class="room-member-item owner">
              <UserAvatar :src="defaultAvatar" alt="测试用户" size="38" class="room-member-avatar" />
              <div class="room-member-name">测试用户</div>
            </div>
          </template>
        </div>
        <!-- 拖动分隔条 -->
        <div class="drag-divider" @mousedown="startDragDivider"></div>
        <div class="chat-messages" ref="chatMessagesRef">
          <div v-for="(msg, idx) in messages" :key="idx" class="chat-message" :class="{ 'self-message': msg.isSelf }">
            <div class="chat-content-row">
              <UserAvatar :src="msg.avatar || defaultAvatar" :alt="msg.username" size="32" class="chat-avatar" />
              <div class="chat-content-col">
                <div class="chat-username" :class="{ 'self-username': msg.isSelf }">{{ msg.username }}</div>
                <span class="chat-bubble">{{ msg.content }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="chat-input-area">
          <input v-model="inputMsg" @keyup.enter="sendMessage" placeholder="输入消息..." class="chat-input" />
          <button @click="sendMessage" class="chat-send-btn">发送</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed, onBeforeUnmount } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useWebSocketStatus } from '@/composables/useWebSocketStatus';
import { useUserInfo } from '@/composables/useUserInfo.js';
import defaultAvatar from '@/assets/default_avatar.jpg';
import { getImageUrl, API_BASE_URL } from '@/utils/api';
import Hls from 'hls.js';
import UserAvatar from '@/components/UserAvatar.vue';

const { wsStatus } = useWebSocketStatus();
const { avatarUrl, username } = useUserInfo();
const videoUrl = ref(''); // 这里可根据房间/后端接口动态设置
const messages = ref([
  // 示例消息
  { username: '系统', content: '欢迎来到房间！' }
]);
const inputMsg = ref('');
const router = useRouter();
const route = useRoute();
const isDarkMode = ref(true);

// 用户身份模拟：实际应从后端接口/房间信息获取
const isOwner = ref(false); // true为房主，false为成员
const videoUrlInput = ref("");
const roomName = ref("");
const videoStatusMsg = ref("");
const videoLoading = ref(false);
const roomMembers = ref([]);
// 在fetchRoomDetailsAndSetIdentity中填充成员，房主排首位
async function fetchRoomDetailsAndSetIdentity() {
  const roomId = route.query.id || route.params.id;
  if (!roomId) return;
  const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
  try {
    const resp = await fetch(`${API_BASE_URL}/rooms/${roomId}/details`, {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    if (resp.ok) {
      const data = await resp.json();
      // 获取当前登录用户id
      let myId = null;
      try {
        myId = JSON.parse(sessionStorage.getItem('icinema_user')).id;
      } catch (e) {}
      if (data.owner && myId && data.owner.id === myId) {
        isOwner.value = true;
      } else {
        isOwner.value = false;
      }
      if (data.video_url) videoUrlInput.value = data.video_url;
      let members = [];
      if (data.owner) {
        members.push({
          id: data.owner.id,
          username: data.owner.username,
          avatarUrl: data.owner.avatar_path ? getImageUrl(data.owner.avatar_path) : defaultAvatar,
          isOwner: true
        });
      }
      if (data.members && Array.isArray(data.members)) {
        members = members.concat(
          data.members
            .filter(u => !data.owner || u.id !== data.owner.id)
            .map(u => ({
              id: u.id,
              username: u.username,
              avatarUrl: u.avatar_path ? getImageUrl(u.avatar_path) : (u.avatar || ''),
              isOwner: false
            }))
        );
      }
      roomMembers.value = members;
      // console.log('最终成员列表:', members);
    }
  } catch (e) { /* 可加错误提示 */ }
}

function goHome() {
  router.push('/');
}

function sendMessage() {
  if (inputMsg.value.trim()) {
    messages.value.push({
      content: inputMsg.value,
      isSelf: true,
      avatar: avatarUrl.value,
      username: username.value
    });
    inputMsg.value = '';
  }
}

const videoRef = ref(null);
const isPlaying = ref(false);
const currentTime = ref(0);
const duration = ref(0);
const volume = ref(1);
let hlsInstance = null;
const bufferedRanges = ref([]); // [{start: 0, end: 100}, ...]
const playedPercent = computed(() => duration.value ? (currentTime.value / duration.value) * 100 : 0);

function togglePlay() {
  const video = videoRef.value;
  if (!video) return;
  if (video.paused) {
    video.play();
  } else {
    video.pause();
  }
}
function onSeek(e) {
  const video = videoRef.value;
  if (video) {
    video.currentTime = currentTime.value;
  }
}
function onVolumeChange() {
  const video = videoRef.value;
  if (video) {
    video.volume = volume.value;
  }
}
function formatTime(t) {
  t = Math.floor(t || 0);
  const m = String(Math.floor(t / 60)).padStart(2, '0');
  const s = String(Math.floor(t % 60)).padStart(2, '0');
  return `${m}:${s}`;
}

function playVideoWithUrl(url, options = {}) {
  const video = videoRef.value;
  if (!video) return;
  // 清理旧的 hls 实例
  if (hlsInstance) {
    hlsInstance.destroy();
    hlsInstance = null;
  }
  videoStatusMsg.value = "";
  videoLoading.value = true;
  if (url && url.endsWith('.m3u8')) {
    if (Hls.isSupported()) {
      hlsInstance = new Hls();
      hlsInstance.loadSource(url);
      hlsInstance.attachMedia(video);
      hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
        videoLoading.value = false;
        videoStatusMsg.value = "";
        if (options.autoPlay) video.play();
      });
      hlsInstance.on(Hls.Events.ERROR, (event, data) => {
        videoLoading.value = false;
        if (data.fatal) {
          videoStatusMsg.value = 'HLS 播放失败：' + data.type;
        } else {
          videoStatusMsg.value = 'HLS 播放警告：' + data.type;
        }
      });
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = url;
      videoLoading.value = false;
      if (options.autoPlay) video.play();
    } else {
      videoStatusMsg.value = '当前浏览器不支持 HLS(m3u8) 播放';
      videoLoading.value = false;
    }
  } else {
    video.src = url;
    videoLoading.value = false;
    if (options.autoPlay) video.play();
  }
}

function confirmVideoUrl() {
  // 只设置视频地址，不自动播放，状态为暂停
  playVideoWithUrl(videoUrlInput.value, { autoPlay: false });
  const video = videoRef.value;
  if (video) {
    video.pause();
  }
  isPlaying.value = false;
}

function updateBuffered() {
  const video = videoRef.value;
  if (!video || !duration.value) {
    bufferedRanges.value = [];
    return;
  }
  const ranges = [];
  for (let i = 0; i < video.buffered.length; i++) {
    const start = (video.buffered.start(i) / duration.value) * 100;
    const end = (video.buffered.end(i) / duration.value) * 100;
    ranges.push({ start, end });
  }
  bufferedRanges.value = ranges;
}

onMounted(() => {
  const video = videoRef.value;
  if (!video) return;
  video.addEventListener('timeupdate', () => {
    currentTime.value = video.currentTime;
  });
  video.addEventListener('durationchange', () => {
    duration.value = video.duration || 0;
  });
  video.addEventListener('play', () => {
    isPlaying.value = true;
  });
  video.addEventListener('pause', () => {
    isPlaying.value = false;
  });
  video.addEventListener('waiting', () => {
    videoStatusMsg.value = '视频加载中...';
    videoLoading.value = true;
  });
  video.addEventListener('playing', () => {
    videoStatusMsg.value = '';
    videoLoading.value = false;
  });
  video.addEventListener('error', () => {
    videoStatusMsg.value = '视频播放失败，请检查链接或网络。';
    videoLoading.value = false;
  });
  video.volume = volume.value;
  fetchRoomDetailsAndSetIdentity();
  // 初始加载
  if (videoUrlInput.value) playVideoWithUrl(videoUrlInput.value);
  video.addEventListener('progress', updateBuffered);
  video.addEventListener('durationchange', updateBuffered);
  video.addEventListener('timeupdate', updateBuffered);
});
watch(currentTime, (val) => {
  const video = videoRef.value;
  if (video && Math.abs(video.currentTime - val) > 0.5) {
    video.currentTime = val;
  }
});
const isValidVideoUrl = computed(() => {
  // 简单检测：支持 http(s) 并以 .mp4/.webm/.ogg/.m3u8 结尾
  if (!videoUrlInput.value) return false;
  const url = videoUrlInput.value.trim();
  return /^https?:\/\/.+\.(mp4|webm|ogg|m3u8)(\?.*)?$/i.test(url);
});
watch(videoUrlInput, (val) => {
  if (!val) {
    videoStatusMsg.value = '';
    return;
  }
  if (!isValidVideoUrl.value) {
    videoStatusMsg.value = '请输入有效的视频直链（支持mp4/webm/ogg/m3u8）';
  } else {
    videoStatusMsg.value = '';
  }
});

const membersBarRef = ref(null);
const chatMessagesRef = ref(null);
let isDragging = false;
let startY = 0;
let startHeight = 0;

function startDragDivider(e) {
  isDragging = true;
  startY = e.clientY;
  startHeight = membersBarRef.value.offsetHeight;
  document.body.style.cursor = 'row-resize';
  window.addEventListener('mousemove', onDragDivider);
  window.addEventListener('mouseup', stopDragDivider);
}
function onDragDivider(e) {
  if (!isDragging) return;
  const delta = e.clientY - startY;
  let newHeight = Math.max(48, startHeight + delta);
  membersBarRef.value.style.height = newHeight + 'px';
}
function stopDragDivider() {
  isDragging = false;
  document.body.style.cursor = '';
  window.removeEventListener('mousemove', onDragDivider);
  window.removeEventListener('mouseup', stopDragDivider);
}
onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onDragDivider);
  window.removeEventListener('mouseup', stopDragDivider);
});
</script>

<style scoped>
.room-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(to bottom, #e6f5f3, #c8e6e0);
  transition: background 0.3s;
}
.ws-status-bar-row {
  display: flex;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #eee;
  padding: 0.5rem 1rem 0.5rem 0.5rem;
  position: relative;
}
.room-page.dark-mode .ws-status-bar-row {
  background: linear-gradient(90deg, #23283a 60%, #181c24 100%);
  border-bottom: 1px solid #23283a;
}
.back-home-btn {
  margin-right: 18px;
  background: #fff;
  color: #1976d2;
  border: 1px solid #1976d2;
  border-radius: 4px;
  padding: 0.3rem 1.1rem;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}
.room-page.dark-mode .back-home-btn {
  background: #23283a;
  color: #90caf9;
  border-color: #90caf9;
}
.back-home-btn:hover {
  background: #1976d2;
  color: #fff;
}
.room-page.dark-mode .back-home-btn:hover {
  background: #90caf9;
  color: #23283a;
}
.ws-status-bar {
  font-size: 15px;
  flex: 1 1 0;
}
.dark-mode-switch {
  margin-left: auto;
  display: flex;
  align-items: center;
  font-size: 15px;
  color: #333;
  user-select: none;
}
.room-page.dark-mode .dark-mode-switch {
  color: #90caf9;
}
.dark-mode-switch label {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 4px 10px;
  border-radius: 16px;
  background: #f0f0f0;
  transition: background 0.2s;
}
.room-page.dark-mode .dark-mode-switch label {
  background: #23283a;
}
.dark-mode-switch input[type="checkbox"] {
  appearance: none;
  width: 36px;
  height: 20px;
  background: #ccc;
  border-radius: 10px;
  position: relative;
  outline: none;
  transition: background 0.2s;
  margin-right: 8px;
  cursor: pointer;
}
.dark-mode-switch input[type="checkbox"]:checked {
  background: #1976d2;
}
.dark-mode-switch input[type="checkbox"]::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 2px;
  width: 16px;
  height: 16px;
  background: #fff;
  border-radius: 50%;
  transition: left 0.2s;
}
.dark-mode-switch input[type="checkbox"]:checked::before {
  left: 18px;
  background: #fff;
}
.dark-mode-switch span {
  font-size: 15px;
  margin-left: 2px;
}
.room-main {
  display: flex;
  flex: 1;
  overflow: hidden;
}
.video-area {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  background: linear-gradient(to bottom, #e6f5f3, #c8e6e0);
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  min-width: 0;
}
.room-page.dark-mode .video-area {
  background: linear-gradient(120deg, #23283a 0%, #181c24 100%);
}
.video-player {
  width: 100%;
  height: auto;
  aspect-ratio: 16 / 9;
  min-width: 640px;
  min-height: 360px;
  max-width: 100vw;
  max-height: 80vh;
  background: #000;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.2);
  display: block;
  margin-top: 32px;
  margin-bottom: 32px;
}
.custom-video-controls {
  width: 100%;
  max-width: 640px;
  margin: 0 auto 8px auto;
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255,255,255,0.95);
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  padding: 8px 16px;
}
.room-page.dark-mode .custom-video-controls {
  background: rgba(35,40,58,0.98);
}
.play-btn {
  background: #1976d2;
  border: none;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  color: #fff;
  cursor: pointer;
  outline: none;
  box-shadow: 0 2px 8px rgba(25,118,210,0.10);
  transition: background 0.2s, box-shadow 0.2s, transform 0.1s;
}
.play-btn:hover {
  background: #1565c0;
  box-shadow: 0 4px 16px rgba(25,118,210,0.18);
  transform: scale(1.08);
}
.room-page.dark-mode .play-btn {
  background: #1976d2;
  color: #fff;
}
.room-page.dark-mode .play-btn:hover {
  background: #42a5f5;
}
.video-progress-bar-wrap {
  position: relative;
  flex: 1 1 0;
  height: 16px;
  margin: 0 8px;
  display: flex;
  align-items: center;
}
.video-buffer-bar {
  position: absolute;
  left: 0; top: 50%;
  width: 100%; height: 6px;
  background: #eee; /* 浅灰，表示未缓冲 */
  border-radius: 3px;
  transform: translateY(-50%);
  z-index: 1;
  overflow: hidden;
}
.room-page.dark-mode .video-buffer-bar {
  background: #444; /* 深色模式下未缓冲为深灰 */
}
.buffered-segment {
  position: absolute;
  top: 0; height: 100%;
  background: #bbb; /* 深灰，表示已缓冲 */
  border-radius: 3px;
  z-index: 2;
}
.room-page.dark-mode .buffered-segment {
  background: #888; /* 深色模式下已缓冲为亮灰 */
}
.video-played-bar {
  position: absolute;
  left: 0; top: 50%;
  height: 6px;
  background: #1976d2;
  border-radius: 3px;
  transform: translateY(-50%);
  z-index: 3;
  pointer-events: none;
}
.video-progress-input {
  position: relative;
  width: 100%;
  height: 16px;
  background: transparent;
  z-index: 4;
  appearance: none;
  outline: none;
  margin: 0;
  padding: 0;
}
.video-progress-input::-webkit-slider-thumb {
  appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #1976d2;
  border: 2px solid #fff;
  box-shadow: 0 1px 4px rgba(25,118,210,0.18);
  cursor: pointer;
  margin-top: -5px;
}
.video-progress-input::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #1976d2;
  border: 2px solid #fff;
  box-shadow: 0 1px 4px rgba(25,118,210,0.18);
  cursor: pointer;
}
.video-progress-input::-ms-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #1976d2;
  border: 2px solid #fff;
  box-shadow: 0 1px 4px rgba(25,118,210,0.18);
  cursor: pointer;
}
.video-progress-input::-webkit-slider-runnable-track {
  height: 6px;
  background: transparent;
}
.video-progress-input::-ms-fill-lower,
.video-progress-input::-ms-fill-upper {
  background: transparent;
}
.video-progress-input:focus {
  outline: none;
}
.volume-slider {
  accent-color: #1976d2;
  height: 4px;
}
.time-label {
  font-size: 13px;
  color: #666;
  min-width: 70px;
  text-align: right;
}
.room-page.dark-mode .time-label {
  color: #90caf9;
}
.video-form {
  width: 100%;
  max-width: 640px;
  margin: 0 auto 24px auto;
  background: rgba(255,255,255,0.95);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  padding: 18px 24px 12px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.room-page.dark-mode .video-form {
  background: rgba(35,40,58,0.98);
}
.form-group {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.video-url-input, .room-name-input {
  flex: 1 1 0;
  padding: 6px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 15px;
}
.video-url-input[disabled] {
  background: #f5f5f5;
  color: #aaa;
}
.room-page.dark-mode .video-url-input[disabled] {
  background: #23283a;
  color: #666;
}
.card {
  width: 100%;
  max-width: 640px;
  margin: 0 auto 24px auto;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  padding: 20px 28px 16px 28px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  border: 1px solid #e0e6ed;
}
.room-page.dark-mode .card {
  background: #23283a;
  border: 1px solid #23283a;
  box-shadow: 0 2px 12px rgba(25,118,210,0.10);
}
.room-settings {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #eee;
}
.room-page.dark-mode .room-settings {
  border-top: 1px solid #23283a;
}
.room-settings h4 {
  color: #1976d2;
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 8px;
}
.room-page.dark-mode .room-settings h4 {
  color: #90caf9;
}
.chat-bar {
  width: 340px;
  background: #fff;
  display: flex;
  flex-direction: column;
  border-left: 1px solid #eee;
  height: 100%;
}
.room-page.dark-mode .chat-bar {
  background: linear-gradient(120deg, #23283a 0%, #181c24 100%);
  border-left: 1px solid #23283a;
}
.chat-messages {
  flex: 1 1 0;
  overflow-y: auto;
  padding: 1rem;
  font-size: 15px;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.chat-message {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-bottom: 8px;
}
.self-message {
  align-items: flex-end;
}
.chat-content-row {
  display: flex;
  align-items: flex-start;
}
.self-message .chat-content-row {
  flex-direction: row-reverse;
}
.chat-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  margin-right: 10px;
  border: 2px solid #e0e6ed;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  user-select: none;
  -webkit-user-drag: none;
}
.self-message .chat-avatar {
  margin-left: 10px;
  margin-right: 0;
}
.chat-content-col {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.self-message .chat-content-col {
  align-items: flex-end;
}
.chat-username {
  font-size: 13px;
  color: #1976d2;
  margin-bottom: 2px;
  font-weight: 500;
  text-align: left;
}
.self-message .chat-username {
  color: #90caf9;
  text-align: right;
}
.chat-bubble {
  display: inline-block;
  padding: 0.5rem 1rem;
  border-radius: 18px;
  background: #f0f4fa;
  color: #333;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  max-width: 100%;
  word-break: break-all;
  position: relative;
  margin-left: 4px;
  margin-right: 4px;
}
.chat-bubble::before,
.self-message .chat-bubble::before,
.room-page.dark-mode .chat-bubble::before,
.room-page.dark-mode .self-message .chat-bubble::before {
  display: none !important;
}
.self-message .chat-bubble {
  background: #d2eafd;
  color: #333; /* 与他人消息一致 */
}
.room-page.dark-mode .self-message .chat-bubble {
  background: #90caf9;
  color: #333;
}
.room-page.dark-mode .self-message .chat-bubble::before {
  display: none !important;
}
.room-page.dark-mode .chat-bubble {
  background: #2d3346; /* 比#23283a更淡一些 */
  color: #e0e6ed;
}
.chat-content {
  color: #333;
}
.chat-input-area {
  display: flex;
  padding: 0.5rem 1rem;
  border-top: 1px solid #eee;
  background: #fafbfc;
}
.room-page.dark-mode .chat-input-area {
  background: linear-gradient(90deg, #23283a 60%, #181c24 100%);
  border-top: 1px solid #23283a;
}
.chat-input {
  flex: 1 1 0;
  padding: 0.4rem 0.6rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 15px;
  outline: none;
}
.chat-send-btn {
  margin-left: 0.5rem;
  padding: 0.4rem 1.2rem;
  background: #1976d2;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.2s;
}
.chat-send-btn:hover {
  background: #1256a2;
}
.room-page.dark-mode .ws-status-bar {
  color: #e0e6ed;
}
.video-url-confirm-btn {
  padding: 6px 16px;
  background: #1976d2;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.2s;
}
.video-url-confirm-btn:disabled {
  background: #ccc;
  color: #fff;
  cursor: not-allowed;
}
.room-page.dark-mode .video-url-confirm-btn {
  background: #90caf9;
  color: #23283a;
}
.room-page.dark-mode .video-url-confirm-btn:disabled {
  background: #444a5a;
  color: #888;
}
.video-status-msg {
  color: #d32f2f;
  font-size: 15px;
  margin-top: 4px;
  margin-bottom: 4px;
  text-align: center; /* 居中文本 */
  display: flex;
  justify-content: center;
  align-items: center;
}
.video-status-msg.loading {
  color: #1976d2;
}
.room-page.dark-mode .video-status-msg {
  color: #ffb4b4;
}
.room-page.dark-mode .video-status-msg.loading {
  color: #90caf9;
}
.loading {
  color: #1976d2;
}
.volume-icon svg {
  color: inherit;
}
.room-page.dark-mode .volume-icon svg {
  color: #fff;
}
.room-members-bar {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(64px, 1fr));
  gap: 12px 8px;
  padding: 10px 12px 6px 12px;
  border-bottom: 1px solid #eee;
  background: #f7fafd;
  min-height: 48px;
  /* max-height: 120px; */
  height: 80px;
  overflow-y: auto;
  overflow-x: hidden;
  /* transition: height 0.1s; */
  user-select: none;
}
.room-page.dark-mode .room-members-bar {
  background: #23283a;
  border-bottom: 1px solid #23283a;
}
.drag-divider {
  height: 7px;
  background: #e0e6ed; /* 纯灰色，不再渐变 */
  cursor: row-resize;
  width: 100%;
  position: relative;
  z-index: 2;
  margin: 0;
  border-radius: 4px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  display: flex;
  align-items: center;
  justify-content: center;
}
.room-page.dark-mode .drag-divider {
  background: #23283a;
}
.drag-divider::after {
  content: '';
  display: block;
  width: 32px;
  height: 3px;
  background: #b0bec5;
  border-radius: 2px;
  margin: 0 auto;
}
.room-page.dark-mode .drag-divider::after {
  background: #90caf9;
}
.room-member-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: 4px;
  min-width: 0;
}
.room-member-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  object-fit: cover;
  border: 2.5px solid #90caf9;
  background: #fff;
  box-sizing: border-box;
}
.room-member-item.owner .room-member-avatar {
  border-color: #ffd600;
  box-shadow: 0 0 0 2px #fffbe6;
}
.room-page.dark-mode .room-member-avatar {
  border-color: #1976d2;
  background: #181c24;
}
.room-page.dark-mode .room-member-item.owner .room-member-avatar {
  border-color: #ffd600;
  box-shadow: 0 0 0 2px #232200;
}
.room-member-name {
  font-size: 13px;
  color: #1976d2;
  text-align: center;
  word-break: break-all;
  max-width: 60px;
  margin-top: 2px;
}
.room-page.dark-mode .room-member-name {
  color: #90caf9;
}

/* 视频外链和房间设置表单 label 默认样式 */
.video-form label,
.room-settings label {
  color: #1976d2;
  font-size: 15px;
  font-weight: 500;
}
.room-page.dark-mode .video-form label,
.room-page.dark-mode .room-settings label {
  color: #90caf9; /* 与返回主页按钮文字色一致 */
}
.room-members-label {
  font-size: 15px;
  font-weight: 600;
  color: #1976d2;
  padding: 10px 12px 2px 12px;
  letter-spacing: 1px;
}
.room-page.dark-mode .room-members-label {
  color: #90caf9;
}
</style>
