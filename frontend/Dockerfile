# 使用 Node.js 镜像
FROM node:18-alpine

WORKDIR /workspace/frontend

# 将依赖文件拷贝进去（提高缓存命中率）
COPY package*.json ./

# 安装依赖
RUN npm install

ENV PATH="/workspace/frontend/node_modules/.bin:$PATH"


# 暴露 Vite 默认端口
EXPOSE 5173

# 启动开发服务器
CMD ["npm", "run", "dev", "--", "--host"]
