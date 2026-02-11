<template>
  <div class="card">
    <h2>Стендап</h2>

    <!-- Форма отправки отчёта -->
    <div class="grid3">
      <label>
        День
        <input v-model.number="dayNumber" type="number" min="1" />
      </label>

      <label>
        Сделал
        <textarea v-model="doneText" rows="3"></textarea>
      </label>

      <label>
        План
        <textarea v-model="planText" rows="3"></textarea>
      </label>

      <label>
        Блокеры
        <textarea v-model="blockersText" rows="3"></textarea>
      </label>
    </div>

    <button @click="sendReport" class="btn" style="margin-top: 12px;">
      Отправить отчёт
    </button>

    <!-- Мои отчёты -->
    <h3 class="mt">Мои отчёты</h3>
    <button @click="loadMyReports" class="btn secondary">Обновить</button>

    <div class="list mt">
      <div
        v-for="report in myReports"
        :key="report.id"
        class="item accent-blue"
      >
        <div class="title">День {{ report.day_number }}</div>
        <div class="muted">{{ formatDate(report.created_at) }}</div>

        <div style="margin-top: 10px;">
          <strong>Сделал:</strong> {{ report.done || '-' }}
        </div>
        <div style="margin-top: 5px;">
          <strong>План:</strong> {{ report.plan || '-' }}
        </div>
        <div style="margin-top: 5px;">
          <strong>Блокеры:</strong> {{ report.blockers || '-' }}
        </div>
      </div>

      <div v-if="myReports.length === 0" class="muted" style="text-align: center; padding: 20px;">
        У вас пока нет отчётов
      </div>
    </div>

    <!-- Менторский блок (показывается только для менторов) -->
    <div v-if="isMentor">
      <h3 class="mt">Отчёты сотрудников</h3>
      <button @click="loadEmployeeReports" class="btn secondary">Обновить</button>

      <div class="list mt">
        <div
          v-for="report in employeeReports"
          :key="report.id"
          class="item accent-purple"
        >
          <div class="title">
            {{ report.user_name || 'Сотрудник' }} - День {{ report.day_number }}
          </div>
          <div class="muted">{{ formatDate(report.created_at) }}</div>

          <div style="margin-top: 10px;">
            <strong>Сделал:</strong> {{ report.done || '-' }}
          </div>
          <div style="margin-top: 5px;">
            <strong>План:</strong> {{ report.plan || '-' }}
          </div>
          <div style="margin-top: 5px;">
            <strong>Блокеры:</strong> {{ report.blockers || '-' }}
          </div>
        </div>

        <div v-if="employeeReports.length === 0" class="muted" style="text-align: center; padding: 20px;">
          Нет отчётов сотрудников
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue';
import api from '../services/api';

const showToast = inject('showToast', null);

// Form state
const dayNumber = ref(1);
const doneText = ref('');
const planText = ref('');
const blockersText = ref('');

// Reports
const myReports = ref([]);
const employeeReports = ref([]);
const isMentor = ref(false); // Определяется из профиля пользователя

// Methods
const sendReport = async () => {
  if (!doneText.value && !planText.value) {
    if (showToast) showToast('Заполните хотя бы одно поле', 'error');
    return;
  }

  try {
    await api.sendReport({
      day_number: dayNumber.value,
      done: doneText.value,
      plan: planText.value,
      blockers: blockersText.value
    });

    if (showToast) showToast('Отчёт отправлен!', 'success');

    // Очистка формы
    doneText.value = '';
    planText.value = '';
    blockersText.value = '';

    // Перезагрузка списка
    await loadMyReports();
  } catch (err) {
    console.error('Ошибка отправки отчёта:', err);
    if (showToast) showToast('Ошибка отправки отчёта', 'error');
  }
};

const loadMyReports = async () => {
  try {
    const res = await api.getMyReports();
    myReports.value = res.data;
  } catch (err) {
    console.error('Ошибка загрузки отчётов:', err);
  }
};

const loadEmployeeReports = async () => {
  try {
    // Предполагается, что есть эндпоинт для менторов
    // const res = await api.get('/standups/employees');
    // employeeReports.value = res.data;

    // Заглушка
    employeeReports.value = [];
  } catch (err) {
    console.error('Ошибка загрузки отчётов сотрудников:', err);
  }
};

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// Проверка роли (заглушка, нужно получать из API)
const checkMentorRole = async () => {
  // Здесь можно запросить профиль и проверить роль
  // const profile = await api.getProfile();
  // isMentor.value = ['MENTOR', 'TEAM_LEAD', 'ADMIN'].includes(profile.role);

  isMentor.value = false; // Заглушка
};

// Lifecycle
onMounted(() => {
  loadMyReports();
  checkMentorRole();
});
</script>

<style scoped>
/* Локальные стили */
</style>
