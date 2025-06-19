// composable: useUserInfo.js
import { ref } from 'vue';
import defaultAvatar from '@/assets/default_avatar.jpg';
import { API_BASE_URL, getImageUrl } from '@/utils/api';

const USER_CACHE_KEY = 'icinema_users';
const username = ref('');
const avatarUrl = ref(defaultAvatar);
const email = ref('');
const userId = ref(null);

// 初始化：从 sessionStorage 读取
const cached = sessionStorage.getItem(USER_CACHE_KEY);
if (cached) {
  try {
    const cacheObj = JSON.parse(cached);
    userId.value = cacheObj.my_id;
    const userInfo = (cacheObj.user_infos || []).find(u => u.user_id === cacheObj.my_id);
    if (userInfo) {
      username.value = userInfo.username;
      avatarUrl.value = userInfo.avatar_url || defaultAvatar;
      email.value = userInfo.email || '';
    }
  } catch (e) {}
}

export function useMyUserInfo() {
  async function fetchUserInfo() {
    try {
      const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
      if (!accessToken) return;
      const response = await fetch(`${API_BASE_URL}/users/me`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        username.value = data.username || 'unknown_user';
        avatarUrl.value = data.avatar_path ? getImageUrl(data.avatar_path) : (data.avatar || defaultAvatar);
        email.value = data.email || '';
        userId.value = data.id || null;
        // 先读取已有缓存
        let cacheObj = { my_id: data.id, user_infos: [] };
        const cached = sessionStorage.getItem(USER_CACHE_KEY);
        if (cached) {
          try {
            cacheObj = JSON.parse(cached);
            cacheObj.my_id = data.id; // 更新 my_id
            if (!Array.isArray(cacheObj.user_infos)) cacheObj.user_infos = [];
          } catch (e) {
            cacheObj = { my_id: data.id, user_infos: [] };
          }
        }
        // 检查 user_infos 是否已有该用户，更新或添加
        const idx = cacheObj.user_infos.findIndex(u => Number(u.user_id) === Number(data.id));
        const userInfoObj = {
          username: data.username || 'unknown_user',
          avatar_url: data.avatar_path ? getImageUrl(data.avatar_path) : (data.avatar || defaultAvatar),
          email: data.email || '',
          user_id: data.id || null
        };
        if (idx >= 0) {
          cacheObj.user_infos[idx] = userInfoObj;
        } else {
          cacheObj.user_infos.push(userInfoObj);
        }
        sessionStorage.setItem(USER_CACHE_KEY, JSON.stringify(cacheObj));
      }
    } catch (e) {
      // alert('获取用户信息失败，请稍后再试。');
      console.error('Error fetching user info:', e);
    }
  }

  return { username, avatarUrl, email, userId, fetchUserInfo };
}

export async function useUserInfo(userId) {
  // 1. 先查缓存（每次都重新读取最新的 sessionStorage）
  let cacheObj = null;
  let cached = sessionStorage.getItem(USER_CACHE_KEY);
  if (cached) {
    try {
      cacheObj = JSON.parse(cached);
      const userInfo = (cacheObj.user_infos || []).find(u => Number(u.user_id) == Number(userId));
      if (userInfo) {
        return {
          username: userInfo.username,
          avatarUrl: userInfo.avatar_url || defaultAvatar,
          email: userInfo.email || '',
          userId: userInfo.user_id
        };
      }
    } catch (e) {}
  }
  // 2. 无缓存则查接口
  let userInfo = null;
  try {
    const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
    const resp = await fetch(`${API_BASE_URL}/users?userid=${userId}`, {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    if (resp.ok) {
      const data = await resp.json();
      const item = (data.items && data.items[0]) || null;
      if (item) {
        userInfo = {
          username: item.username,
          avatarUrl: item.avatar_path ? getImageUrl(item.avatar_path) : defaultAvatar,
          email: item.email || '',
          userId: item.id
        };
        // 写入缓存
        if (!cacheObj) cacheObj = { my_id: null, user_infos: [] };
        // 若已存在则替换，否则push
        const idx = cacheObj.user_infos.findIndex(u => u.user_id === item.id);
        if (idx >= 0) {
          cacheObj.user_infos[idx] = {
            username: item.username,
            avatar_url: item.avatar_path ? getImageUrl(item.avatar_path) : defaultAvatar,
            email: item.email || '',
            user_id: item.id
          };
        } else {
          cacheObj.user_infos.push({
            username: item.username,
            avatar_url: item.avatar_path ? getImageUrl(item.avatar_path) : defaultAvatar,
            email: item.email || '',
            user_id: item.id
          });
        }
        sessionStorage.setItem(USER_CACHE_KEY, JSON.stringify(cacheObj));
      }
    }
  } catch (e) {}
  return userInfo;
}
