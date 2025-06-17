// composable: useUserInfo.js
import { ref } from 'vue';
import defaultAvatar from '@/assets/default_avatar.jpg';
import { API_BASE_URL, getImageUrl } from '@/utils/api';

const USER_CACHE_KEY = 'icinema_user';
const username = ref('');
const avatarUrl = ref(defaultAvatar);
const email = ref('');

// 初始化：从 sessionStorage 读取
const cachedUser = sessionStorage.getItem(USER_CACHE_KEY);
if (cachedUser) {
  try {
    const userObj = JSON.parse(cachedUser);
    if (userObj.avatar_path) {
      avatarUrl.value = getImageUrl(userObj.avatar_path);
    } else if (userObj.avatar) {
      avatarUrl.value = userObj.avatar;
    }
    if (userObj.username) {
      username.value = userObj.username;
    }
    if (userObj.email) {
      email.value = userObj.email;
    }
  } catch (e) {}
}

export function useUserInfo() {
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
        if (data.avatar_path) {
          avatarUrl.value = getImageUrl(data.avatar_path);
        } else {
          avatarUrl.value = data.avatar || defaultAvatar;
        }
        email.value = data.email || '';
        // 统一缓存完整用户信息
        sessionStorage.setItem('icinema_user', JSON.stringify(data));
      }
    } catch (e) {
      // 可选：错误处理
      alert('获取用户信息失败，请稍后再试。');
      console.error('Error fetching user info:', e);
    }
  }

  return { username, avatarUrl, email, fetchUserInfo };
}
