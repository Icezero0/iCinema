// composable: useUserInfo.js
import { ref } from 'vue';
import defaultAvatar from '@/assets/default_avatar.jpg';
import { API_BASE_URL, getImageUrl } from '@/utils/api';

export function useUserInfo() {
  const username = ref('');
  const avatarUrl = ref(defaultAvatar);
  const email = ref('');

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
