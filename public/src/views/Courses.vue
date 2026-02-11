<template>
  <div class="card">
    <h2>Курсы</h2>

    <!-- Кнопки управления -->
    <div class="row" style="gap:10px;">
      <button @click="loadMyCourses" class="btn secondary">🔄 Обновить</button>
      <button @click="showCatalog = !showCatalog" class="btn secondary">
        {{ showCatalog ? '✖️ Скрыть каталог' : '📚 Открыть каталог' }}
      </button>
    </div>

    <!-- Двухколоночная сетка -->
    <div class="courses-2col mt">
      <!-- LEFT: Мои курсы -->
      <div id="myCoursesView">
        <div class="row" style="justify-content:space-between; align-items:center; gap:10px;">
          <h3 style="margin:0;">Мои курсы</h3>

          <!-- Фильтры -->
          <div class="row" style="gap:8px; flex-wrap:wrap;">
            <button
              @click="filterType = 'all'"
              :class="['btn', 'secondary', { activeFilter: filterType === 'all' }]"
            >
              Все
            </button>
            <button
              @click="filterType = 'active'"
              :class="['btn', 'secondary', { activeFilter: filterType === 'active' }]"
            >
              Активные
            </button>
            <button
              @click="filterType = 'completed'"
              :class="['btn', 'secondary', { activeFilter: filterType === 'completed' }]"
            >
              Завершённые
            </button>
          </div>
        </div>

        <!-- Список моих курсов -->
        <div class="list mt">
          <div
            v-for="course in filteredMyCourses"
            :key="course.course_id"
            :class="['item', getStatusClass(course)]"
          >
            <div class="title">{{ course.title }}</div>
            <div class="muted">{{ course.description || 'Описание отсутствует' }}</div>

            <!-- Прогресс -->
            <div class="progress-container">
              <div class="progress-bar" :style="{ width: course.progress_percent + '%' }"></div>
            </div>
            <div class="muted" style="margin-top: 5px;">
              Прогресс: {{ course.progress_percent }}% ({{ getCompletedCount(course) }}/{{ getTotalLessons(course) }} уроков)
            </div>

            <!-- Дедлайн -->
            <div v-if="course.deadline_at" class="muted" style="margin-top: 8px;">
              📅 Дедлайн: {{ formatDate(course.deadline_at) }}
              <span v-if="isOverdue(course.deadline_at)" style="color: #ef4444; font-weight: 600;">
                (просрочено!)
              </span>
            </div>

            <!-- Уроки с возможностью клика -->
            <div v-if="course.lessons && course.lessons.length > 0" class="lessons-list-container">
              <h4>📚 Уроки:</h4>

              <div
                v-for="(lesson, idx) in course.lessons"
                :key="lesson.id"
                :class="['lesson-link-item', {
                  completed: lesson.is_completed,
                  locked: isLessonLocked(course.lessons, idx)
                }]"
                @click="openLesson(course.course_id, lesson.id, isLessonLocked(course.lessons, idx))"
              >
                <span class="lesson-icon">
                  {{ lesson.is_completed ? '✅' : isLessonLocked(course.lessons, idx) ? '🔒' : '📄' }}
                </span>
                <span class="lesson-name">{{ lesson.title }}</span>
                <span v-if="lesson.is_completed" class="done-label">Пройдено</span>
                <span v-else-if="isLessonLocked(course.lessons, idx)" class="locked-label">Заблокировано</span>
              </div>
            </div>

            <!-- Кнопки действий -->
            <div class="row" style="margin-top: 12px; gap: 8px;">
              <button
                v-if="course.progress_percent === 0 && course.lessons.length > 0"
                @click="openLesson(course.course_id, course.lessons[0].id)"
                class="btn startBtn"
              >
                🚀 Начать курс
              </button>
              <button
                v-else-if="course.progress_percent < 100 && getNextLesson(course)"
                @click="openLesson(course.course_id, getNextLesson(course).id)"
                class="btn secondary contBtn"
              >
                ▶️ Продолжить (урок {{ getNextLesson(course).order }})
              </button>
              <span v-else-if="course.progress_percent === 100" class="badge" style="background: rgba(34, 197, 94, 0.2); color: #22c55e;">
                ✅ Курс завершён
              </span>
            </div>
          </div>

          <!-- Пустое состояние -->
          <div v-if="filteredMyCourses.length === 0" class="muted" style="text-align: center; padding: 20px;">
            {{ filterType === 'all' ? 'У вас пока нет назначенных курсов' : 'Нет курсов в этой категории' }}
          </div>
        </div>
      </div>
    </div>

    <!-- FULLSCREEN Catalog -->
    <section v-if="showCatalog" class="catalog-side mt">
      <div class="row" style="justify-content:space-between; align-items:center;">
        <h2 style="margin:0;">📚 Каталог курсов</h2>
        <button @click="showCatalog = false" class="btn secondary">✖️ Закрыть</button>
      </div>

      <div class="course-grid">
        <div
          v-for="course in catalogCourses"
          :key="course.course_id"
          :class="['course-card', { overdue: isOverdue(course.deadline_at) }]"
          @click="viewCourseDetails(course)"
        >
          <div class="course-cover">
            <div class="coverText">{{ course.title }}</div>
          </div>
          <div class="course-title">{{ course.title }}</div>
          <div class="muted">{{ course.description || 'Без описания' }}</div>

          <div class="progress">
            <div :style="{ width: (course.progress_percent || 0) + '%' }"></div>
          </div>

          <div class="course-meta">
            <span>{{ course.lessons?.length || 0 }} уроков</span>
            <span v-if="course.deadline_at">{{ formatDate(course.deadline_at) }}</span>
          </div>
        </div>
      </div>

      <div v-if="catalogCourses.length === 0" class="muted" style="text-align: center; padding: 40px;">
        Каталог пуст
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue';
import { useRouter } from 'vue-router';
import api from '../services/api';

const router = useRouter();
const showToast = inject('showToast', null);

// State
const myCourses = ref([]);
const catalogCourses = ref([]);
const filterType = ref('all');
const showCatalog = ref(false);

// Computed
const filteredMyCourses = computed(() => {
  if (filterType.value === 'active') {
    return myCourses.value.filter(c => c.progress_percent < 100);
  }
  if (filterType.value === 'completed') {
    return myCourses.value.filter(c => c.progress_percent === 100);
  }
  return myCourses.value;
});

// Methods
const loadMyCourses = async () => {
  try {
    const res = await api.getMyCourses();
    console.log('Loaded courses:', res.data);
    myCourses.value = res.data;
    catalogCourses.value = res.data;

    if (showToast) {
      showToast('Курсы обновлены', 'success', 2000);
    }
  } catch (err) {
    console.error('Ошибка загрузки курсов:', err);
    if (showToast) {
      showToast('Ошибка загрузки курсов', 'error');
    }
  }
};

const getStatusClass = (course) => {
  if (course.progress_percent === 100) return 'accent-green';
  if (isOverdue(course.deadline_at)) return 'accent-red';
  if (course.progress_percent > 0 && course.progress_percent < 50) return 'accent-yellow';
  if (course.progress_percent >= 50) return 'accent-blue';
  return '';
};

const isOverdue = (deadline) => {
  if (!deadline) return false;
  return new Date(deadline) < new Date();
};

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
};

const getTotalLessons = (course) => {
  return course.lessons?.length || 0;
};

const getCompletedCount = (course) => {
  return course.lessons?.filter(l => l.is_completed).length || 0;
};

const getNextLesson = (course) => {
  if (!course.lessons) return null;
  return course.lessons.find(l => !l.is_completed);
};

// Проверка блокировки урока
const isLessonLocked = (lessons, currentIndex) => {
  if (currentIndex === 0) return false;
  const previousLesson = lessons[currentIndex - 1];
  return !previousLesson?.is_completed;
};

// ИСПРАВЛЕНИЕ: Используем course_id, который возвращает API
const openLesson = (courseId, lessonId, isLocked = false) => {
  if (isLocked) {
    if (showToast) {
      showToast('🔒 Этот урок заблокирован. Завершите предыдущие уроки.', 'error');
    } else {
      alert('🔒 Этот урок заблокирован. Завершите предыдущие уроки.');
    }
    return;
  }

  console.log('Opening lesson:', { courseId, lessonId });
  router.push(`/course/${courseId}/lesson/${lessonId}`);
};

const viewCourseDetails = (course) => {
  if (!course.lessons || course.lessons.length === 0) {
    if (showToast) {
      showToast('В этом курсе пока нет уроков', 'info');
    }
    return;
  }

  const firstLesson = course.lessons[0];
  openLesson(course.course_id, firstLesson.id);
};

// Lifecycle
onMounted(() => {
  loadMyCourses();
});
</script>

<style scoped>
/* Дополнительные стили для блокированных уроков */
.lesson-link-item.locked {
  opacity: 0.5;
  cursor: not-allowed;
}

.lesson-link-item.locked:hover {
  background: #0b1220;
  border-color: #334155;
  transform: none;
}

.locked-label {
  font-size: 11px;
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}
</style>