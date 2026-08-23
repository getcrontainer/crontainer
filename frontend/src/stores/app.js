import { defineStore } from "pinia";
import { reactive, ref } from "vue";

import { api } from "../api";

export const useAppStore = defineStore("app", () => {
  const currentUser = ref(null);
  const loading = ref(true);
  const error = ref("");
  const notice = ref("");
  const saveError = ref(null);
  const collections = reactive({ schedules: [], jobs: [], credentials: [], users: [], nodes: [] });

  function message(text) {
    notice.value = text;
    error.value = "";
  }

  function failure(err) {
    error.value = err.message;
    notice.value = "";
  }

  function clearMessages() {
    error.value = "";
    notice.value = "";
    saveError.value = null;
  }

  async function load(resource) {
    collections[resource] = await api.list(resource);
  }

  async function loadAll() {
    await Promise.all(Object.keys(collections).map(load));
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
      Object.keys(collections).forEach((key) => { collections[key] = []; });
      clearMessages();
    }
  }

  async function saveResource(resource, payload, id) {
    clearMessages();
    try {
      await api.save(resource, payload, id);
      await load(resource);
      message(`${resource.slice(0, -1)} saved.`);
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
      await load(resource);
      message("Deleted.");
      return true;
    } catch (err) {
      failure(err);
      return false;
    }
  }

  return {
    currentUser,
    loading,
    error,
    notice,
    collections,
    authenticate,
    initialise,
    load,
    loadAll,
    removeResource,
    saveResource,
    saveError,
    signOut,
  };
});
