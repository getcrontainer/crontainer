<script setup>
import {
  Activity,
  ArrowLeft,
  BookOpen,
  CalendarClock,
  Check,
  Clock3,
  Cloud,
  Container,
  Copy,
  GitBranch,
  GitFork,
  HardDrive,
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
  Terminal,
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
const healthCheckDefinitions = [
  ["cron", "Cron service", Clock3],
  ["job_updater", "Job updater", Activity],
  ["disk", "Disk capacity", HardDrive],
];
const HEALTH_POLL_INTERVAL_MS = 30_000;

const route = useRoute();
const router = useRouter();
const appStore = useAppStore();
const { currentUser, loading, error, notice, saveError, collections } = storeToRefs(appStore);
const activeTab = computed(() => route.meta.resource || "schedules");
const mobileSidebarOpen = ref(false);
const userMenuOpen = ref(false);
const searchQuery = ref("");
const searchInput = ref(null);
const logCopied = ref(false);
const systemHealth = ref(null);
const healthError = ref("");
const healthRefreshing = ref(false);
const healthCheckedAt = ref(null);
const loginForm = reactive({ username: "", password: "" });
const editing = reactive({ schedules: null, credentials: null, users: null, nodes: null });
const formErrors = reactive({
  schedules: { fields: {}, general: [] },
  credentials: { fields: {}, general: [] },
  users: { fields: {}, general: [] },
  nodes: { fields: {}, general: [] },
});
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
let healthPollTimer;
let healthRequestId = 0;

const activeSchedules = computed(() => collections.value.schedules.filter((schedule) => schedule.active).length);
const healthyJobs = computed(() => collections.value.jobs.filter((job) => {
  const status = String(job.status || "").toLowerCase();
  return status.includes("success") || status.includes("complete") || Number(job.status_code) === 0;
}).length);
const sshNodes = computed(() => collections.value.nodes.filter((node) => node.use_ssh).length);
const adminUsers = computed(() => collections.value.users.filter((user) => user.is_superuser).length);
const systemHealthState = computed(() => {
  if (healthError.value) return "unavailable";
  if (!systemHealth.value) return healthRefreshing.value ? "checking" : "unavailable";
  return systemHealth.value.healthy ? "healthy" : "unhealthy";
});
const systemHealthLabel = computed(() => ({
  checking: "Checking system",
  healthy: "System healthy",
  unhealthy: "System needs attention",
  unavailable: "Health unavailable",
}[systemHealthState.value]));
const healthCheckedAtLabel = computed(() => healthCheckedAt.value?.toLocaleTimeString([], {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
}) || "Not checked yet");
const systemHealthChecks = computed(() => healthCheckDefinitions.map(([key, label, icon]) => {
  const check = healthError.value ? null : systemHealth.value?.checks?.[key];
  const status = ["healthy", "unhealthy"].includes(check?.status) ? check.status : "unknown";
  let detail = "Status unavailable";
  if (key === "disk" && Number.isFinite(Number(check?.used_percent))) {
    detail = `${check.used_percent}% used · Keep below ${check.max_used_percent}%`;
  } else if (key !== "disk" && status !== "unknown") {
    detail = check.running ? "Running normally" : "Not running";
  }
  return { key, label, icon, status, detail };
}));
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

function normalizedSuccessRate(value) {
  const rate = Number(value);
  return Number.isFinite(rate) ? Math.min(100, Math.max(0, rate)) : 0;
}

function formattedSuccessRate(value) {
  const rate = normalizedSuccessRate(value);
  return `${Number.isInteger(rate) ? rate : rate.toFixed(1)}%`;
}

function successRateTone(value) {
  const rate = normalizedSuccessRate(value);
  if (rate >= 90) return "success-rate-high";
  if (rate >= 60) return "success-rate-medium";
  return "success-rate-low";
}

const selectedJob = computed(() => {
  if (route.meta.resource !== "jobs" || route.meta.mode !== "log") return null;
  return collections.value.jobs.find((job) => String(job.id) === String(route.params.id)) || null;
});
const terminalLogLines = computed(() => parseTerminalLog(selectedJob.value?.log || ""));

const ansiColorNames = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"];
const ghosttyPalette = [
  "#51576d", "#e78284", "#a6d189", "#e5c890", "#8caaee", "#ca9ee6", "#81c8be", "#b5bfe2",
  "#626880", "#eebebe", "#b5d39a", "#f0d9a7", "#9bb7f0", "#d6a8e9", "#99d1c9", "#c6d0f5",
];

function newAnsiState() {
  return { foreground: "", background: "", color: "", backgroundColor: "", bold: false, dim: false, italic: false, underline: false };
}

function xtermColor(index) {
  if (index < 16) return ghosttyPalette[index];
  if (index >= 232) {
    const value = 8 + ((index - 232) * 10);
    return `rgb(${value} ${value} ${value})`;
  }
  const offset = index - 16;
  const levels = [0, 95, 135, 175, 215, 255];
  return `rgb(${levels[Math.floor(offset / 36)]} ${levels[Math.floor((offset % 36) / 6)]} ${levels[offset % 6]})`;
}

function applyAnsiCodes(state, rawCodes) {
  const codes = rawCodes === "" ? [0] : rawCodes.split(";").map(Number);
  for (let index = 0; index < codes.length; index += 1) {
    const code = codes[index];
    if (code === 0) Object.assign(state, newAnsiState());
    else if (code === 1) state.bold = true;
    else if (code === 2) state.dim = true;
    else if (code === 3) state.italic = true;
    else if (code === 4) state.underline = true;
    else if (code === 22) { state.bold = false; state.dim = false; }
    else if (code === 23) state.italic = false;
    else if (code === 24) state.underline = false;
    else if (code === 39) { state.foreground = ""; state.color = ""; }
    else if (code === 49) { state.background = ""; state.backgroundColor = ""; }
    else if (code >= 30 && code <= 37) { state.foreground = ansiColorNames[code - 30]; state.color = ""; }
    else if (code >= 90 && code <= 97) { state.foreground = `bright-${ansiColorNames[code - 90]}`; state.color = ""; }
    else if (code >= 40 && code <= 47) { state.background = ansiColorNames[code - 40]; state.backgroundColor = ""; }
    else if (code >= 100 && code <= 107) { state.background = `bright-${ansiColorNames[code - 100]}`; state.backgroundColor = ""; }
    else if ((code === 38 || code === 48) && codes[index + 1] === 5) {
      const color = xtermColor(codes[index + 2]);
      if (code === 38) { state.foreground = ""; state.color = color; }
      else { state.background = ""; state.backgroundColor = color; }
      index += 2;
    } else if ((code === 38 || code === 48) && codes[index + 1] === 2) {
      const color = `rgb(${codes[index + 2]} ${codes[index + 3]} ${codes[index + 4]})`;
      if (code === 38) { state.foreground = ""; state.color = color; }
      else { state.background = ""; state.backgroundColor = color; }
      index += 4;
    }
  }
}

function ansiSegment(text, state) {
  return {
    text,
    classes: [
      state.foreground && `ansi-fg-${state.foreground}`,
      state.background && `ansi-bg-${state.background}`,
      state.bold && "ansi-bold",
      state.dim && "ansi-dim",
      state.italic && "ansi-italic",
      state.underline && "ansi-underline",
    ].filter(Boolean),
    style: { color: state.color || undefined, backgroundColor: state.backgroundColor || undefined },
  };
}

function plainLogSegments(text) {
  const tokenPattern = /(https?:\/\/[^\s]+|\b(?:ERROR|FATAL|FAILED|FAILURE)\b|\b(?:WARN|WARNING)\b|\b(?:INFO|DEBUG|TRACE)\b|\b(?:SUCCESS|SUCCEEDED|OK|DONE)\b|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|\b\d+(?:\.\d+)?(?:ms|s|MB|GB|%)?\b)/gi;
  return text.split(tokenPattern).filter((token) => token !== "").map((token) => {
    let tokenClass = "";
    if (/^(ERROR|FATAL|FAILED|FAILURE)$/i.test(token)) tokenClass = "log-token-error";
    else if (/^(WARN|WARNING)$/i.test(token)) tokenClass = "log-token-warning";
    else if (/^(INFO|DEBUG|TRACE)$/i.test(token)) tokenClass = "log-token-info";
    else if (/^(SUCCESS|SUCCEEDED|OK|DONE)$/i.test(token)) tokenClass = "log-token-success";
    else if (/^https?:\/\//i.test(token)) tokenClass = "log-token-link";
    else if (/^["']/.test(token)) tokenClass = "log-token-string";
    else if (/^\d/.test(token)) tokenClass = "log-token-number";
    return { text: token, classes: tokenClass ? [tokenClass] : [], style: {} };
  });
}

function parseTerminalLog(log) {
  const state = newAnsiState();
  return String(log).replace(/\r\n?/g, "\n").split("\n").map((line) => {
    const segments = [];
    const ansiPattern = /\u001b\[([0-9;]*)m/g;
    let cursor = 0;
    let match;
    let hasAnsi = false;
    while ((match = ansiPattern.exec(line)) !== null) {
      hasAnsi = true;
      if (match.index > cursor) segments.push(ansiSegment(line.slice(cursor, match.index), state));
      applyAnsiCodes(state, match[1]);
      cursor = ansiPattern.lastIndex;
    }
    if (cursor < line.length) segments.push(ansiSegment(line.slice(cursor), state));
    const stateIsPlain = !state.foreground && !state.background && !state.color && !state.backgroundColor && !state.bold && !state.dim && !state.italic && !state.underline;
    return !hasAnsi && stateIsPlain ? plainLogSegments(line) : segments;
  });
}

function emptySchedule() {
  return { name: "", image: "", cmd: "", parameters: "", cron_rule: "0 0 * * *", active: true, singleton: false, credential: null, cpu: null, memory: null };
}
function emptyCredential() { return { name: "", username: "", password: "", category: 1 }; }
function emptyUser() { return { username: "", email: "", first_name: "", last_name: "", password: "" }; }
function emptyNode() { return { name: "", host: "", port: 2375, use_ssh: false, secret: "" }; }
function replace(target, source) { Object.assign(target, source); }
function validationMessages(value) {
  if (Array.isArray(value)) return value.flatMap(validationMessages);
  if (value && typeof value === "object") return Object.values(value).flatMap(validationMessages);
  return value === undefined || value === null || value === "" ? [] : [String(value)];
}
function clearFormErrors(resource) {
  formErrors[resource].fields = {};
  formErrors[resource].general = [];
}
function clearFieldError(resource, field) {
  if (!(field in formErrors[resource].fields)) return;
  const fields = { ...formErrors[resource].fields };
  delete fields[field];
  formErrors[resource].fields = fields;
}
function applyFormErrors(resource, apiError) {
  clearFormErrors(resource);
  const details = apiError?.details;
  if (details && typeof details === "object" && !Array.isArray(details)) {
    Object.entries(details).forEach(([field, value]) => {
      const messages = validationMessages(value);
      if (["detail", "non_field_errors"].includes(field)) formErrors[resource].general.push(...messages);
      else if (messages.length) formErrors[resource].fields[field] = messages;
    });
  } else {
    formErrors[resource].general = validationMessages(details || apiError?.message || "Unable to save this item.");
  }
}
function fieldError(resource, field) { return formErrors[resource].fields[field]?.join(" ") || ""; }
function formHasErrors(resource) { return formErrors[resource].general.length > 0 || Object.keys(formErrors[resource].fields).length > 0; }
function formErrorSummary(resource) {
  return formErrors[resource].general.join(" ") || "Review the highlighted fields and try again.";
}
function resetForm(resource) {
  editing[resource] = null;
  clearFormErrors(resource);
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
function isJobLog() { return activeTab.value === "jobs" && route.meta.mode === "log"; }
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

async function copyJobLog() {
  if (!selectedJob.value?.log) return;
  await navigator.clipboard.writeText(selectedJob.value.log);
  logCopied.value = true;
  window.setTimeout(() => { logCopied.value = false; }, 1600);
}

function setCronRuleParts(cronRule) {
  const parts = String(cronRule || "").trim().split(/\s+/).slice(0, cronFieldLabels.length);
  cronRuleParts.value = cronFieldLabels.map((_, index) => parts[index] || "");
}

function updateCronRulePart(index, value) {
  cronRuleParts.value[index] = value.replace(/\s/g, "");
  scheduleForm.cron_rule = cronRuleParts.value.join(" ");
  clearFieldError("schedules", "cron_rule");
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
  clearFormErrors("schedules");
  const env_vars = Object.fromEntries(envRows.value.filter((row) => row.key).map((row) => [row.key, row.value]));
  if (await appStore.saveResource("schedules", { ...scheduleForm, env_vars }, editing.schedules?.id)) {
    closeForm("schedules");
  } else {
    applyFormErrors("schedules", saveError.value);
  }
}
async function save(resource, form) {
  clearFormErrors(resource);
  const payload = { ...form };
  if (editing[resource] && !payload.password) delete payload.password;
  if (await appStore.saveResource(resource, payload, editing[resource]?.id)) closeForm(resource);
  else applyFormErrors(resource, saveError.value);
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

async function refreshJobs() {
  try {
    await appStore.load("jobs");
  } catch (err) {
    error.value = err.message || "Unable to refresh jobs.";
    notice.value = "";
  }
}

async function refreshSystemHealth() {
  const requestId = ++healthRequestId;
  healthRefreshing.value = true;
  try {
    const result = await api.health();
    if (requestId !== healthRequestId) return;
    systemHealth.value = result;
    healthError.value = "";
  } catch (err) {
    if (requestId !== healthRequestId) return;
    healthError.value = err.message || "Unable to check system health.";
  } finally {
    if (requestId === healthRequestId) {
      healthRefreshing.value = false;
      healthCheckedAt.value = new Date();
    }
  }
}

function stopSystemHealthPolling() {
  window.clearInterval(healthPollTimer);
  healthPollTimer = undefined;
  healthRequestId += 1;
  healthRefreshing.value = false;
  healthError.value = "";
  systemHealth.value = null;
  healthCheckedAt.value = null;
}

function startSystemHealthPolling() {
  stopSystemHealthPolling();
  refreshSystemHealth();
  healthPollTimer = window.setInterval(refreshSystemHealth, HEALTH_POLL_INTERVAL_MS);
}

watch(() => route.fullPath, (_currentPath, previousPath) => {
  mobileSidebarOpen.value = false;
  userMenuOpen.value = false;
  searchQuery.value = "";
  logCopied.value = false;
  if (currentUser.value) {
    syncRouteForm();
    const isInJobs = route.meta.resource === "jobs";
    const wasInJobs = previousPath?.startsWith("/jobs");
    if (isInJobs || wasInJobs) refreshJobs();
  }
});

watch(
  [() => scheduleForm.cron_rule, () => isForm("schedules"), currentUser],
  ([cronRule, scheduleFormOpen, user]) => queueCronDescription(cronRule, scheduleFormOpen && Boolean(user)),
  { immediate: true },
);

watch(
  currentUser,
  (user) => {
    if (user) startSystemHealthPolling();
    else stopSystemHealthPolling();
  },
  { immediate: true },
);

onMounted(() => {
  window.addEventListener("keydown", handleEscape);
  initialise();
});
onBeforeUnmount(() => {
  window.clearTimeout(cronDescriptionTimer);
  stopSystemHealthPolling();
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
          <div class="system-health">
            <button
              type="button"
              class="system-status"
              :class="`system-status-${systemHealthState}`"
              :aria-label="systemHealthLabel"
              aria-describedby="system-health-popover"
            >
              <span class="status-dot" aria-hidden="true"></span>
              <span class="system-status-label">{{ systemHealthLabel }}</span>
            </button>
            <div id="system-health-popover" class="system-health-popover" role="tooltip">
              <header class="health-popover-header">
                <span><strong>System health</strong><small>Checked {{ healthCheckedAtLabel }}</small></span>
                <span class="health-summary" :class="`health-summary-${systemHealthState}`">{{ systemHealthState }}</span>
              </header>
              <p v-if="healthError" class="health-fetch-error">{{ healthError }}</p>
              <ul class="health-check-list">
                <li v-for="check in systemHealthChecks" :key="check.key" :class="`health-check-${check.status}`">
                  <span class="health-check-icon"><component :is="check.icon" :size="16" aria-hidden="true" /></span>
                  <span class="health-check-copy"><strong>{{ check.label }}</strong><small>{{ check.detail }}</small></span>
                  <span class="health-check-state"><i aria-hidden="true"></i>{{ check.status }}</span>
                </li>
              </ul>
              <footer><span class="status-dot" aria-hidden="true"></span>Refreshes automatically every 30 seconds</footer>
            </div>
          </div>
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
        <p v-if="notice" class="alert alert-success"><Check :size="18" aria-hidden="true" />{{ notice }}</p><p v-if="error && route.meta.mode !== 'form'" class="alert alert-error">{{ error }}</p>

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
              <thead class="text-sm font-bold uppercase text-gray-400"><tr><th class="px-6 py-3">Name</th><th class="py-3 text-center">Active</th><th class="px-6 py-3 w-36">Success rate</th><th class="px-6 py-3 w-36">Cron Rule</th><th class="px-6 py-3">Source</th><th class="px-6 py-3">CPU</th><th class="px-6 py-3">Memory</th><th class="px-6 py-3">Owner</th><th class="px-6 py-3 w-36">Action</th></tr></thead>
              <tbody><tr v-for="schedule in visibleCollections.schedules" :key="schedule.id" class="default-table-row"><td class="px-6 py-4 text-gray-900 rounded-s-xl"><div class="table-primary">{{ schedule.name }}</div><div class="table-secondary">{{ schedule.id }}</div></td><td class="text-center"><span class="state-pill" :class="schedule.active ? 'state-active' : 'state-paused'"><span></span>{{ schedule.active ? 'Active' : 'Paused' }}</span></td><td class="px-6 py-4"><div class="success-rate" :class="successRateTone(schedule.success_rate)" :aria-label="`${formattedSuccessRate(schedule.success_rate)} success rate across the latest completed executions`"><div class="success-rate-value"><span class="success-rate-dot"></span><strong>{{ formattedSuccessRate(schedule.success_rate) }}</strong></div><div class="success-rate-track" aria-hidden="true"><span :style="{ width: `${normalizedSuccessRate(schedule.success_rate)}%` }"></span></div></div></td><td class="px-6 py-4"><code class="cron-code" :title="schedule.cron_description">{{ schedule.cron_rule }}</code></td><td class="px-6 py-4"><div class="flex items-center">
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

        <div v-if="isForm('schedules')" :class="{ 'modal-backdrop': isModal('schedules') }">
        <section class="form-card" :class="{ 'modal-card': isModal('schedules') }" :role="isModal('schedules') ? 'dialog' : undefined" :aria-modal="isModal('schedules') || undefined" aria-labelledby="schedule-form-title">
          <button v-if="isModal('schedules')" type="button" class="modal-close" aria-label="Close schedule form" @click="closeForm('schedules')"><X :size="18" aria-hidden="true" /></button>
          <h3 id="schedule-form-title" class="form-title">{{ editing.schedules ? 'Update schedule' : 'New schedule' }}</h3>
          <div v-if="formHasErrors('schedules')" class="form-error-summary" role="alert"><span aria-hidden="true">!</span><div><strong>Schedule wasn’t saved</strong><p>{{ formErrorSummary('schedules') }}</p></div></div>
          <form class="form-stack" @submit.prevent="saveSchedule">
            <div>
              <label class="form-label">Name</label>
              <input v-model="scheduleForm.name" class="form-control" :class="{ 'form-control-error': fieldError('schedules', 'name') }" :aria-invalid="Boolean(fieldError('schedules', 'name'))" aria-describedby="schedule-name-error" required @input="clearFieldError('schedules', 'name')" />
              <p v-if="fieldError('schedules', 'name')" id="schedule-name-error" class="form-field-error">{{ fieldError('schedules', 'name') }}</p>
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
                      :class="{ 'form-control-error': fieldError('schedules', 'cron_rule') }"
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
              <p v-if="fieldError('schedules', 'cron_rule')" class="form-field-error">{{ fieldError('schedules', 'cron_rule') }}</p>
            </div>
            <div>
              <label class="form-label">Env vars</label>
              <div v-for="(row, index) in envRows" :key="index" class="mb-2 flex items-center gap-2">
                <input v-model="row.key" class="form-control flex-1" placeholder="Name" @input="clearFieldError('schedules', 'env_vars')" />
                <input v-model="row.value" class="form-control flex-1" placeholder="Value" @input="clearFieldError('schedules', 'env_vars')" />
                <button type="button" class="btn btn-danger btn-round !mb-0 !me-0" aria-label="Remove environment variable" @click="envRows.splice(index, 1)"><X :size="18" aria-hidden="true" /></button>
              </div>
              <button type="button" class="btn btn-success btn-round" aria-label="Add environment variable" @click="envRows.push({ key: '', value: '' })"><Plus :size="20" aria-hidden="true" /></button>
              <p v-if="fieldError('schedules', 'env_vars')" class="form-field-error">{{ fieldError('schedules', 'env_vars') }}</p>
            </div>
            <div>
              <label class="form-label">Image</label>
              <input v-model="scheduleForm.image" class="form-control" :class="{ 'form-control-error': fieldError('schedules', 'image') }" :aria-invalid="Boolean(fieldError('schedules', 'image'))" aria-describedby="schedule-image-error" required @input="clearFieldError('schedules', 'image')" />
              <p v-if="fieldError('schedules', 'image')" id="schedule-image-error" class="form-field-error">{{ fieldError('schedules', 'image') }}</p>
            </div>
            <div>
              <label class="form-label">Credentials</label>
              <select v-model="scheduleForm.credential" class="form-control" :class="{ 'form-control-error': fieldError('schedules', 'credential') }" :aria-invalid="Boolean(fieldError('schedules', 'credential'))" @change="clearFieldError('schedules', 'credential')">
                <option :value="null">---------</option>
                <option v-for="credential in collections.credentials" :key="credential.id" :value="credential.id">{{ credential.name }}</option>
              </select>
              <p v-if="fieldError('schedules', 'credential')" class="form-field-error">{{ fieldError('schedules', 'credential') }}</p>
            </div>
            <div>
              <label class="form-label">Cmd</label>
              <input v-model="scheduleForm.cmd" class="form-control" :class="{ 'form-control-error': fieldError('schedules', 'cmd') }" :aria-invalid="Boolean(fieldError('schedules', 'cmd'))" @input="clearFieldError('schedules', 'cmd')" />
              <p v-if="fieldError('schedules', 'cmd')" class="form-field-error">{{ fieldError('schedules', 'cmd') }}</p>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="form-label">Cpu</label>
                <input v-model.number="scheduleForm.cpu" class="form-control" :class="{ 'form-control-error': fieldError('schedules', 'cpu') }" min="1" type="number" @input="clearFieldError('schedules', 'cpu')" />
                <span class="form-help">Number of CPUs</span>
                <p v-if="fieldError('schedules', 'cpu')" class="form-field-error">{{ fieldError('schedules', 'cpu') }}</p>
              </div>
              <div>
                <label class="form-label">Memory</label>
                <input v-model.number="scheduleForm.memory" class="form-control" :class="{ 'form-control-error': fieldError('schedules', 'memory') }" min="1" type="number" @input="clearFieldError('schedules', 'memory')" />
                <span class="form-help">Memory in MB</span>
                <p v-if="fieldError('schedules', 'memory')" class="form-field-error">{{ fieldError('schedules', 'memory') }}</p>
              </div>
            </div>
            <div>
              <label class="form-check"><input v-model="scheduleForm.active" class="rounded" type="checkbox" @change="clearFieldError('schedules', 'active')" /><span>Active</span></label>
              <p class="form-help">Active</p>
              <p v-if="fieldError('schedules', 'active')" class="form-field-error">{{ fieldError('schedules', 'active') }}</p>
            </div>
            <div>
              <label class="form-check"><input v-model="scheduleForm.singleton" class="rounded" type="checkbox" @change="clearFieldError('schedules', 'singleton')" /><span>Singleton</span></label>
              <p class="form-help">Selecting this option will make this schedule a singleton: only one instance will be allowed to run at any given time.</p>
              <p v-if="fieldError('schedules', 'singleton')" class="form-field-error">{{ fieldError('schedules', 'singleton') }}</p>
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
          <div class="data-panel not-format relative overflow-x-auto"><div class="panel-heading"><div><h2>Recent activity</h2><span>{{ visibleCollections.jobs.length }} recorded runs</span></div></div><table class="resource-table w-full text-sm text-left"><thead><tr><th class="px-6 py-3 w-10"><input type="checkbox" aria-label="Select all jobs" /></th><th class="px-6 py-3">Id</th><th class="px-6 py-3">Status</th><th class="px-6 py-3">Schedule</th><th class="px-6 py-3">Cron rule</th><th class="px-6 py-3">Started at</th><th class="px-6 py-3">Duration</th><th class="px-6 py-3">Log</th></tr></thead><tbody><tr v-for="job in visibleCollections.jobs" :key="job.id" class="default-table-row"><td class="px-6 py-4 rounded-s-xl"><input type="checkbox" :aria-label="`Select job ${job.id}`" /></td><td class="px-6 py-4 whitespace-nowrap"><span class="table-secondary">{{ job.id }}</span></td><td class="px-6 py-4"><span class="state-pill" :class="Number(job.status_code) === 0 ? 'state-active' : 'state-paused'"><span></span>{{ job.status || 'Unknown' }}</span></td><td class="px-6 py-4"><span class="table-primary">{{ job.schedule_name }}</span></td><td class="px-6 py-4"><code class="cron-code">{{ job.schedule_cron_rule || '—' }}</code></td><td class="px-6 py-4">{{ new Date(job.created_at).toLocaleString() }}</td><td class="px-6 py-4">{{ job.duration }}s</td><td class="px-6 py-4"><RouterLink :to="{ name: 'job-log', params: { id: job.id } }" class="btn-mini-edit" :aria-label="`Open log for job ${job.id}`"><Logs :size="18" aria-hidden="true" /></RouterLink></td></tr></tbody></table></div>
        </section>

        <section v-if="isJobLog()" class="resource-section job-log-view">
          <RouterLink :to="{ name: 'jobs' }" class="log-back"><ArrowLeft :size="16" aria-hidden="true" />All jobs</RouterLink>
          <template v-if="selectedJob">
            <header class="page-heading job-log-heading">
              <div><p class="eyebrow">Execution log</p><h1>{{ selectedJob.schedule_name || 'Job run' }}</h1><p class="job-id">Run {{ selectedJob.id }}</p></div>
              <span class="state-pill job-log-state" :class="Number(selectedJob.status_code) === 0 ? 'state-active' : 'state-paused'"><span></span>{{ selectedJob.status || 'Unknown' }}</span>
            </header>
            <div class="job-log-layout">
              <article class="log-console">
                <header class="log-console-bar">
                  <div><span class="terminal-dots" aria-hidden="true"><i></i><i></i><i></i></span><Terminal :size="15" aria-hidden="true" /><strong>Container output</strong></div>
                  <button type="button" class="log-copy" :disabled="!selectedJob.log" @click="copyJobLog"><Check v-if="logCopied" :size="14" aria-hidden="true" /><Copy v-else :size="14" aria-hidden="true" />{{ logCopied ? 'Copied' : 'Copy log' }}</button>
                </header>
                <pre v-if="selectedJob.log" class="log-output"><code><span v-for="(line, lineIndex) in terminalLogLines" :key="lineIndex" class="terminal-line"><span v-for="(segment, segmentIndex) in line" :key="segmentIndex" :class="segment.classes" :style="segment.style">{{ segment.text }}</span></span></code></pre>
                <div v-else class="log-empty"><Logs :size="27" aria-hidden="true" /><strong>No output captured</strong><span>This run completed without writing a container log.</span></div>
              </article>
              <aside class="job-facts" aria-label="Job details">
                <div class="job-facts-heading"><span>Run details</span><small>Recorded execution</small></div>
                <dl>
                  <div><dt>Status</dt><dd>{{ selectedJob.status || 'Unknown' }}<small>Code {{ selectedJob.status_code ?? '—' }}</small></dd></div>
                  <div><dt>Started</dt><dd>{{ new Date(selectedJob.created_at).toLocaleString() }}</dd></div>
                  <div><dt>Duration</dt><dd>{{ selectedJob.duration }}s</dd></div>
                  <div><dt>Schedule</dt><dd>{{ selectedJob.schedule_name || '—' }}<small><code>{{ selectedJob.schedule_cron_rule || 'No cron rule' }}</code></small></dd></div>
                  <div><dt>Run ID</dt><dd class="fact-id">{{ selectedJob.id }}</dd></div>
                </dl>
              </aside>
            </div>
          </template>
          <div v-else class="job-not-found"><Logs :size="28" aria-hidden="true" /><h1>Job not found</h1><p>This run may no longer be available.</p><RouterLink :to="{ name: 'jobs' }" class="page-primary">Return to jobs</RouterLink></div>
        </section>

        <section v-if="isList('credentials')" class="resource-section">
          <header class="page-heading"><div><p class="eyebrow">Secure access</p><h1>Credentials</h1><p>Private connection details, organized without exposing what matters.</p></div><RouterLink :to="{ name: 'credential-new' }" class="page-primary"><Plus :size="18" aria-hidden="true" />New credential</RouterLink></header>
          <div class="data-panel not-format relative overflow-x-auto"><div class="panel-heading"><div><h2>Credential vault</h2><span>{{ visibleCollections.credentials.length }} secure connections</span></div><span class="panel-badge panel-badge-neutral"><LockKeyhole :size="13" aria-hidden="true" />Encrypted</span></div><table class="resource-table w-full text-sm text-left"><thead><tr><th class="px-6 py-3">Name</th><th class="px-6 py-3">Provider</th><th class="px-6 py-3">Username</th><th class="px-6 py-3">Schedules</th><th class="px-6 py-3 w-36">Action</th></tr></thead><tbody><tr v-for="credential in visibleCollections.credentials" :key="credential.id" class="default-table-row"><td class="px-6 py-4 text-gray-900 rounded-s-xl"><div class="table-primary">{{ credential.name }}</div></td><td class="px-6 py-4"><span class="provider-chip"><KeyRound :size="14" aria-hidden="true" />{{ categoryName(credential.category) }}</span></td><td class="px-6 py-4">{{ credential.username || 'Token only' }}</td><td class="px-6 py-4"><span class="count-chip">{{ credentialScheduleCount(credential.id) }}</span></td><td class="px-6 py-4 rounded-e-xl"><button class="btn-mini-remove" aria-label="Delete credential" @click="requestDelete('credentials', credential)"><Trash2 :size="18" aria-hidden="true" /></button> <RouterLink :to="{ name: 'credential-edit', params: { id: credential.id } }" class="btn-mini-edit inline-flex items-center justify-center" aria-label="Edit credential"><Pencil :size="18" aria-hidden="true" /></RouterLink></td></tr></tbody></table></div><RouterLink :to="{ name: 'credential-new' }" class="mobile-fab" aria-label="Add credential"><Plus :size="25" aria-hidden="true" /></RouterLink>
        </section>
        <div v-if="isForm('credentials')" :class="{ 'modal-backdrop': isModal('credentials') }">
        <section class="form-card" :class="{ 'modal-card': isModal('credentials') }" :role="isModal('credentials') ? 'dialog' : undefined" :aria-modal="isModal('credentials') || undefined" aria-labelledby="credential-form-title">
          <button v-if="isModal('credentials')" type="button" class="modal-close" aria-label="Close credential form" @click="closeForm('credentials')"><X :size="18" aria-hidden="true" /></button>
          <h3 id="credential-form-title" class="form-title">{{ editing.credentials ? 'Update credential' : 'New credential' }}</h3>
          <div v-if="formHasErrors('credentials')" class="form-error-summary" role="alert"><span aria-hidden="true">!</span><div><strong>Credential wasn’t saved</strong><p>{{ formErrorSummary('credentials') }}</p></div></div>
          <p class="text-sm font-bold text-gray-900">Select a source provider:</p>
          <div class="provider-grid">
            <button
              v-for="[category, label, icon] in credentialProviders"
              :key="category"
              type="button"
              class="provider-option"
              :class="{ 'provider-option-active': credentialForm.category === category }"
              @click="credentialForm.category = category; clearFieldError('credentials', 'category')"
            >
              <component :is="icon" :size="18" aria-hidden="true" />
              <span class="ms-3 whitespace-nowrap">{{ label }}</span>
            </button>
          </div>
          <p v-if="fieldError('credentials', 'category')" class="form-field-error">{{ fieldError('credentials', 'category') }}</p>
          <form class="form-stack" @submit.prevent="save('credentials', credentialForm)">
            <div>
              <label class="form-label">Label</label>
              <input v-model="credentialForm.name" class="form-control" :class="{ 'form-control-error': fieldError('credentials', 'name') }" :aria-invalid="Boolean(fieldError('credentials', 'name'))" required @input="clearFieldError('credentials', 'name')" />
              <p v-if="fieldError('credentials', 'name')" class="form-field-error">{{ fieldError('credentials', 'name') }}</p>
            </div>
            <div v-if="credentialNeedsUsername(credentialForm.category)">
              <label class="form-label">{{ credentialUsernameLabel(credentialForm.category) }}</label>
              <input v-model="credentialForm.username" class="form-control" :class="{ 'form-control-error': fieldError('credentials', 'username') }" :aria-invalid="Boolean(fieldError('credentials', 'username'))" @input="clearFieldError('credentials', 'username')" />
              <p v-if="fieldError('credentials', 'username')" class="form-field-error">{{ fieldError('credentials', 'username') }}</p>
            </div>
            <div>
              <label class="form-label">{{ credentialPasswordLabel(credentialForm.category) }}</label>
              <input v-model="credentialForm.password" type="password" class="form-control" :class="{ 'form-control-error': fieldError('credentials', 'password') }" :aria-invalid="Boolean(fieldError('credentials', 'password'))" :required="!editing.credentials" @input="clearFieldError('credentials', 'password')" />
              <p v-if="fieldError('credentials', 'password')" class="form-field-error">{{ fieldError('credentials', 'password') }}</p>
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
        <div v-if="isForm('nodes')" :class="{ 'modal-backdrop': isModal('nodes') }">
        <section class="form-card" :class="{ 'modal-card': isModal('nodes') }" :role="isModal('nodes') ? 'dialog' : undefined" :aria-modal="isModal('nodes') || undefined" aria-labelledby="node-form-title">
          <button v-if="isModal('nodes')" type="button" class="modal-close" aria-label="Close node form" @click="closeForm('nodes')"><X :size="18" aria-hidden="true" /></button>
          <h3 id="node-form-title" class="form-title">{{ editing.nodes ? 'Update node' : 'New node' }}</h3>
          <div v-if="formHasErrors('nodes')" class="form-error-summary" role="alert"><span aria-hidden="true">!</span><div><strong>Node wasn’t saved</strong><p>{{ formErrorSummary('nodes') }}</p></div></div>
          <form class="form-stack" @submit.prevent="save('nodes', nodeForm)">
            <div>
              <label class="form-label">Name</label>
              <input v-model="nodeForm.name" class="form-control" :class="{ 'form-control-error': fieldError('nodes', 'name') }" :aria-invalid="Boolean(fieldError('nodes', 'name'))" required @input="clearFieldError('nodes', 'name')" />
              <p v-if="fieldError('nodes', 'name')" class="form-field-error">{{ fieldError('nodes', 'name') }}</p>
            </div>
            <div class="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_6rem_7rem]">
              <div>
                <label class="form-label">Host</label>
                <input v-model="nodeForm.host" class="form-control" :class="{ 'form-control-error': fieldError('nodes', 'host') }" :aria-invalid="Boolean(fieldError('nodes', 'host'))" required @input="clearFieldError('nodes', 'host')" />
                <p v-if="fieldError('nodes', 'host')" class="form-field-error">{{ fieldError('nodes', 'host') }}</p>
              </div>
              <div>
                <label class="form-label">Port</label>
                <input v-model.number="nodeForm.port" class="form-control" :class="{ 'form-control-error': fieldError('nodes', 'port') }" :aria-invalid="Boolean(fieldError('nodes', 'port'))" type="number" required @input="clearFieldError('nodes', 'port')" />
                <p v-if="fieldError('nodes', 'port')" class="form-field-error">{{ fieldError('nodes', 'port') }}</p>
              </div>
              <div class="flex items-end pb-1">
                <div><label class="form-check"><input v-model="nodeForm.use_ssh" type="checkbox" class="rounded" @change="clearFieldError('nodes', 'use_ssh')" /><span>Use SSH</span></label><p v-if="fieldError('nodes', 'use_ssh')" class="form-field-error">{{ fieldError('nodes', 'use_ssh') }}</p></div>
              </div>
            </div>
            <div>
              <label class="form-label">Secret</label>
              <input v-model="nodeForm.secret" type="password" class="form-control" :class="{ 'form-control-error': fieldError('nodes', 'secret') }" :aria-invalid="Boolean(fieldError('nodes', 'secret'))" @input="clearFieldError('nodes', 'secret')" />
              <p v-if="fieldError('nodes', 'secret')" class="form-field-error">{{ fieldError('nodes', 'secret') }}</p>
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
        <div v-if="isForm('users')" :class="{ 'modal-backdrop': isModal('users') }">
        <section class="form-card" :class="{ 'modal-card': isModal('users') }" :role="isModal('users') ? 'dialog' : undefined" :aria-modal="isModal('users') || undefined" aria-labelledby="user-form-title">
          <button v-if="isModal('users')" type="button" class="modal-close" aria-label="Close user form" @click="closeForm('users')"><X :size="18" aria-hidden="true" /></button>
          <h3 id="user-form-title" class="form-title">{{ editing.users ? 'Update user' : 'Create user' }}</h3>
          <div v-if="formHasErrors('users')" class="form-error-summary" role="alert"><span aria-hidden="true">!</span><div><strong>User wasn’t saved</strong><p>{{ formErrorSummary('users') }}</p></div></div>
          <form class="form-stack" @submit.prevent="save('users', userForm)">
            <div>
              <label class="form-label">Username</label>
              <input v-model="userForm.username" class="form-control" :class="{ 'form-control-error': fieldError('users', 'username') }" :aria-invalid="Boolean(fieldError('users', 'username'))" required @input="clearFieldError('users', 'username')" />
              <p v-if="fieldError('users', 'username')" class="form-field-error">{{ fieldError('users', 'username') }}</p>
            </div>
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label class="form-label">First name</label>
                <input v-model="userForm.first_name" class="form-control" :class="{ 'form-control-error': fieldError('users', 'first_name') }" :aria-invalid="Boolean(fieldError('users', 'first_name'))" @input="clearFieldError('users', 'first_name')" />
                <p v-if="fieldError('users', 'first_name')" class="form-field-error">{{ fieldError('users', 'first_name') }}</p>
              </div>
              <div>
                <label class="form-label">Last name</label>
                <input v-model="userForm.last_name" class="form-control" :class="{ 'form-control-error': fieldError('users', 'last_name') }" :aria-invalid="Boolean(fieldError('users', 'last_name'))" @input="clearFieldError('users', 'last_name')" />
                <p v-if="fieldError('users', 'last_name')" class="form-field-error">{{ fieldError('users', 'last_name') }}</p>
              </div>
            </div>
            <div>
              <label class="form-label">Email</label>
              <input v-model="userForm.email" class="form-control" :class="{ 'form-control-error': fieldError('users', 'email') }" :aria-invalid="Boolean(fieldError('users', 'email'))" type="email" @input="clearFieldError('users', 'email')" />
              <p v-if="fieldError('users', 'email')" class="form-field-error">{{ fieldError('users', 'email') }}</p>
            </div>
            <div>
              <label class="form-label">Password</label>
              <input v-model="userForm.password" type="password" class="form-control" :class="{ 'form-control-error': fieldError('users', 'password') }" :aria-invalid="Boolean(fieldError('users', 'password'))" :required="!editing.users" @input="clearFieldError('users', 'password')" />
              <p v-if="fieldError('users', 'password')" class="form-field-error">{{ fieldError('users', 'password') }}</p>
            </div>
            <div class="form-actions"><button class="btn btn-primary">Save</button></div>
          </form>
        </section>
        </div>
      </div></main>

      <div
        v-if="deleteRequest"
        class="modal-backdrop"
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
