<template>
  <div>
    <!-- Topbar -->
    <div class="topbar">
      <div class="brand">B+ LMS</div>
      <div class="actions">
        <span class="badge">{{ userEmail }}</span>
        <button @click="handleLogout" class="btn secondary">Выйти</button>
      </div>
    </div>

    <!-- Container -->
    <div class="container">
      <!-- Navigation Tabs -->
      <div class="nav-tabs">
        <router-link to="/courses" class="nav-btn" active-class="active">Курсы</router-link>
        <router-link to="/standups" class="nav-btn" active-class="active">Стендапы</router-link>
        <router-link to="/documents" class="nav-btn" active-class="active">Регламенты</router-link>
        <router-link to="/admin" class="nav-btn" active-class="active">Админка</router-link>
      </div>

      <!-- Toast notifications -->
      <div v-if="toast.visible" :class="['toast', toast.type]">
        {{ toast.message }}
      </div>

      <!-- Router View -->
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, provide } from 'vue';
import { useRouter } from 'vue-router';
import api from '../services/api';

const router = useRouter();
const userEmail = ref('');

// Toast state
const toast = ref({
  visible: false,
  message: '',
  type: 'info' // 'success', 'error', 'info'
});

// Show toast function
const showToast = (message, type = 'info', duration = 3000) => {
  toast.value = { visible: true, message, type };
  setTimeout(() => {
    toast.value.visible = false;
  }, duration);
};

// Provide toast to child components
provide('showToast', showToast);

const handleLogout = () => {
  api.logout();
  router.push('/login');
};

onMounted(async () => {
  // Можно загрузить данные профиля
  const token = api.getToken();
  if (token) {
    // Декодируем email из токена или делаем запрос
    userEmail.value = 'user@example.com'; // Заглушка
  }
});
</script>

<style scoped>
/* Локальные стили если нужны */
</style>

