import { ref, onMounted, onUnmounted } from 'vue';
import { isMobile, isMobileDevice, isMobileViewport, getDeviceType, matchesBreakpoint } from '@/utils/mobile';

/**
 * 响应式设备检测 Composable
 * 提供响应式的设备类型检测和断点匹配
 */
export function useResponsive() {
  const isMobileRef = ref(false);
  const isMobileDeviceRef = ref(false);
  const isMobileViewportRef = ref(false);
  const deviceType = ref('desktop');
  
  const updateResponsiveState = () => {
    isMobileRef.value = isMobile();
    isMobileDeviceRef.value = isMobileDevice();
    isMobileViewportRef.value = isMobileViewport();
    deviceType.value = getDeviceType();
  };
  
  const handleResize = () => {
    updateResponsiveState();
  };
  
  onMounted(() => {
    updateResponsiveState();
    window.addEventListener('resize', handleResize);
  });
  
  onUnmounted(() => {
    window.removeEventListener('resize', handleResize);
  });
  
  return {
    isMobile: isMobileRef,
    isMobileDevice: isMobileDeviceRef,
    isMobileViewport: isMobileViewportRef,
    deviceType,
    matchesBreakpoint: (breakpoint) => matchesBreakpoint(breakpoint)
  };
}
