// API 基础配置
export const API_BASE_URL = '/api';

// 图片资源基础路径
export const IMAGE_BASE_URL = '/api';

/**
 * 获取完整的图片URL
 * @param {string} path - 图片路径，如果以 data: 开头则为base64
 * @returns {string} 完整的图片URL
 */
export function getImageUrl(path) {
  if (!path) return '';
  if (path.startsWith('data:') || path.startsWith('http')) {
    return path;
  }
  // 确保路径以 / 开头
  const formattedPath = path.startsWith('/') ? path : `/${path}`;
  return `${IMAGE_BASE_URL}${formattedPath}`;
}
