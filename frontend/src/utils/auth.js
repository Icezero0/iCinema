import { API_BASE_URL } from '@/utils/api';

export function clearTokens() {
  document.cookie = 'accesstoken=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;';
  document.cookie = 'refreshtoken=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;';
}

export async function checkAccessToken(accessToken) {
  try {
    const response = await fetch(`${API_BASE_URL}/token/check`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });
    if (response.ok) {
      return true;
    }
    const refreshtoken = document.cookie.split('; ').find(row => row.startsWith('refreshtoken='))?.split('=')[1];
    if (!refreshtoken) {
      clearTokens();
      return false;
    }
    const refreshResp = await fetch(`${API_BASE_URL}/token/refresh`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${refreshtoken}`,
      },
    });
    if (!refreshResp.ok) {
      clearTokens();
      return false;
    }    const data = await refreshResp.json();
    document.cookie = `accesstoken=${data.access_token}; path=/; secure;`;
    document.cookie = `refreshtoken=${data.refresh_token}; path=/; secure; max-age=604800;`;
    const newAccessToken = data.access_token;
    const checkNewResp = await fetch(`${API_BASE_URL}/token/check`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${newAccessToken}`,
      },
    });
    if (!checkNewResp.ok) {
      clearTokens();
      return false;
    }
    return true;
  } catch (error) {
    clearTokens();
    return false;
  }
}