import { createRouter, createWebHistory } from "vue-router";

const RouteMarker = { name: "RouteMarker", render: () => null };

const routes = [
  { path: "/", redirect: { name: "schedules" } },
  { path: "/login", name: "login", component: RouteMarker, meta: { public: true } },
  { path: "/schedules", name: "schedules", component: RouteMarker, meta: { resource: "schedules", mode: "list" } },
  { path: "/schedules/new", name: "schedule-new", component: RouteMarker, meta: { resource: "schedules", mode: "form", presentation: "modal" } },
  { path: "/schedules/:id/edit", name: "schedule-edit", component: RouteMarker, meta: { resource: "schedules", mode: "form", presentation: "modal" } },
  { path: "/jobs", name: "jobs", component: RouteMarker, meta: { resource: "jobs", mode: "list" } },
  { path: "/jobs/:id/log", name: "job-log", component: RouteMarker, meta: { resource: "jobs", mode: "log" } },
  { path: "/credentials", name: "credentials", component: RouteMarker, meta: { resource: "credentials", mode: "list" } },
  { path: "/credentials/new", name: "credential-new", component: RouteMarker, meta: { resource: "credentials", mode: "form", presentation: "modal" } },
  { path: "/credentials/:id/edit", name: "credential-edit", component: RouteMarker, meta: { resource: "credentials", mode: "form", presentation: "modal" } },
  { path: "/nodes", name: "nodes", component: RouteMarker, meta: { resource: "nodes", mode: "list" } },
  { path: "/nodes/new", name: "node-new", component: RouteMarker, meta: { resource: "nodes", mode: "form", presentation: "modal" } },
  { path: "/nodes/:id/edit", name: "node-edit", component: RouteMarker, meta: { resource: "nodes", mode: "form", presentation: "modal" } },
  { path: "/users", name: "users", component: RouteMarker, meta: { resource: "users", mode: "list" } },
  { path: "/users/new", name: "user-new", component: RouteMarker, meta: { resource: "users", mode: "form", presentation: "modal" } },
  { path: "/users/:id/edit", name: "user-edit", component: RouteMarker, meta: { resource: "users", mode: "form", presentation: "modal" } },
  { path: "/:pathMatch(.*)*", redirect: { name: "schedules" } },
];

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: () => ({ top: 0 }),
});
