<template>
  <div class="card">
    <h2>Админка</h2>

    <!-- Отделы -->
    <section>
      <h3>Отделы</h3>
      <div class="row">
        <input v-model="newDeptName" placeholder="Название отдела..." />
        <button @click="createDepartment" class="btn secondary">Добавить</button>
        <button @click="loadDepartments" class="btn secondary">Обновить</button>
      </div>

      <div class="list mt">
        <div
          v-for="dept in departments"
          :key="dept.id"
          class="item accent-blue"
        >
          <div class="title">{{ dept.name }}</div>
          <div class="muted">ID: {{ dept.id }}</div>
        </div>

        <div v-if="departments.length === 0" class="muted" style="text-align: center; padding: 20px;">
          Отделы не созданы
        </div>
      </div>
    </section>

    <!-- Назначение курса -->
    <section class="mt">
      <h3>Назначить курс</h3>
      <div class="grid">
        <label>
          Пользователь
          <select v-model="assignUserId">
            <option value="">Выберите пользователя</option>
            <option v-for="user in users" :key="user.id" :value="user.id">
              {{ user.name }} ({{ user.email }})
            </option>
          </select>
        </label>

        <label>
          Курс
          <select v-model="assignCourseId">
            <option value="">Выберите курс</option>
            <option v-for="course in allCourses" :key="course.id" :value="course.id">
              {{ course.name }}
            </option>
          </select>
        </label>
      </div>

      <button @click="assignCourse" class="btn" style="margin-top: 12px;">
        Назначить
      </button>
    </section>

    <!-- Создание пользователя -->
    <section class="mt">
      <h3>Создать пользователя</h3>
      <div class="grid">
        <label>
          Email
          <input v-model="newUser.email" placeholder="user@company.com" />
        </label>

        <label>
          ФИО
          <input v-model="newUser.name" placeholder="Иван Иванов" />
        </label>

        <label>
          Пароль
          <input v-model="newUser.password" type="password" placeholder="min 6 символов" />
        </label>

        <label>
          Роль
          <select v-model="newUser.role">
            <option value="EMPLOYEE">EMPLOYEE</option>
            <option value="MENTOR">MENTOR</option>
            <option value="TEAM_LEAD">TEAM_LEAD</option>
            <option value="LD_MANAGER">LD_MANAGER</option>
            <option value="ADMIN">ADMIN</option>
          </select>
        </label>

        <label>
          Отдел
          <select v-model="newUser.department_id">
            <option value="">Выберите отдел</option>
            <option v-for="dept in departments" :key="dept.id" :value="dept.id">
              {{ dept.name }}
            </option>
          </select>
        </label>
      </div>

      <button @click="createUser" class="btn" style="margin-top: 12px;">
        Создать
      </button>
    </section>

    <!-- Список пользователей -->
    <section class="mt">
      <h3>Пользователи</h3>
      <button @click="loadUsers" class="btn secondary">Обновить</button>

      <div class="list mt">
        <div
          v-for="user in users"
          :key="user.id"
          :class="['item', getRoleClass(user.role)]"
        >
          <div class="title">{{ user.name }}</div>
          <div class="muted">{{ user.email }}</div>
          <div class="badge" style="margin-top: 8px;">{{ user.role }}</div>
          <div v-if="user.department" class="muted" style="margin-top: 5px;">
            Отдел: {{ user.department.name }}
          </div>
        </div>

        <div v-if="users.length === 0" class="muted" style="text-align: center; padding: 20px;">
          Пользователи не найдены
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue';
import api from '../services/api';

const showToast = inject('showToast', null);

// State
const departments = ref([]);
const users = ref([]);
const allCourses = ref([]);

const newDeptName = ref('');
const assignUserId = ref('');
const assignCourseId = ref('');

const newUser = ref({
  email: '',
  name: '',
  password: '',
  role: 'EMPLOYEE',
  department_id: ''
});

// Methods
const loadDepartments = async () => {
  try {
    const res = await api.getDepartments();
    departments.value = res.data;
  } catch (err) {
    console.error('Ошибка загрузки отделов:', err);
  }
};

const createDepartment = async () => {
  if (!newDeptName.value.trim()) {
    if (showToast) showToast('Введите название отдела', 'error');
    return;
  }

  try {
    await api.createDepartment({ name: newDeptName.value });
    if (showToast) showToast('Отдел создан!', 'success');
    newDeptName.value = '';
    await loadDepartments();
  } catch (err) {
    console.error('Ошибка создания отдела:', err);
    if (showToast) showToast('Ошибка создания отдела', 'error');
  }
};

const loadUsers = async () => {
  try {
    const res = await api.getUsers();
    users.value = res.data;
  } catch (err) {
    console.error('Ошибка загрузки пользователей:', err);
  }
};

const createUser = async () => {
  if (!newUser.value.email || !newUser.value.password || !newUser.value.name) {
    if (showToast) showToast('Заполните все обязательные поля', 'error');
    return;
  }

  try {
    await api.createUser(newUser.value);
    if (showToast) showToast('Пользователь создан!', 'success');

    // Очистка формы
    newUser.value = {
      email: '',
      name: '',
      password: '',
      role: 'EMPLOYEE',
      department_id: ''
    };

    await loadUsers();
  } catch (err) {
    console.error('Ошибка создания пользователя:', err);
    if (showToast) showToast('Ошибка создания пользователя', 'error');
  }
};

const assignCourse = async () => {
  if (!assignUserId.value || !assignCourseId.value) {
    if (showToast) showToast('Выберите пользователя и курс', 'error');
    return;
  }

  try {
    await api.assignCourse({
      user_id: assignUserId.value,
      course_id: assignCourseId.value
    });

    if (showToast) showToast('Курс назначен!', 'success');
    assignUserId.value = '';
    assignCourseId.value = '';
  } catch (err) {
    console.error('Ошибка назначения курса:', err);
    if (showToast) showToast('Ошибка назначения курса', 'error');
  }
};

const loadAllCourses = async () => {
  try {
    const res = await api.getMyCourses();
    allCourses.value = res.data;
  } catch (err) {
    console.error('Ошибка загрузки курсов:', err);
  }
};

const getRoleClass = (role) => {
  const roleMap = {
    'ADMIN': 'accent-red',
    'LD_MANAGER': 'accent-purple',
    'TEAM_LEAD': 'accent-blue',
    'MENTOR': 'accent-yellow',
    'EMPLOYEE': 'accent-green'
  };
  return roleMap[role] || '';
};

// Lifecycle
onMounted(() => {
  loadDepartments();
  loadUsers();
  loadAllCourses();
});
</script>

<style scoped>
/* Локальные стили */
</style>