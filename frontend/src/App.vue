<script setup>
import {
  Activity,
  BookOpen,
  CalendarClock,
  Check,
  Clock3,
  Cloud,
  Container,
  GitBranch,
  GitFork,
  Infinity,
  KeyRound,
  LockKeyhole,
  LockKeyholeOpen,
  Logs,
  Menu,
  Monitor,
  Pencil,
  Plus,
  Search,
  Settings,
  Trash2,
  Users,
  X,
} from "@lucide/vue";
import { storeToRefs } from "pinia";
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { api } from "./api";
import { useAppStore } from "./stores/app";

const navItems = [
  ["schedules", "Schedules", CalendarClock],
  ["jobs", "Jobs", Activity],
  ["credentials", "Credentials", KeyRound],
  ["nodes", "Nodes", Monitor],
];
const credentialProviders = [
  [2, "GitHub", GitBranch],
  [1, "DockerHub", Container],
  [4, "GitLab", GitBranch],
  [98, "Generic Git", GitFork],
  [3, "AWS ECR", Cloud],
];
const cronFieldLabels = ["Minute", "Hour", "Day", "Month", "Weekday"];
const listRouteNames = { schedules: "schedules", jobs: "jobs", credentials: "credentials", nodes: "nodes", users: "users" };

const route = useRoute();
const router = useRouter();
const appStore = useAppStore();
const { currentUser, loading, error, notice, collections } = storeToRefs(appStore);
const activeTab = computed(() => route.meta.resource || "schedules");
const mobileSidebarOpen = ref(false);
const userMenuOpen = ref(false);
const searchQuery = ref("");
const searchInput = ref(null);
const loginForm = reactive({ username: "", password: "" });
const editing = reactive({ schedules: null, credentials: null, users: null, nodes: null });
const scheduleForm = reactive(emptySchedule());
const cronRuleParts = ref(scheduleForm.cron_rule.split(" "));
const credentialForm = reactive(emptyCredential());
const userForm = reactive(emptyUser());
const nodeForm = reactive(emptyNode());
const envRows = ref([]);
const cronDescription = ref("");
const cronDescriptionError = ref("");
const describingCron = ref(false);
const deleteRequest = ref(null);
const deleting = ref(false);
const deleteError = ref("");
let cronDescriptionTimer;
let cronDescriptionRequest = 0;

const activeSchedules = computed(() => collections.value.schedules.filter((schedule) => schedule.active).length);
const healthyJobs = computed(() => collections.value.jobs.filter((job) => {
  const status = String(job.status || "").toLowerCase();
  return status.includes("success") || status.includes("complete") || Number(job.status_code) === 0;
}).length);
const sshNodes = computed(() => collections.value.nodes.filter((node) => node.use_ssh).length);
const adminUsers = computed(() => collections.value.users.filter((user) => user.is_superuser).length);
const userInitials = computed(() => {
  const user = currentUser.value;
  if (!user) return "CT";
  const parts = [user.first_name, user.last_name].filter(Boolean);
  const source = parts.length ? parts : [user.username];
  return source.map((part) => part?.[0]).filter(Boolean).join("").slice(0, 2).toUpperCase();
});
const visibleCollections = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  if (!query) return collections.value;

  return Object.fromEntries(Object.entries(collections.value).map(([resource, items]) => [
    resource,
    items.filter((item) => Object.values(item).some((value) => String(value ?? "").toLowerCase().includes(query))),
  ]));
});

function emptySchedule() {
  return { name: "", image: "", cmd: "", parameters: "", cron_rule: "0 0 * * *", active: true, singleton: false, credential: null, cpu: null, memory: null };
}
function emptyCredential() { return { name: "", username: "", password: "", category: 1 }; }
function emptyUser() { return { username: "", email: "", first_name: "", last_name: "", password: "" }; }
function emptyNode() { return { name: "", host: "", port: 2375, use_ssh: false, secret: "" }; }
function replace(target, source) { Object.assign(target, source); }
function resetForm(resource) {
  editing[resource] = null;
  if (resource === "schedules") {
    replace(scheduleForm, emptySchedule());
    setCronRuleParts(scheduleForm.cron_rule);
    envRows.value = [];
  }
  if (resource === "credentials") replace(credentialForm, emptyCredential());
  if (resource === "users") replace(userForm, emptyUser());
  if (resource === "nodes") replace(nodeForm, emptyNode());
}
function closeForm(resource) {
  resetForm(resource);
  router.push({ name: listRouteNames[resource] });
}
function isList(resource) {
  return activeTab.value === resource && (route.meta.mode === "list" || route.meta.presentation === "modal");
}
function isForm(resource) { return activeTab.value === resource && route.meta.mode === "form"; }
function isModal(resource) { return activeTab.value === resource && route.meta.presentation === "modal"; }
function categoryName(category) {
  return { 1: "Dockerhub", 2: "Github PAT", 3: "AWS ECR", 4: "Gitlab PAT", 97: "Generic registry", 98: "Generic Git", 99: "Generic HTTP auth" }[category] || category;
}
function credentialNeedsUsername(category) {
  return [1, 3, 98].includes(Number(category));
}
function credentialUsernameLabel(category) {
  return Number(category) === 3 ? "aws_access_key_id" : "Username";
}
function credentialPasswordLabel(category) {
  if (Number(category) === 3) return "aws_secret_access_key";
  if ([2, 4].includes(Number(category))) return "Token";
  return "Password";
}
function sourceIcon(sourceName) {
  return sourceName === "GitHub" || sourceName === "GitLab" ? GitBranch : Container;
}
function credentialScheduleCount(credentialId) { return collections.value.schedules.filter((schedule) => schedule.credential === credentialId).length; }

function setCronRuleParts(cronRule) {
  const parts = String(cronRule || "").trim().split(/\s+/).slice(0, cronFieldLabels.length);
  cronRuleParts.value = cronFieldLabels.map((_, index) => parts[index] || "");
}

function updateCronRulePart(index, value) {
  cronRuleParts.value[index] = value.replace(/\s/g, "");
  scheduleForm.cron_rule = cronRuleParts.value.join(" ");
}

function queueCronDescription(cronRule, enabled) {
  window.clearTimeout(cronDescriptionTimer);
  const requestId = ++cronDescriptionRequest;
  cronDescription.value = "";
  cronDescriptionError.value = "";
  describingCron.value = false;

  if (!enabled || !cronRule.trim()) return;

  cronDescriptionTimer = window.setTimeout(async () => {
    describingCron.value = true;
    try {
      const result = await api.describeCron(cronRule);
      if (requestId === cronDescriptionRequest) cronDescription.value = result.description;
    } catch (err) {
      if (requestId === cronDescriptionRequest) {
        cronDescriptionError.value = err.status === 400 ? "Invalid cron expression" : "Unable to describe cron expression.";
      }
    } finally {
      if (requestId === cronDescriptionRequest) describingCron.value = false;
    }
  }, 500);
}

function populateForm(resource, item) {
  editing[resource] = item;
  if (resource === "schedules") {
    replace(scheduleForm, { ...emptySchedule(), ...item });
    setCronRuleParts(scheduleForm.cron_rule);
    envRows.value = Object.entries(item.env_vars || {}).map(([key, value]) => ({ key, value }));
  } else if (resource === "credentials") {
    replace(credentialForm, { ...emptyCredential(), ...item, password: "" });
  } else if (resource === "users") {
    replace(userForm, { ...emptyUser(), ...item, password: "" });
  } else if (resource === "nodes") {
    replace(nodeForm, { ...emptyNode(), ...item, secret: "" });
  }
}

function syncRouteForm() {
  if (loading.value) return;
  const resource = route.meta.resource;
  if (!resource || !isForm(resource) || !(resource in editing)) return;

  resetForm(resource);
  if (!route.params.id) return;

  const item = collections.value[resource].find((candidate) => String(candidate.id) === String(route.params.id));
  if (!item) {
    error.value = `${resource.slice(0, -1)} not found.`;
    notice.value = "";
    router.replace({ name: listRouteNames[resource] });
    return;
  }
  populateForm(resource, item);
}

async function authenticate() {
  if (!await appStore.authenticate(loginForm)) return;
  const redirect = typeof route.query.redirect === "string" && route.query.redirect.startsWith("/")
    ? route.query.redirect
    : "/schedules";
  await router.replace(redirect);
}
async function signOut() {
  try { await appStore.signOut(); }
  finally { await router.replace({ name: "login" }); }
}
async function saveSchedule() {
  const env_vars = Object.fromEntries(envRows.value.filter((row) => row.key).map((row) => [row.key, row.value]));
  if (await appStore.saveResource("schedules", { ...scheduleForm, env_vars }, editing.schedules?.id)) {
    closeForm("schedules");
  }
}
async function save(resource, form) {
  const payload = { ...form };
  if (editing[resource] && !payload.password) delete payload.password;
  if (await appStore.saveResource(resource, payload, editing[resource]?.id)) closeForm(resource);
}
function itemLabel(item) {
  return item.name || item.username || item.id;
}
function requestDelete(resource, item) {
  deleteError.value = "";
  deleteRequest.value = { resource, item };
}
function closeDeleteConfirmation() {
  if (deleting.value) return;
  deleteRequest.value = null;
  deleteError.value = "";
}
async function confirmDelete() {
  if (!deleteRequest.value || deleting.value) return;

  const { resource, item } = deleteRequest.value;
  deleting.value = true;
  try {
    if (await appStore.removeResource(resource, item)) {
      deleteRequest.value = null;
      deleteError.value = "";
    } else {
      deleteError.value = error.value || "The item could not be deleted.";
    }
  } finally {
    deleting.value = false;
  }
}
function handleEscape(event) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    searchInput.value?.focus();
    return;
  }
  if (event.key !== "Escape") return;
  if (deleteRequest.value) {
    closeDeleteConfirmation();
    return;
  }

  const resource = route.meta.resource;
  if (resource && isForm(resource) && isModal(resource)) closeForm(resource);
}
async function initialise() {
  await appStore.initialise();
  if (!currentUser.value && route.name !== "login") {
    await router.replace({ name: "login", query: { redirect: route.fullPath } });
  } else if (currentUser.value && route.name === "login") {
    await router.replace({ name: "schedules" });
  }
  syncRouteForm();
}

watch(() => route.fullPath, () => {
  mobileSidebarOpen.value = false;
  userMenuOpen.value = false;
  searchQuery.value = "";
  if (currentUser.value) syncRouteForm();
});

watch(
  [() => scheduleForm.cron_rule, () => isForm("schedules"), currentUser],
  ([cronRule, scheduleFormOpen, user]) => queueCronDescription(cronRule, scheduleFormOpen && Boolean(user)),
  { immediate: true },
);

onMounted(() => {
  window.addEventListener("keydown", handleEscape);
  initialise();
});
onBeforeUnmount(() => {
  window.clearTimeout(cronDescriptionTimer);
  window.removeEventListener("keydown", handleEscape);
});
</script>

<template>
  <main v-if="!loading">
    <section v-if="!currentUser" class="login-shell">
      <div class="login-atmosphere" aria-hidden="true"><span></span><span></span><span></span></div>
      <div class="login-hero">
        <div class="login-brand brand-lockup"><span class="brand-icon"><Clock3 :size="22" aria-hidden="true" /></span><span>Crontainer</span></div>
        <div class="login-pitch">
          <p class="eyebrow">Container orchestration, distilled.</p>
          <h1>Set it once.<br />Let it run.</h1>
          <p>Quietly dependable scheduling for the infrastructure that keeps your work moving.</p>
        </div>
        <div class="login-proof"><span class="status-dot"></span><span>All systems ready</span></div>
      </div>
      <div class="login-panel">
        <div class="login-card">
          <div class="login-card-heading">
            <p class="eyebrow">Welcome back</p>
            <h2>Sign in to Crontainer</h2>
            <p>Manage schedules, jobs and infrastructure from one focused workspace.</p>
          </div>
          <p v-if="error" class="alert alert-error">{{ error }}</p>
          <form class="login-form" @submit.prevent="authenticate">
            <label class="login-field"><span>Username</span><input v-model="loginForm.username" autocomplete="username" required placeholder="Enter your username" /></label>
            <label class="login-field"><span>Password</span><input v-model="loginForm.password" type="password" autocomplete="current-password" required placeholder="Enter your password" /></label>
            <button type="submit" class="login-submit">Continue <span aria-hidden="true">→</span></button>
          </form>
          <p class="login-footnote"><LockKeyhole :size="14" aria-hidden="true" /> Secured by your private Crontainer instance</p>
        </div>
      </div>
    </section>

    <div v-else class="app-shell">
      <nav class="app-topbar">
        <div class="topbar-start">
          <button class="mobile-menu" @click="mobileSidebarOpen = !mobileSidebarOpen"><Menu :size="21" aria-hidden="true" /><span class="sr-only">Toggle sidebar</span></button>
          <RouterLink :to="{ name: 'schedules' }" class="mobile-brand brand-lockup"><span class="brand-icon"><Clock3 :size="18" aria-hidden="true" /></span><span>Crontainer</span></RouterLink>
          <label class="search-box">
            <span class="sr-only">Search current view</span>
            <Search :size="18" aria-hidden="true" />
            <input ref="searchInput" v-model="searchQuery" placeholder="Search this view" />
            <kbd>⌘ K</kbd>
          </label>
        </div>
        <div class="topbar-actions">
          <div class="system-status"><span class="status-dot"></span><span>System healthy</span></div>
          <div class="relative">
            <button class="user-trigger" :aria-expanded="userMenuOpen" @click="userMenuOpen = !userMenuOpen"><span class="user-avatar">{{ userInitials }}</span><span class="user-name">{{ currentUser.first_name || currentUser.username }}</span><Settings :size="16" aria-hidden="true" /><span class="sr-only">Open user menu</span></button>
            <div v-if="userMenuOpen" class="user-popover">
              <div class="user-summary"><span class="user-avatar user-avatar-large">{{ userInitials }}</span><span><strong>{{ currentUser.username }}</strong><small>{{ currentUser.email || 'Crontainer administrator' }}</small></span></div>
              <ul><li><RouterLink :to="{ name: 'users' }" @click="userMenuOpen = false"><Users :size="17" aria-hidden="true" />User management</RouterLink></li></ul>
              <ul><li><button @click="signOut"><LockKeyholeOpen :size="17" aria-hidden="true" />Sign out</button></li></ul>
            </div>
          </div>
        </div>
      </nav>

      <button v-if="mobileSidebarOpen" class="sidebar-scrim" aria-label="Close sidebar" @click="mobileSidebarOpen = false"></button>
      <aside class="app-sidebar" :class="{ 'sidebar-open': mobileSidebarOpen }" aria-label="Primary navigation">
        <div class="sidebar-inner">
          <RouterLink :to="{ name: 'schedules' }" class="sidebar-brand brand-lockup"><span class="brand-icon"><Clock3 :size="21" aria-hidden="true" /></span><span>Crontainer</span></RouterLink>
          <div class="sidebar-label">Workspace</div>
          <ul class="sidebar-nav">
            <li v-for="[key, label, icon] in navItems" :key="key"><RouterLink :to="{ name: listRouteNames[key] }" class="side-link" :class="{ 'side-link-active': activeTab === key }" @click="mobileSidebarOpen = false"><component :is="icon" :size="19" aria-hidden="true" /><span>{{ label }}</span><small>{{ collections[key].length }}</small></RouterLink></li>
          </ul>
          <div class="sidebar-spacer"></div>
          <div class="sidebar-label">Resources</div>
          <ul class="sidebar-support">
            <li><a href="https://github.com/getcrontainer/" target="_blank" rel="noreferrer"><BookOpen :size="18" aria-hidden="true" /><span>Documentation</span></a></li>
            <li><a href="https://github.com/getcrontainer/" target="_blank" rel="noreferrer"><GitFork :size="18" aria-hidden="true" /><span>GitHub</span></a></li>
          </ul>
          <div class="sidebar-note"><Container :size="20" aria-hidden="true" /><div><strong>Ready to run</strong><span>{{ collections.nodes.length || 'Local' }} runtime {{ collections.nodes.length === 1 ? 'node' : 'nodes' }}</span></div><span class="status-dot"></span></div>
        </div>
      </aside>

      <main class="app-content"><div class="app-surface">
        <p v-if="notice" class="alert alert-success"><Check :size="18" aria-hidden="true" />{{ notice }}</p><p v-if="error" class="alert alert-error">{{ error }}</p>

        <section v-if="isList('schedules')" class="resource-section">
          <header class="page-heading"><div><p class="eyebrow">Automation</p><h1>Schedules</h1><p>Every recurring workload, precisely timed and quietly under control.</p></div><RouterLink :to="{ name: 'schedule-new' }" class="page-primary"><Plus :size="18" aria-hidden="true" />New schedule</RouterLink></header>
          <div class="metric-grid">
            <article class="metric-card metric-featured"><div class="metric-icon"><CalendarClock :size="20" aria-hidden="true" /></div><div><span>Total schedules</span><strong>{{ collections.schedules.length }}</strong><small>configured automations</small></div></article>
            <article class="metric-card"><div class="metric-icon"><Activity :size="20" aria-hidden="true" /></div><div><span>Active now</span><strong>{{ activeSchedules }}</strong><small>{{ collections.schedules.length - activeSchedules }} paused</small></div></article>
            <article class="metric-card"><div class="metric-icon"><Monitor :size="20" aria-hidden="true" /></div><div><span>Runtime nodes</span><strong>{{ collections.nodes.length }}</strong><small>available targets</small></div></article>
          </div>
          <div class="data-panel not-format relative overflow-x-auto">
            <div class="panel-heading"><div><h2>All schedules</h2><span>{{ visibleCollections.schedules.length }} {{ visibleCollections.schedules.length === 1 ? 'schedule' : 'schedules' }}</span></div><span class="panel-badge"><span class="status-dot"></span>Live</span></div>
            <table class="resource-table w-full text-sm text-left">
              <thead class="text-sm font-bold uppercase text-gray-400"><tr><th class="px-6 py-3">Name</th><th class="py-3 text-center">Active</th><th class="px-6 py-3 w-36">Cron Rule</th><th class="px-6 py-3">Source</th><th class="px-6 py-3">CPU</th><th class="px-6 py-3">Memory</th><th class="px-6 py-3">Owner</th><th class="px-6 py-3 w-36">Action</th></tr></thead>
              <tbody><tr v-for="schedule in visibleCollections.schedules" :key="schedule.id" class="default-table-row"><td class="px-6 py-4 text-gray-900 rounded-s-xl"><div class="table-primary">{{ schedule.name }}</div><div class="table-secondary">{{ schedule.id }}</div></td><td class="text-center"><span class="state-pill" :class="schedule.active ? 'state-active' : 'state-paused'"><span></span>{{ schedule.active ? 'Active' : 'Paused' }}</span></td><td class="px-6 py-4"><code class="cron-code" :title="schedule.cron_description">{{ schedule.cron_rule }}</code></td><td class="px-6 py-4"><div class="flex items-center">
                <span
                  class="source-tooltip-trigger me-4"
                  tabindex="0"
                  aria-label="Credential status"
                  :aria-describedby="`credential-status-${schedule.id}`"
                >
                  <component :is="schedule.credential ? LockKeyhole : LockKeyholeOpen" :size="18" :class="{ 'text-gray-300': !schedule.credential }" aria-hidden="true" />
                  <span :id="`credential-status-${schedule.id}`" class="source-tooltip" role="tooltip">{{ schedule.credential ? 'Private source' : 'Public source' }}</span>
                </span>
                <span
                  class="source-tooltip-trigger me-3"
                  tabindex="0"
                  aria-label="Source provider"
                  :aria-describedby="`source-provider-${schedule.id}`"
                >
                  <component :is="sourceIcon(schedule.source_name)" :size="18" aria-hidden="true" />
                  <span :id="`source-provider-${schedule.id}`" class="source-tooltip" role="tooltip">{{ schedule.source_name }}</span>
                </span>
                {{ schedule.image }}
              </div></td><td class="px-6 py-4"><span v-if="schedule.cpu">{{ schedule.cpu }}</span><Infinity v-else :size="18" aria-label="Unlimited" /></td><td class="px-6 py-4"><span v-if="schedule.memory">{{ schedule.memory }} MB</span><Infinity v-else :size="18" aria-label="Unlimited" /></td><td class="px-6 py-4">{{ schedule.created_by || 'system' }}</td><td class="px-6 py-4 rounded-e-xl"><button class="btn-mini-remove" aria-label="Delete schedule" @click="requestDelete('schedules', schedule)"><Trash2 :size="18" aria-hidden="true" /></button> <RouterLink :to="{ name: 'schedule-edit', params: { id: schedule.id } }" class="btn-mini-edit inline-flex items-center justify-center" aria-label="Edit schedule"><Pencil :size="18" aria-hidden="true" /></RouterLink></td></tr></tbody>
            </table>
          </div>
          <RouterLink :to="{ name: 'schedule-new' }" class="mobile-fab" aria-label="Add schedule"><Plus :size="25" aria-hidden="true" /></RouterLink>
        </section>

        <div v-if="isForm('schedules')" :class="{ 'modal-backdrop': isModal('schedules') }" @click.self="isModal('schedules') && closeForm('schedules')">
        <section class="form-card" :class="{ 'modal-card': isModal('schedules') }" :role="isModal('schedules') ? 'dialog' : undefined" :aria-modal="isModal('schedules') || undefined" aria-labelledby="schedule-form-title">
          <button v-if="isModal('schedules')" type="button" class="modal-close" aria-label="Close schedule form" @click="closeForm('schedules')"><X :size="18" aria-hidden="true" /></button>
          <h3 id="schedule-form-title" class="form-title">{{ editing.schedules ? 'Update schedule' : 'New schedule' }}</h3>
          <form class="form-stack" @submit.prevent="saveSchedule">
            <div>
              <label class="form-label">Name</label>
              <input v-model="scheduleForm.name" class="form-control" required />
            </div>
            <div>
              <fieldset aria-describedby="cron-rule-description">
                <legend class="form-label">Cron rule</legend>
                <div class="grid grid-cols-5 gap-2">
                  <label v-for="(label, index) in cronFieldLabels" :key="label" class="min-w-0">
                    <span class="mb-1 block text-xs font-normal text-gray-600">{{ label }}</span>
                    <input
                      :value="cronRuleParts[index]"
                      class="form-control text-center"
                      required
                      autocomplete="off"
                      spellcheck="false"
                      @input="updateCronRulePart(index, $event.target.value)"
                    />
                  </label>
                </div>
              </fieldset>
              <span id="cron-rule-description" class="form-help min-h-6" aria-live="polite">
                <span v-if="describingCron">Describing…</span>
                <span v-else-if="cronDescriptionError" class="text-red-600">{{ cronDescriptionError }}</span>
                <span v-else>{{ cronDescription }}</span>
              </span>
            </div>
            <div>
              <label class="form-label">Env vars</label>
              <div v-for="(row, index) in envRows" :key="index" class="mb-2 flex items-center gap-2">
                <input v-model="row.key" class="form-control flex-1" placeholder="Name" />
                <input v-model="row.value" class="form-control flex-1" placeholder="Value" />
                <button type="button" class="btn btn-danger btn-round !mb-0 !me-0" aria-label="Remove environment variable" @click="envRows.splice(index, 1)"><X :size="18" aria-hidden="true" /></button>
              </div>
              <button type="button" class="btn btn-success btn-round" aria-label="Add environment variable" @click="envRows.push({ key: '', value: '' })"><Plus :size="20" aria-hidden="true" /></button>
            </div>
            <div>
              <label class="form-label">Image</label>
              <input v-model="scheduleForm.image" class="form-control" required />
            </div>
            <div>
              <label class="form-label">Credentials</label>
              <select v-model="scheduleForm.credential" class="form-control">
                <option :value="null">---------</option>
                <option v-for="credential in collections.credentials" :key="credential.id" :value="credential.id">{{ credential.name }}</option>
              </select>
            </div>
            <div>
              <label class="form-label">Cmd</label>
              <input v-model="scheduleForm.cmd" class="form-control" />
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="form-label">Cpu</label>
                <input v-model.number="scheduleForm.cpu" class="form-control" min="1" type="number" />
                <span class="form-help">Number of CPUs</span>
              </div>
              <div>
                <label class="form-label">Memory</label>
                <input v-model.number="scheduleForm.memory" class="form-control" min="1" type="number" />
                <span class="form-help">Memory in MB</span>
              </div>
            </div>
            <div>
              <label class="form-check"><input v-model="scheduleForm.active" class="rounded" type="checkbox" /><span>Active</span></label>
              <p class="form-help">Active</p>
            </div>
            <div>
              <label class="form-check"><input v-model="scheduleForm.singleton" class="rounded" type="checkbox" /><span>Singleton</span></label>
              <p class="form-help">Selecting this option will make this schedule a singleton: only one instance will be allowed to run at any given time.</p>
            </div>
            <div class="form-actions"><button class="btn btn-primary">Save</button></div>
          </form>
        </section>
        </div>

        <section v-if="isList('jobs')" class="resource-section">
          <header class="page-heading"><div><p class="eyebrow">Execution history</p><h1>Jobs</h1><p>A clear, chronological view of every container run.</p></div></header>
          <div class="metric-grid metric-grid-compact">
            <article class="metric-card metric-featured"><div class="metric-icon"><Activity :size="20" aria-hidden="true" /></div><div><span>Total runs</span><strong>{{ collections.jobs.length }}</strong><small>recorded executions</small></div></article>
            <article class="metric-card"><div class="metric-icon"><Check :size="20" aria-hidden="true" /></div><div><span>Healthy runs</span><strong>{{ healthyJobs }}</strong><small>completed successfully</small></div></article>
          </div>
          <div class="data-panel not-format relative overflow-x-auto"><div class="panel-heading"><div><h2>Recent activity</h2><span>{{ visibleCollections.jobs.length }} recorded runs</span></div></div><table class="resource-table w-full text-sm text-left"><thead><tr><th class="px-6 py-3 w-10"><input type="checkbox" aria-label="Select all jobs" /></th><th class="px-6 py-3">Id</th><th class="px-6 py-3">Status</th><th class="px-6 py-3">Schedule</th><th class="px-6 py-3">Cron rule</th><th class="px-6 py-3">Started at</th><th class="px-6 py-3">Duration</th><th class="px-6 py-3">Log</th></tr></thead><tbody><tr v-for="job in visibleCollections.jobs" :key="job.id" class="default-table-row"><td class="px-6 py-4 rounded-s-xl"><input type="checkbox" :aria-label="`Select job ${job.id}`" /></td><td class="px-6 py-4 whitespace-nowrap"><span class="table-secondary">{{ job.id }}</span></td><td class="px-6 py-4"><span class="state-pill" :class="Number(job.status_code) === 0 ? 'state-active' : 'state-paused'"><span></span>{{ job.status || 'Unknown' }}</span></td><td class="px-6 py-4"><span class="table-primary">{{ job.schedule_name }}</span></td><td class="px-6 py-4"><code class="cron-code">{{ job.schedule_cron_rule || '—' }}</code></td><td class="px-6 py-4">{{ new Date(job.created_at).toLocaleString() }}</td><td class="px-6 py-4">{{ job.duration }}s</td><td class="px-6 py-4"><details v-if="job.log"><summary class="btn-mini-edit" aria-label="Show job log"><Logs :size="18" aria-hidden="true" /></summary><pre class="job-log mt-2 whitespace-pre-wrap">{{ job.log }}</pre></details><span v-else class="btn-mini-edit is-disabled" aria-label="No job log"><Logs :size="18" aria-hidden="true" /></span></td></tr></tbody></table></div>
        </section>

        <section v-if="isList('credentials')" class="resource-section">
          <header class="page-heading"><div><p class="eyebrow">Secure access</p><h1>Credentials</h1><p>Private connection details, organized without exposing what matters.</p></div><RouterLink :to="{ name: 'credential-new' }" class="page-primary"><Plus :size="18" aria-hidden="true" />New credential</RouterLink></header>
          <div class="data-panel not-format relative overflow-x-auto"><div class="panel-heading"><div><h2>Credential vault</h2><span>{{ visibleCollections.credentials.length }} secure connections</span></div><span class="panel-badge panel-badge-neutral"><LockKeyhole :size="13" aria-hidden="true" />Encrypted</span></div><table class="resource-table w-full text-sm text-left"><thead><tr><th class="px-6 py-3">Name</th><th class="px-6 py-3">Provider</th><th class="px-6 py-3">Username</th><th class="px-6 py-3">Schedules</th><th class="px-6 py-3 w-36">Action</th></tr></thead><tbody><tr v-for="credential in visibleCollections.credentials" :key="credential.id" class="default-table-row"><td class="px-6 py-4 text-gray-900 rounded-s-xl"><div class="table-primary">{{ credential.name }}</div></td><td class="px-6 py-4"><span class="provider-chip"><KeyRound :size="14" aria-hidden="true" />{{ categoryName(credential.category) }}</span></td><td class="px-6 py-4">{{ credential.username || 'Token only' }}</td><td class="px-6 py-4"><span class="count-chip">{{ credentialScheduleCount(credential.id) }}</span></td><td class="px-6 py-4 rounded-e-xl"><button class="btn-mini-remove" aria-label="Delete credential" @click="requestDelete('credentials', credential)"><Trash2 :size="18" aria-hidden="true" /></button> <RouterLink :to="{ name: 'credential-edit', params: { id: credential.id } }" class="btn-mini-edit inline-flex items-center justify-center" aria-label="Edit credential"><Pencil :size="18" aria-hidden="true" /></RouterLink></td></tr></tbody></table></div><RouterLink :to="{ name: 'credential-new' }" class="mobile-fab" aria-label="Add credential"><Plus :size="25" aria-hidden="true" /></RouterLink>
        </section>
        <div v-if="isForm('credentials')" :class="{ 'modal-backdrop': isModal('credentials') }" @click.self="isModal('credentials') && closeForm('credentials')">
        <section class="form-card" :class="{ 'modal-card': isModal('credentials') }" :role="isModal('credentials') ? 'dialog' : undefined" :aria-modal="isModal('credentials') || undefined" aria-labelledby="credential-form-title">
          <button v-if="isModal('credentials')" type="button" class="modal-close" aria-label="Close new credential" @click="closeForm('credentials')"><X :size="18" aria-hidden="true" /></button>
          <h3 id="credential-form-title" class="form-title">{{ editing.credentials ? 'Update credential' : 'New credential' }}</h3>
          <p class="text-sm font-bold text-gray-900">Select a source provider:</p>
          <div class="provider-grid">
            <button
              v-for="[category, label, icon] in credentialProviders"
              :key="category"
              type="button"
              class="provider-option"
              :class="{ 'provider-option-active': credentialForm.category === category }"
              @click="credentialForm.category = category"
            >
              <component :is="icon" :size="18" aria-hidden="true" />
              <span class="ms-3 whitespace-nowrap">{{ label }}</span>
            </button>
          </div>
          <form class="form-stack" @submit.prevent="save('credentials', credentialForm)">
            <div>
              <label class="form-label">Label</label>
              <input v-model="credentialForm.name" class="form-control" required />
            </div>
            <div v-if="credentialNeedsUsername(credentialForm.category)">
              <label class="form-label">{{ credentialUsernameLabel(credentialForm.category) }}</label>
              <input v-model="credentialForm.username" class="form-control" />
            </div>
            <div>
              <label class="form-label">{{ credentialPasswordLabel(credentialForm.category) }}</label>
              <input v-model="credentialForm.password" type="password" class="form-control" :required="!editing.credentials" />
            </div>
            <div class="form-actions"><button class="btn btn-primary">Save</button></div>
          </form>
        </section>
        </div>

        <section v-if="isList('nodes')" class="resource-section">
          <header class="page-heading"><div><p class="eyebrow">Infrastructure</p><h1>Nodes</h1><p>The runtime destinations where your scheduled work comes alive.</p></div><RouterLink :to="{ name: 'node-new' }" class="page-primary"><Plus :size="18" aria-hidden="true" />New node</RouterLink></header>
          <div class="metric-grid metric-grid-compact"><article class="metric-card metric-featured"><div class="metric-icon"><Monitor :size="20" aria-hidden="true" /></div><div><span>Runtime nodes</span><strong>{{ collections.nodes.length }}</strong><small>configured endpoints</small></div></article><article class="metric-card"><div class="metric-icon"><LockKeyhole :size="20" aria-hidden="true" /></div><div><span>SSH secured</span><strong>{{ sshNodes }}</strong><small>encrypted connections</small></div></article></div>
          <div class="data-panel not-format relative overflow-x-auto"><div class="panel-heading"><div><h2>Connected infrastructure</h2><span>{{ visibleCollections.nodes.length }} runtime targets</span></div></div><table class="resource-table w-full text-sm text-left"><thead><tr><th class="px-6 py-3 w-10"><input type="checkbox" aria-label="Select all nodes" /></th><th class="px-6 py-3">Name</th><th class="px-6 py-3">Host</th><th class="px-6 py-3">Port</th><th class="px-6 py-3">Connection</th><th class="px-6 py-3">Secret</th><th class="px-6 py-3 w-36">Action</th></tr></thead><tbody><tr v-for="node in visibleCollections.nodes" :key="node.id" class="default-table-row"><td class="px-6 py-4 rounded-s-xl"><input type="checkbox" :aria-label="`Select node ${node.name}`" /></td><td class="px-6 py-4 whitespace-nowrap"><div class="table-primary">{{ node.name }}</div></td><td class="px-6 py-4"><code class="host-code">{{ node.host }}</code></td><td class="px-6 py-4">{{ node.port }}</td><td class="px-6 py-4"><span class="provider-chip"><LockKeyhole v-if="node.use_ssh" :size="14" aria-hidden="true" /><Monitor v-else :size="14" aria-hidden="true" />{{ node.use_ssh ? 'SSH' : 'Direct' }}</span></td><td class="px-6 py-4"><span class="secret-value">••••••••</span></td><td class="px-6 py-4"><button class="btn-mini-remove" aria-label="Delete node" @click="requestDelete('nodes', node)"><Trash2 :size="18" aria-hidden="true" /></button> <RouterLink :to="{ name: 'node-edit', params: { id: node.id } }" class="btn-mini-edit inline-flex items-center justify-center" aria-label="Edit node"><Pencil :size="18" aria-hidden="true" /></RouterLink></td></tr></tbody></table></div><RouterLink :to="{ name: 'node-new' }" class="mobile-fab" aria-label="Add node"><Plus :size="25" aria-hidden="true" /></RouterLink>
        </section>
        <div v-if="isForm('nodes')" :class="{ 'modal-backdrop': isModal('nodes') }" @click.self="isModal('nodes') && closeForm('nodes')">
        <section class="form-card" :class="{ 'modal-card': isModal('nodes') }" :role="isModal('nodes') ? 'dialog' : undefined" :aria-modal="isModal('nodes') || undefined" aria-labelledby="node-form-title">
          <button v-if="isModal('nodes')" type="button" class="modal-close" aria-label="Close new node" @click="closeForm('nodes')"><X :size="18" aria-hidden="true" /></button>
          <h3 id="node-form-title" class="form-title">{{ editing.nodes ? 'Update node' : 'New node' }}</h3>
          <form class="form-stack" @submit.prevent="save('nodes', nodeForm)">
            <div>
              <label class="form-label">Name</label>
              <input v-model="nodeForm.name" class="form-control" required />
            </div>
            <div class="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_6rem_7rem]">
              <div>
                <label class="form-label">Host</label>
                <input v-model="nodeForm.host" class="form-control" required />
              </div>
              <div>
                <label class="form-label">Port</label>
                <input v-model.number="nodeForm.port" class="form-control" type="number" required />
              </div>
              <div class="flex items-end pb-1">
                <label class="form-check"><input v-model="nodeForm.use_ssh" type="checkbox" class="rounded" /><span>Use SSH</span></label>
              </div>
            </div>
            <div>
              <label class="form-label">Secret</label>
              <input v-model="nodeForm.secret" type="password" class="form-control" />
            </div>
            <div class="form-actions"><button class="btn btn-primary">Save</button></div>
          </form>
        </section>
        </div>

        <section v-if="isList('users')" class="resource-section">
          <header class="page-heading"><div><p class="eyebrow">Access control</p><h1>Users</h1><p>Manage the people trusted with your Crontainer workspace.</p></div><RouterLink :to="{ name: 'user-new' }" class="page-primary"><Plus :size="18" aria-hidden="true" />Invite user</RouterLink></header>
          <div class="metric-grid metric-grid-compact"><article class="metric-card metric-featured"><div class="metric-icon"><Users :size="20" aria-hidden="true" /></div><div><span>Total users</span><strong>{{ collections.users.length }}</strong><small>workspace accounts</small></div></article><article class="metric-card"><div class="metric-icon"><KeyRound :size="20" aria-hidden="true" /></div><div><span>Administrators</span><strong>{{ adminUsers }}</strong><small>elevated access</small></div></article></div>
          <div class="data-panel not-format relative overflow-x-auto"><div class="panel-heading"><div><h2>Workspace members</h2><span>{{ visibleCollections.users.length }} people with access</span></div></div><table class="resource-table w-full text-sm text-left"><thead><tr><th class="px-6 py-3">Name / Email</th><th class="px-6 py-3">Username</th><th class="px-6 py-3">Joined</th><th class="px-6 py-3">Last login</th><th class="px-6 py-3">Role</th><th class="px-6 py-3 w-36">Action</th></tr></thead><tbody><tr v-for="user in visibleCollections.users" :key="user.id" class="default-table-row"><td class="px-6 py-4 text-gray-900 rounded-s-xl"><div class="table-primary">{{ [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username }}</div><div class="table-secondary">{{ user.email || 'No email set' }}</div></td><td class="px-6 py-4">{{ user.username }}</td><td class="px-6 py-4">{{ user.date_joined ? new Date(user.date_joined).toLocaleDateString() : '—' }}</td><td class="px-6 py-4">{{ user.last_login ? new Date(user.last_login).toLocaleString() : 'Never' }}</td><td class="px-6 py-4"><span class="provider-chip"><Check v-if="user.is_superuser" :size="14" aria-hidden="true" />{{ user.is_superuser ? 'Administrator' : 'Member' }}</span></td><td class="px-6 py-4 rounded-e-xl"><button class="btn-mini-remove" aria-label="Delete user" @click="requestDelete('users', user)"><Trash2 :size="18" aria-hidden="true" /></button> <RouterLink :to="{ name: 'user-edit', params: { id: user.id } }" class="btn-mini-edit inline-flex items-center justify-center" aria-label="Edit user"><Pencil :size="18" aria-hidden="true" /></RouterLink></td></tr></tbody></table></div><RouterLink :to="{ name: 'user-new' }" class="mobile-fab" aria-label="Add user"><Plus :size="25" aria-hidden="true" /></RouterLink>
        </section>
        <div v-if="isForm('users')" :class="{ 'modal-backdrop': isModal('users') }" @click.self="isModal('users') && closeForm('users')">
        <section class="form-card" :class="{ 'modal-card': isModal('users') }" :role="isModal('users') ? 'dialog' : undefined" :aria-modal="isModal('users') || undefined" aria-labelledby="user-form-title">
          <button v-if="isModal('users')" type="button" class="modal-close" aria-label="Close user form" @click="closeForm('users')"><X :size="18" aria-hidden="true" /></button>
          <h3 id="user-form-title" class="form-title">{{ editing.users ? 'Update user' : 'Create user' }}</h3>
          <form class="form-stack" @submit.prevent="save('users', userForm)">
            <div>
              <label class="form-label">Username</label>
              <input v-model="userForm.username" class="form-control" required />
            </div>
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label class="form-label">First name</label>
                <input v-model="userForm.first_name" class="form-control" />
              </div>
              <div>
                <label class="form-label">Last name</label>
                <input v-model="userForm.last_name" class="form-control" />
              </div>
            </div>
            <div>
              <label class="form-label">Email</label>
              <input v-model="userForm.email" class="form-control" type="email" />
            </div>
            <div>
              <label class="form-label">Password</label>
              <input v-model="userForm.password" type="password" class="form-control" :required="!editing.users" />
            </div>
            <div class="form-actions"><button class="btn btn-primary">Save</button></div>
          </form>
        </section>
        </div>
      </div></main>

      <div
        v-if="deleteRequest"
        class="modal-backdrop"
        @click.self="closeDeleteConfirmation"
      >
        <section
          class="modal-card form-card !max-w-md"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-confirmation-title"
          aria-describedby="delete-confirmation-description"
        >
          <button type="button" class="modal-close !start-auto !end-4" aria-label="Close delete confirmation" :disabled="deleting" @click="closeDeleteConfirmation"><X :size="18" aria-hidden="true" /></button>
          <div class="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-red-600"><Trash2 :size="22" aria-hidden="true" /></div>
          <h3 id="delete-confirmation-title" class="mb-2 text-xl font-bold text-gray-900">Delete {{ deleteRequest.resource.slice(0, -1) }}?</h3>
          <p id="delete-confirmation-description" class="text-sm font-normal text-gray-600">
            Are you sure you want to delete <strong class="font-semibold text-gray-900">{{ itemLabel(deleteRequest.item) }}</strong>? This action cannot be undone.
          </p>
          <p v-if="deleteError" class="mt-4 rounded-lg bg-red-50 p-3 text-sm font-normal text-red-700">{{ deleteError }}</p>
          <div class="mt-6 flex justify-end gap-2">
            <button type="button" class="btn !mb-0 !me-0 bg-white text-gray-700 ring-1 ring-gray-300 hover:bg-gray-50" :disabled="deleting" @click="closeDeleteConfirmation">Cancel</button>
            <button type="button" class="btn btn-danger !mb-0 !me-0" :disabled="deleting" @click="confirmDelete">{{ deleting ? 'Deleting…' : 'Delete' }}</button>
          </div>
        </section>
      </div>
    </div>
  </main>
  <div v-else class="loading-screen"><span class="brand-icon"><Clock3 :size="22" aria-hidden="true" /></span><span>Preparing your workspace…</span></div>
</template>
