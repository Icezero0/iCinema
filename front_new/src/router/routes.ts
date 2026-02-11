export default [
  {
    path: "/auth",
    component: () => import("@/layouts/AuthLayout.vue"),
    children: [
      {
        path: "login",
        name: "login",
        component: () => import("@/pages/login/LoginPage.vue"),
      },
      {
        path: "register",
        name: "register",
        component: () => import("@/pages/register/RegisterPage.vue"),
      },
    ],
  },

  {
    path: "/",
    component: () => import("@/layouts/AppLayout.vue"),
    meta: { requiresAuth: true },
    children: [
      {
        path: "",
        name: "home",
        component: () => import("@/pages/home/HomePage.vue"),
      },
      {
        path: "profile",
        name: "profile",
        component: () => import("@/pages/profile/ProfileEditPage.vue"),
      },
      {
        path: "notifications",
        name: "notifications",
        component: () =>
          import("@/pages/notifications/NotificationsPage.vue"),
      },
    ],
  },
];
