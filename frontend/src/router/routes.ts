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
        path: "rooms/:id",
        name: "room",
        component: () => import("@/pages/room/RoomPage.vue"),
      },
      {
        path: "profile",
        name: "profile",
        component: () => import("@/pages/profile/ProfileEditPage.vue"),
      },
      {
        path: "join-requests",
        name: "join-requests",
        component: () =>
          import("@/pages/join-requests/JoinRequestsPage.vue"),
      },
      {
        path: "public-rooms",
        name: "public-rooms",
        component: () =>
          import("@/pages/public-rooms/PublicRoomsPage.vue"),
      },
      {
        path: "notifications",
        name: "notifications",
        component: () =>
          import("@/pages/notifications/NotificationsPage.vue"),
      },
      {
        path: "contact",
        name: "contact",
        component: () => import("@/pages/contact/ContactPage.vue"),
      },
      {
        path: "feedback-admin",
        name: "feedback-admin",
        component: () =>
          import("@/pages/feedback-admin/FeedbackAdminPage.vue"),
      },
    ],
  },
];
