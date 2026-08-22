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
const listRouteNames = { schedules: "schedules", jobs: "jobs", credentials: "credentials", nodes: "nodes", users: "users" };

const route = useRoute();
const router = useRouter();
const appStore = useAppStore();
const { currentUser, loading, error, notice, collections } = storeToRefs(appStore);
const activeTab = computed(() => route.meta.resource || "schedules");
const mobileSidebarOpen = ref(false);
const userMenuOpen = ref(false);
const loginForm = reactive({ username: "", password: "" });
const editing = reactive({ schedules: null, credentials: null, users: null, nodes: null });
const scheduleForm = reactive(emptySchedule());
const credentialForm = reactive(emptyCredential());
const userForm = reactive(emptyUser());
const nodeForm = reactive(emptyNode());
const envRows = ref([]);
const deleteRequest = ref(null);
const deleting = ref(false);
const deleteError = ref("");

function emptySchedule() {
  return { name: "", image: "", cmd: "", parameters: "", cron_rule: "0 0 * * *", active: true, singleton: false, credential: null, cpu: null, memory: null };
}
function emptyCredential() { return { name: "", username: "", password: "", category: 1 }; }
function emptyUser() { return { username: "", email: "", first_name: "", last_name: "", password: "" }; }
function emptyNode() { return { name: "", host: "", port: 2375, use_ssh: false, secret: "" }; }
function replace(target, source) { Object.assign(target, source); }
function resetForm(resource) {
  editing[resource] = null;
  if (resource === "schedules") { replace(scheduleForm, emptySchedule()); envRows.value = []; }
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

function populateForm(resource, item) {
  editing[resource] = item;
  if (resource === "schedules") {
    replace(scheduleForm, { ...emptySchedule(), ...item });
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
  if (currentUser.value) syncRouteForm();
});

onMounted(() => {
  window.addEventListener("keydown", handleEscape);
  initialise();
});
onBeforeUnmount(() => window.removeEventListener("keydown", handleEscape));
</script>

<template>
  <main v-if="!loading">
    <section v-if="!currentUser" class="bg-amber-100 min-h-screen">
      <div class="flex flex-col items-center justify-center px-6 py-8 mx-auto min-h-screen lg:py-0">
        <div class="flex items-center mb-6 text-2xl font-semibold text-gray-900">Cr<Clock3 class="mx-0.5" :size="24" aria-hidden="true" />ntainer</div>
        <div class="w-full bg-white rounded-lg shadow sm:max-w-md xl:p-0">
          <div class="p-6 space-y-4 md:space-y-6 sm:p-8">
            <h1 class="text-xl font-bold leading-tight tracking-tight text-gray-900 md:text-2xl">Sign in to your account</h1>
            <p v-if="error" class="text-red-400">{{ error }}</p>
            <form class="space-y-4 md:space-y-6" @submit.prevent="authenticate">
              <div><label class="block mb-2 text-sm font-medium text-gray-900">Username</label><input v-model="loginForm.username" autocomplete="username" required class="bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5" /></div>
              <div><label class="block mb-2 text-sm font-medium text-gray-900">Password</label><input v-model="loginForm.password" type="password" autocomplete="current-password" required class="bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5" /></div>
              <button type="submit" class="w-full text-white bg-primary-600 hover:bg-primary-700 focus:ring-4 focus:outline-none focus:ring-primary-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center">Sign in</button>
            </form>
          </div>
        </div>
      </div>
    </section>

    <div v-else class="antialiased bg-gray-100">
      <nav class="bg-gray-100 px-4 py-2.5 fixed left-0 right-0 top-0 z-50">
        <div class="flex flex-wrap justify-between items-center">
          <div class="flex justify-start items-center">
            <button class="p-2 mr-2 text-gray-600 rounded-lg cursor-pointer md:hidden hover:text-gray-900 hover:bg-gray-200" @click="mobileSidebarOpen = !mobileSidebarOpen"><Menu :size="24" aria-hidden="true" /><span class="sr-only">Toggle sidebar</span></button>
            <RouterLink :to="{ name: 'schedules' }" class="flex items-center justify-between mr-4"><span class="flex items-center self-center text-2xl font-semibold whitespace-nowrap">CR<Clock3 class="mx-0.5" :size="24" aria-hidden="true" />NTAINER</span></RouterLink>
            <div class="hidden md:block md:pl-2"><label class="sr-only">Search</label><div class="relative md:w-96"><div class="flex absolute inset-y-0 left-0 items-center pl-3 pointer-events-none"><Search :size="20" class="text-gray-500" aria-hidden="true" /></div><input class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg block w-full pl-10 p-2.5" placeholder="Search" /></div></div>
          </div>
          <div class="relative flex items-center lg:order-3">
            <button class="flex mx-3 text-sm bg-gray-100 rounded-full focus:text-red-300" @click="userMenuOpen = !userMenuOpen"><span class="sr-only">Open user menu</span><Settings :size="20" aria-hidden="true" /></button>
            <div v-if="userMenuOpen" class="absolute right-0 top-8 z-50 my-4 w-56 text-base list-none bg-white rounded-xl divide-y divide-gray-100 shadow">
              <div class="py-3 px-4"><span class="block text-sm font-semibold text-gray-900">{{ currentUser.username }}</span><span class="block text-sm text-gray-900 truncate">{{ currentUser.email }}</span></div>
              <ul class="py-1 text-gray-700"><li><RouterLink :to="{ name: 'users' }" class="flex w-full items-center py-2 px-4 text-sm hover:bg-gray-100" @click="userMenuOpen = false"><Users :size="20" class="mr-2 text-gray-400" aria-hidden="true" />User management</RouterLink></li></ul>
              <ul class="py-1 text-gray-700"><li><button class="block w-full py-2 px-4 text-left text-sm hover:bg-gray-100" @click="signOut">Sign Out</button></li></ul>
            </div>
          </div>
        </div>
      </nav>

      <aside class="fixed top-0 left-0 z-40 w-64 h-screen pt-14 transition-transform bg-gray-100 border-r border-gray-100 md:translate-x-0" :class="mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full'" aria-label="Sidenav">
        <div class="overflow-y-auto py-5 px-4 h-full bg-gray-100">
          <ul class="space-y-2">
            <li v-for="[key, label, icon] in navItems" :key="key"><RouterLink :to="{ name: listRouteNames[key] }" class="flex items-center p-2 w-full text-base font-medium text-gray-900 rounded-lg hover:bg-gray-300 group" :class="{ 'bg-gray-200': activeTab === key }" @click="mobileSidebarOpen = false"><component :is="icon" :size="20" aria-hidden="true" /><span class="ml-3">{{ label }}</span><div class="w-full text-right text-gray-400">{{ collections[key].length }}</div></RouterLink></li>
          </ul>
          <ul class="pt-5 mt-5 space-y-2 border-t border-gray-200">
            <li><a href="https://github.com/getcrontainer/" target="_blank" rel="noreferrer" class="flex items-center p-2 text-base font-medium text-gray-900 rounded-lg hover:bg-gray-200"><BookOpen :size="18" aria-hidden="true" /><span class="ml-3">Docs</span></a></li>
            <li><a href="https://github.com/getcrontainer/" target="_blank" rel="noreferrer" class="flex items-center p-2 text-base font-medium text-gray-900 rounded-lg hover:bg-gray-200"><GitFork :size="18" aria-hidden="true" /><span class="ml-3">Github</span></a></li>
          </ul>
        </div>
      </aside>

      <main class="md:ml-64 pt-20 bg-gray-100 ml-5 min-h-screen"><div class="bg-white p-5 rounded-tl-3xl shadow-2xl min-h-[calc(100vh-80px)]">
        <p v-if="notice" class="mb-4 p-3 rounded-lg text-green-700 bg-green-50">{{ notice }}</p><p v-if="error" class="mb-4 p-3 rounded-lg text-red-700 bg-red-50">{{ error }}</p>

        <section v-if="isList('schedules')">
          <div class="container p-2"><h3 class="text-3xl text-gray-600 font-bold">Schedules</h3></div>
          <div class="not-format mt-4 relative overflow-x-auto rounded-lg mb-12">
            <table class="w-full text-sm text-left text-gray-500">
              <thead class="text-sm font-bold uppercase text-gray-400"><tr><th class="px-6 py-3">Name</th><th class="py-3 text-center">Active</th><th class="px-6 py-3 w-36">Cron Rule</th><th class="px-6 py-3">Source</th><th class="px-6 py-3">CPU</th><th class="px-6 py-3">Memory</th><th class="px-6 py-3">Owner</th><th class="px-6 py-3 w-36">Action</th></tr></thead>
              <tbody><tr v-for="schedule in collections.schedules" :key="schedule.id" class="default-table-row"><td class="px-6 py-4 text-gray-900 rounded-s-xl"><div class="text-base font-semibold">{{ schedule.name }}</div><div class="text-xs font-semibold text-gray-500">{{ schedule.id }}</div></td><td class="text-center"><div class="inline-flex h-2.5 w-2.5 rounded-full" :class="schedule.active ? 'bg-green-500' : 'bg-red-500'"></div></td><td class="px-6 py-4"><span :title="schedule.cron_description">{{ schedule.cron_rule }}</span></td><td class="px-6 py-4"><div class="flex items-center">
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
          <RouterLink :to="{ name: 'schedule-new' }" class="fixed end-6 bottom-6 btn-primary rounded-full w-14 h-14 items-center justify-center flex px-0 py-0" aria-label="Add schedule"><Plus :size="30" aria-hidden="true" /></RouterLink>
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
              <label class="form-label">Cron rule</label>
              <input v-model="scheduleForm.cron_rule" class="form-control" required />
              <span class="form-help">Use a five-part cron expression.</span>
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

        <section v-if="isList('jobs')"><div class="container p-2"><h3 class="text-3xl text-gray-600 font-bold">Jobs</h3></div><div class="not-format mt-4 relative overflow-x-auto rounded-lg"><table class="w-full text-sm text-left text-gray-500"><thead class="text-sm font-bold uppercase text-gray-400"><tr><th class="px-6 py-3 w-10"><input type="checkbox" class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded" /></th><th class="px-6 py-3">Id</th><th class="px-6 py-3">Status</th><th class="px-6 py-3">Schedule</th><th class="px-6 py-3">Cron rule</th><th class="px-6 py-3">Started at</th><th class="px-6 py-3">Duration</th><th class="px-6 py-3">Action</th></tr></thead><tbody><tr v-for="job in collections.jobs" :key="job.id" class="default-table-row"><td class="px-6 py-4 rounded-s-xl"><input type="checkbox" class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded" /></td><td class="px-6 py-4 text-gray-600 whitespace-nowrap">{{ job.id }}</td><td class="px-6 py-4">{{ job.status }} ({{ job.status_code ?? '—' }})</td><td class="px-6 py-4">{{ job.schedule_name }}</td><td class="px-6 py-4">{{ job.schedule_cron_rule || '—' }}</td><td class="px-6 py-4">{{ new Date(job.created_at).toLocaleString() }}</td><td class="px-6 py-4">{{ job.duration }}s</td><td class="px-6 py-4"><details v-if="job.log"><summary class="btn-mini-edit" aria-label="Show job log"><Logs :size="18" aria-hidden="true" /></summary><pre class="mt-2 whitespace-pre-wrap">{{ job.log }}</pre></details><span v-else class="btn-mini-edit bg-gray-100 text-gray-400" aria-label="No job log"><Logs :size="18" aria-hidden="true" /></span></td></tr></tbody></table></div></section>

        <section v-if="isList('credentials')"><div class="container p-2"><h3 class="text-3xl text-gray-600 font-bold">Credentials</h3></div><div class="not-format mt-4 relative overflow-x-auto rounded-lg"><table class="w-full text-sm text-left text-gray-500"><thead class="text-sm font-bold uppercase text-gray-400"><tr><th class="px-6 py-3">Name</th><th class="px-6 py-3">Category</th><th class="px-6 py-3">Username</th><th class="px-6 py-3">Schedules</th><th class="px-6 py-3 w-36">Action</th></tr></thead><tbody><tr v-for="credential in collections.credentials" :key="credential.id" class="default-table-row"><td class="px-6 py-4 text-gray-900 rounded-s-xl"><div class="text-base font-semibold">{{ credential.name }}</div></td><td class="px-6 py-4">{{ categoryName(credential.category) }}</td><td class="px-6 py-4">{{ credential.username }}</td><td class="px-6 py-4">{{ credentialScheduleCount(credential.id) }}</td><td class="px-6 py-4 rounded-e-xl"><button class="btn-mini-remove" aria-label="Delete credential" @click="requestDelete('credentials', credential)"><Trash2 :size="18" aria-hidden="true" /></button> <RouterLink :to="{ name: 'credential-edit', params: { id: credential.id } }" class="btn-mini-edit inline-flex items-center justify-center" aria-label="Edit credential"><Pencil :size="18" aria-hidden="true" /></RouterLink></td></tr></tbody></table></div><RouterLink :to="{ name: 'credential-new' }" class="fixed end-6 bottom-6 btn-primary rounded-full w-14 h-14 items-center justify-center flex px-0 py-0" aria-label="Add credential"><Plus :size="30" aria-hidden="true" /></RouterLink></section>
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

        <section v-if="isList('nodes')"><div class="container p-2"><h3 class="text-3xl text-gray-600 font-bold">Nodes</h3></div><div class="not-format mt-4 relative overflow-x-auto rounded-lg"><table class="w-full text-sm text-left text-gray-500"><thead class="text-sm font-bold uppercase text-gray-400"><tr><th class="px-6 py-3 w-10"><input type="checkbox" class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded" /></th><th class="px-6 py-3">Name</th><th class="px-6 py-3">Host</th><th class="px-6 py-3">Port</th><th class="px-6 py-3">Use SSH</th><th class="px-6 py-3">Secret</th><th class="px-6 py-3 w-36">Action</th></tr></thead><tbody><tr v-for="node in collections.nodes" :key="node.id" class="default-table-row"><td class="px-6 py-4 rounded-s-xl"><input type="checkbox" class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded" /></td><td class="px-6 py-4 text-gray-600 whitespace-nowrap"><div class="text-base font-semibold">{{ node.name }}</div></td><td class="px-6 py-4">{{ node.host }}</td><td class="px-6 py-4">{{ node.port }}</td><td class="px-6 py-4">{{ node.use_ssh }}</td><td class="px-6 py-4">••••••••</td><td class="px-6 py-4"><button class="btn-mini-remove" aria-label="Delete node" @click="requestDelete('nodes', node)"><Trash2 :size="18" aria-hidden="true" /></button> <RouterLink :to="{ name: 'node-edit', params: { id: node.id } }" class="btn-mini-edit inline-flex items-center justify-center" aria-label="Edit node"><Pencil :size="18" aria-hidden="true" /></RouterLink></td></tr></tbody></table></div><RouterLink :to="{ name: 'node-new' }" class="fixed end-6 bottom-6 btn-primary rounded-full w-14 h-14 items-center justify-center flex px-0 py-0" aria-label="Add node"><Plus :size="30" aria-hidden="true" /></RouterLink></section>
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

        <section v-if="isList('users')"><div class="container p-2"><h3 class="text-3xl text-gray-600 font-bold">Users</h3></div><div class="not-format mt-4 relative overflow-x-auto rounded-lg"><table class="w-full text-sm text-left text-gray-500"><thead class="text-sm font-bold uppercase text-gray-400"><tr><th class="px-6 py-3">Name/Email</th><th class="px-6 py-3">Username</th><th class="px-6 py-3">Joined at</th><th class="px-6 py-3">Last login</th><th class="px-6 py-3">Admin</th><th class="px-6 py-3 w-36">Action</th></tr></thead><tbody class="text-gray-700"><tr v-for="user in collections.users" :key="user.id" class="default-table-row"><td class="px-6 py-4 text-gray-900 rounded-s-xl">{{ [user.first_name, user.last_name].filter(Boolean).join(' ') }}<br /><small>{{ user.email }}</small></td><td class="px-6 py-4">{{ user.username }}</td><td class="px-6 py-4">{{ user.date_joined ? new Date(user.date_joined).toLocaleString() : '—' }}</td><td class="px-6 py-4">{{ user.last_login ? new Date(user.last_login).toLocaleString() : '—' }}</td><td class="px-6 py-4"><Check v-if="user.is_superuser" :size="20" class="text-green-600" aria-label="Administrator" /></td><td class="px-6 py-4 rounded-e-xl"><button class="btn-mini-remove" aria-label="Delete user" @click="requestDelete('users', user)"><Trash2 :size="18" aria-hidden="true" /></button> <RouterLink :to="{ name: 'user-edit', params: { id: user.id } }" class="btn-mini-edit inline-flex items-center justify-center" aria-label="Edit user"><Pencil :size="18" aria-hidden="true" /></RouterLink></td></tr></tbody></table></div><RouterLink :to="{ name: 'user-new' }" class="fixed end-6 bottom-6 btn-primary rounded-full w-14 h-14 items-center justify-center flex px-0 py-0" aria-label="Add user"><Plus :size="30" aria-hidden="true" /></RouterLink></section>
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
  <div v-else class="min-h-screen grid place-items-center bg-gray-100 text-gray-500">Loading Crontainer…</div>
</template>
