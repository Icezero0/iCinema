# iCinema 样式系统文档

## 项目结构

```
src/styles/
├── global/                 # 全局样式
│   ├── variables.css      # CSS 变量和设计 token
│   ├── base.css          # 基础重置样式
│   └── utilities.css     # 工具类样式
├── components/           # 组件样式
│   ├── base/            # 基础组件
│   │   ├── dialog.css
│   │   ├── toast.css
│   │   ├── pagination.css
│   │   └── index.css
│   ├── user/            # 用户相关组件
│   │   ├── avatar.css
│   │   ├── avatar-uploader.css
│   │   └── index.css
│   ├── room/            # 房间相关组件
│   │   ├── form.css
│   │   └── index.css
│   └── video/           # 视频相关组件
│       ├── video-area.css
│       ├── video-controls.css
│       ├── video-form.css
│       ├── room-settings.css
│       └── index.css
├── themes/              # 主题样式
│   ├── light.css
│   └── dark.css
└── index.css           # 主入口文件
```

## 设计系统

### 颜色系统
- **主色调**: `--primary-color` (#007bff)
- **成功色**: `--success-color` (#28a745)
- **危险色**: `--danger-color` (#dc3545)
- **警告色**: `--warning-color` (#ffc107)
- **信息色**: `--info-color` (#17a2b8)

### 间距系统
- `--spacing-xs`: 4px
- `--spacing-sm`: 8px
- `--spacing-md`: 16px
- `--spacing-lg`: 24px
- `--spacing-xl`: 32px
- `--spacing-2xl`: 48px
- `--spacing-3xl`: 64px

### 圆角系统
- `--border-radius-xs`: 2px
- `--border-radius-sm`: 4px
- `--border-radius-md`: 8px
- `--border-radius-lg`: 12px
- `--border-radius-xl`: 16px

### 阴影系统
- `--shadow-xs`: 轻微阴影
- `--shadow-sm`: 小阴影
- `--shadow-md`: 中等阴影
- `--shadow-lg`: 大阴影
- `--shadow-xl`: 超大阴影

### 过渡动画
- `--transition-fast`: 0.15s ease-in-out
- `--transition-normal`: 0.3s ease-in-out
- `--transition-slow`: 0.5s ease-in-out

## 主题系统

项目支持明暗两套主题，通过 CSS 变量实现：

### 明亮主题
- 白色背景系列
- 深色文字
- 浅色边框

### 暗色主题
- 深色背景系列
- 浅色文字
- 深色边框

## 工具类

提供了丰富的工具类，支持快速样式应用：

### 间距工具类
- `.m-xs`, `.m-sm`, `.m-md`, `.m-lg`, `.m-xl` - 外边距
- `.p-xs`, `.p-sm`, `.p-md`, `.p-lg`, `.p-xl` - 内边距

### 文字工具类
- `.text-xs`, `.text-sm`, `.text-base`, `.text-lg`, `.text-xl` - 字体大小
- `.font-light`, `.font-normal`, `.font-medium`, `.font-semibold`, `.font-bold` - 字重
- `.text-center`, `.text-left`, `.text-right` - 对齐

### 颜色工具类
- `.text-primary`, `.text-success`, `.text-danger` - 文字颜色
- `.bg-primary`, `.bg-success`, `.bg-danger` - 背景颜色

### 布局工具类
- `.flex`, `.flex-col`, `.flex-row` - Flexbox
- `.items-center`, `.justify-center` - 对齐
- `.hidden`, `.block`, `.inline-block` - 显示

## 响应式设计

使用标准断点：
- `--breakpoint-sm`: 576px
- `--breakpoint-md`: 768px
- `--breakpoint-lg`: 992px
- `--breakpoint-xl`: 1200px

工具类支持响应式前缀：
- `.sm:hidden` - 小屏幕隐藏
- `.md:flex-col` - 中等屏幕垂直布局
- `.lg:block` - 大屏幕显示

## 使用指南

### 在组件中使用

```vue
<script setup>
import '@/styles/components/your-component/your-style.css';
</script>

<template>
  <div class="your-component">
    <!-- 使用 CSS 变量 -->
    <button class="btn-primary">
      Primary Button
    </button>
    
    <!-- 使用工具类 -->
    <div class="flex items-center gap-md">
      Content
    </div>
  </div>
</template>

<style scoped>
.your-component {
  background: var(--color-background);
  padding: var(--spacing-md);
  border-radius: var(--border-radius-md);
  box-shadow: var(--shadow-sm);
  transition: var(--transition-normal);
}

.btn-primary {
  background: var(--primary-color);
  color: var(--vt-c-white);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--border-radius-sm);
  border: none;
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-primary:hover {
  background: var(--primary-color-hover);
}
</style>
```

### 最佳实践

1. **优先使用 CSS 变量**：确保主题一致性
2. **模块化样式**：每个组件有独立的样式文件
3. **使用工具类**：减少重复的样式代码
4. **响应式设计**：使用断点工具类
5. **保持可维护性**：合理组织样式文件结构

## 扩展指南

### 添加新组件样式
1. 在对应的 `components/category/` 目录下创建样式文件
2. 使用 CSS 变量而非硬编码值
3. 在对应的 `index.css` 中导入
4. 在组件中引入样式文件

### 添加新的设计 token
1. 在 `global/variables.css` 中添加新变量
2. 在 `themes/` 中定义主题特定值
3. 更新文档说明

### 添加新工具类
1. 在 `global/utilities.css` 中添加
2. 遵循现有命名规范
3. 考虑响应式变体
