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
    ],
  },
];
