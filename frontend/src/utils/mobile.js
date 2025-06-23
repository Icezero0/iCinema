/**
 * 移动端检测和相关工具函数
 */

/**
 * 检测当前设备是否为移动设备
 * @returns {boolean} 是否为移动设备
 */
export function isMobileDevice() {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

/**
 * 检测当前视窗是否为移动端尺寸
 * @returns {boolean} 是否为移动端尺寸
 */
export function isMobileViewport() {
  return window.innerWidth <= 768;
}

/**
 * 检测是否为移动端（设备或视窗尺寸）
 * @returns {boolean} 是否为移动端
 */
export function isMobile() {
  return isMobileDevice() || isMobileViewport();
}

/**
 * 检测当前是否为触摸设备
 * @returns {boolean} 是否为触摸设备
 */
export function isTouchDevice() {
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
}

/**
 * 获取当前设备类型
 * @returns {string} 设备类型：'mobile', 'tablet', 'desktop'
 */
export function getDeviceType() {
  const width = window.innerWidth;
  
  if (width <= 480) {
    return 'mobile';
  } else if (width <= 1024) {
    return 'tablet';
  } else {
    return 'desktop';
  }
}

/**
 * 响应式断点检测
 */
export const breakpoints = {
  mobile: 480,
  mobileL: 768,
  tablet: 1024,
  desktop: 1440
};

/**
 * 检测当前是否匹配指定断点
 * @param {string} breakpoint 断点名称
 * @returns {boolean} 是否匹配
 */
export function matchesBreakpoint(breakpoint) {
  const width = window.innerWidth;
  const bp = breakpoints[breakpoint];
  
  if (!bp) return false;
  
  switch (breakpoint) {
    case 'mobile':
      return width <= bp;
    case 'mobileL':
      return width <= bp && width > breakpoints.mobile;
    case 'tablet':
      return width <= bp && width > breakpoints.mobileL;
    case 'desktop':
      return width > breakpoints.tablet;
    default:
      return false;
  }
}
