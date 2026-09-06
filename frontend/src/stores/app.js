import { defineStore } from "pinia";
import { reactive, ref } from "vue";

import { api } from "../api";

const resourceNames = ["schedules", "jobs", "credentials", "users", "nodes"];

function emptyPagination() {
  return { count: 0, next: null, previous: null, loadingMore: false };
}

function emptySummary() {
  return {
    schedules: { total: 0, active: 0 },
    jobs: { total: 0, healthy: 0 },
    credentials: { total: 0 },
    users: { total: 0, administrators: 0 },
    nodes: { total: 0, ssh: 0 },
  };
}

export const useAppStore = defineStore("app", () => {
  const currentUser = ref(null);
  const loading = ref(true);
  const error = ref("");
  const notice = ref(null);
  const saveError = ref(null);
  const collections = reactive(Object.fromEntries(resourceNames.map((resource) => [resource, []])));
  const pagination = reactive(Object.fromEntries(resourceNames.map((resource) => [resource, emptyPagination()])));
  const dashboardSummary = reactive(emptySummary());
  const jobFilterOptions = reactive({ statuses: [], schedules: [] });

  function message(action, resource, item = {}) {
    const singular = resource.slice(0, -1);
    const resourceLabel = singular.charAt(0).toUpperCase() + singular.slice(1);
    const itemLabel = item.name || item.username;
    const subject = itemLabel ? `“${itemLabel}”` : `The ${singular}`;
    const copy = {
      create: {
        title: `${resourceLabel} created`,
        detail: resource === "schedules" ? `${subject} is ready to run.` : `${subject} is ready to use.`,
      },
      edit: {
        title: `${resourceLabel} updated`,
        detail: itemLabel ? `Changes to ${subject} were saved.` : "Your changes were saved successfully.",
      },
      delete: {
        title: `${resourceLabel} deleted`,
        detail: `${subject} was removed successfully.`,
      },
    }[action];
    notice.value = { action, ...copy };
    error.value = "";
  }

  function failure(err) {
    error.value = err.message;
    notice.value = null;
  }

  function clearMessages() {
    error.value = "";
    notice.value = null;
    saveError.value = null;
  }

  async function load(resource, { append = false, page = null, filters = {} } = {}) {
    const response = await api.list(resource, page, filters);
    const items = Array.isArray(response) ? response : response.results;
    if (append) {
      const existingIds = new Set(collections[resource].map((item) => item.id));
      collections[resource].push(...items.filter((item) => !existingIds.has(item.id)));
    } else {
      collections[resource] = items;
    }
    Object.assign(pagination[resource], {
      count: Array.isArray(response) ? items.length : response.count,
      next: Array.isArray(response) ? null : response.next,
      previous: Array.isArray(response) ? null : response.previous,
    });
  }

  async function loadMore(resource) {
    const page = pagination[resource].next;
    if (!page || pagination[resource].loadingMore) return;
    pagination[resource].loadingMore = true;
    try {
      await load(resource, { append: true, page });
    } finally {
      pagination[resource].loadingMore = false;
    }
  }

  async function loadDashboardSummary() {
    const summary = await api.dashboardSummary();
    resourceNames.forEach((resource) => Object.assign(dashboardSummary[resource], summary[resource]));
  }

  async function loadJobFilterOptions() {
    const options = await api.jobFilterOptions();
    jobFilterOptions.statuses = options.statuses;
    jobFilterOptions.schedules = options.schedules;
  }

  async function loadAll() {
    await Promise.all([
      ...resourceNames.map((resource) => load(resource)),
      loadDashboardSummary(),
      loadJobFilterOptions(),
    ]);
  }

  async function initialise() {
    loading.value = true;
    clearMessages();
    try {
      await api.csrf();
      currentUser.value = await api.currentUser();
      await loadAll();
    } catch (err) {
      currentUser.value = null;
      if (err.status !== 401 && err.status !== 403) failure(err);
    } finally {
      loading.value = false;
    }
  }

  async function authenticate(credentials) {
    clearMessages();
    try {
      await api.csrf();
      currentUser.value = await api.login(credentials);
      await loadAll();
      return true;
    } catch (err) {
      failure(err);
      return false;
    }
  }

  async function signOut() {
    try {
      await api.logout();
    } finally {
      currentUser.value = null;
      resourceNames.forEach((resource) => {
        collections[resource] = [];
        Object.assign(pagination[resource], emptyPagination());
        Object.assign(dashboardSummary[resource], emptySummary()[resource]);
      });
      jobFilterOptions.statuses = [];
      jobFilterOptions.schedules = [];
      clearMessages();
    }
  }

  async function saveResource(resource, payload, id) {
    clearMessages();
    try {
      await api.save(resource, payload, id);
      await Promise.all([load(resource), loadDashboardSummary()]);
      message(id == null ? "create" : "edit", resource, payload);
      return true;
    } catch (err) {
      saveError.value = err;
      return false;
    }
  }

  async function removeResource(resource, item) {
    clearMessages();
    try {
      await api.remove(resource, item.id);
      await Promise.all([load(resource), loadDashboardSummary()]);
      message("delete", resource, item);
      return true;
    } catch (err) {
      failure(err);
      return false;
    }
  }

  return {
    currentUser,
    dashboardSummary,
    jobFilterOptions,
    loading,
    error,
    notice,
    collections,
    authenticate,
    initialise,
    load,
    loadAll,
    loadDashboardSummary,
    loadJobFilterOptions,
    loadMore,
    pagination,
    removeResource,
    saveResource,
    saveError,
    signOut,
  };
});
