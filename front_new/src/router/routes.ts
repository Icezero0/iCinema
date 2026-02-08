export default [
  {
    path: '/login',
    component: () => import('@/layouts/AuthLayout.vue'),
    children: [
      { path: '', name: 'login', component: () => import('@/pages/login/LoginPage.vue') },
    ],
  },

  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'home', component: () => import('@/pages/home/HomePage.vue') },
      // 以后加：{ path: 'rooms', component: () => import('@/pages/rooms/RoomsPage.vue') }
    ],
  },
]
