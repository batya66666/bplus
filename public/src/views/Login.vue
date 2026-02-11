<template>
  <div class="container" style="max-width: 500px; margin-top: 80px;">
    <div class="card">
      <h2>Вход</h2>

      <div class="grid">
        <label>
          Email
          <input
            v-model="email"
            type="email"
            placeholder="admin@local.test"
            @keyup.enter="handleLogin"
          />
        </label>

        <label>
          Пароль
          <input
            v-model="password"
            type="password"
            placeholder="admin12345"
            @keyup.enter="handleLogin"
          />
        </label>
      </div>

      <button
        @click="handleLogin"
        :disabled="loading"
        class="btn"
        style="margin-top: 16px; width: 100%;"
      >
        {{ loading ? 'Вход...' : 'Войти' }}
      </button>

      <p v-if="error" class="hint" style="color: #ef4444;">
        {{ error }}
      </p>

      <p class="hint">
        Swagger: <a href="/docs" target="_blank">/docs</a>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import api from '../services/api';

const router = useRouter();

const email = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');

const handleLogin = async () => {
  if (!email.value || !password.value) {
    error.value = 'Заполните все поля';
    return;
  }

  loading.value = true;
  error.value = '';

  try {
    const res = await api.login(email.value, password.value);
    api.setToken(res.data.access_token);
    router.push('/courses');
  } catch (err) {
    console.error('Ошибка входа:', err);
    error.value = err.response?.data?.detail || 'Неверный email или пароль';
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
/* Локальные стили */
</style>