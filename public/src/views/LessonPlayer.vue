<template>
  <div class="player-layout">
    <!-- Sidebar с модулями -->
    <aside class="lessons-sidebar">
      <div class="sidebar-header">
        <h3>{{ course?.title || 'Курс' }}</h3>
        <button @click="goBack" class="btn secondary">← Назад</button>
      </div>

      <div v-if="lessons.length > 0" class="modules-list">
        <div class="module-block">
          <h4 class="module-title">Уроки курса</h4>
          <div
            v-for="(lesson, idx) in lessons"
            :key="lesson.id"
            @click="selectLesson(lesson)"
            :class="['lesson-item', {
              active: currentLesson?.id === lesson.id,
              locked: isLessonLocked(idx),
              completed: lesson.is_completed
            }]"
          >
            <span class="lesson-icon">
              <template v-if="lesson.is_completed">✅</template>
              <template v-else-if="isLessonLocked(idx)">🔒</template>
              <template v-else>▶️</template>
            </span>
            <span class="lesson-title">{{ lesson.title }}</span>
          </div>
        </div>
      </div>

      <div v-else class="no-lessons">
        <p class="muted">Загрузка уроков...</p>
      </div>
    </aside>

    <!-- Основная область плеера -->
    <main class="player-main">
      <div v-if="loading" class="loading">Загрузка урока...</div>

      <template v-else-if="currentLesson">
        <div class="lesson-header">
          <h2>{{ currentLesson.title }}</h2>
          <span v-if="currentLesson.is_completed" class="badge completed-badge">✅ Пройдено</span>
        </div>

        <div class="video-container">
          <!-- YouTube видео -->
          <template v-if="isYouTube">
            <div id="youtube-player-container"></div>
            <div v-if="!embedUrl" class="no-video">
              <p>❌ Ошибка в URL видео</p>
            </div>
          </template>

          <!-- HTML5 видео -->
          <template v-else-if="currentLesson.video_url">
            <video
              ref="videoPlayer"
              :src="currentLesson.video_url"
              controls
              controlsList="nodownload"
              @timeupdate="handleTimeUpdate"
              @ended="handleVideoEnd"
              @seeking="handleSeeking"
              @seeked="handleSeeked"
              @loadedmetadata="onVideoLoaded"
              class="video-player"
            ></video>
          </template>

          <!-- Нет видео -->
          <div v-else class="no-video">
            <p>📹 Видео отсутствует</p>
          </div>
        </div>

        <div class="progress-info">
          <div class="progress-bar-container">
            <div class="progress-bar-fill" :style="{ width: watchedPercent + '%' }"></div>
          </div>
          <div class="progress-text muted">
            Прогресс просмотра: {{ watchedPercent }}%
            <span v-if="!isFirstWatch" class="rewatching-label">(повторный просмотр)</span>
          </div>
        </div>

        <div v-if="currentLesson.content" class="lesson-content">
          <h3>Описание</h3>
          <p class="content-text">{{ currentLesson.content }}</p>
        </div>

        <div class="lesson-footer">
          <button
            v-if="!currentLesson.is_completed && watchedPercent >= 95"
            @click="markCompleted(true)"
            class="btn primary"
          >
            ✅ Отметить как пройденный
          </button>
          <button
            v-else-if="!currentLesson.is_completed"
            class="btn primary"
            disabled
            title="Досмотрите видео до 95% для завершения"
          >
            🔒 Досмотрите до конца ({{ watchedPercent }}%)
          </button>
          <button
            v-else
            @click="markCompleted(false)"
            class="btn secondary"
          >
            ❌ Снять отметку
          </button>

          <button
            v-if="nextLesson && !isLessonLocked(getNextLessonIndex())"
            @click="goToNextLesson"
            class="btn secondary"
          >
            ➡️ Следующий урок
          </button>
          <button
            v-else-if="nextLesson"
            class="btn secondary"
            disabled
            title="Завершите текущий урок для разблокировки"
          >
            🔒 Следующий урок (заблокирован)
          </button>
        </div>
      </template>

      <div v-else class="no-lesson">
        <p>Выберите урок из списка слева</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from '../services/api';

const route = useRoute();
const router = useRouter();

// ИСПРАВЛЕНИЕ: courseId из route.params - это строка, конвертируем в число
const courseId = ref(parseInt(route.params.courseId));
const lessonId = ref(parseInt(route.params.lessonId));

const loading = ref(true);
const course = ref(null);
const lessons = ref([]);
const currentLesson = ref(null);
const currentPositionSec = ref(0);
const watchedPercent = ref(0);
const maxWatchedPositionSec = ref(0);
const isFirstWatch = ref(true);
const videoDuration = ref(0);

const videoPlayer = ref(null);
let youtubePlayer = null;
let saveProgressInterval = null;

// ========== COMPUTED ==========

const isYouTube = computed(() => {
  const url = currentLesson.value?.video_url;
  return url && (url.includes('youtube.com') || url.includes('youtu.be'));
});

const embedUrl = computed(() => {
  if (!isYouTube.value) return '';
  const url = currentLesson.value.video_url;
  const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
  const match = url.match(regExp);
  const videoId = match && match[2].length === 11 ? match[2] : null;
  return videoId;
});

const nextLesson = computed(() => {
  const currentIdx = lessons.value.findIndex(l => l.id === currentLesson.value?.id);
  return lessons.value[currentIdx + 1] || null;
});

const getNextLessonIndex = () => {
  const currentIdx = lessons.value.findIndex(l => l.id === currentLesson.value?.id);
  return currentIdx + 1;
};

// ========== БЛОКИРОВКА УРОКОВ ==========

const isLessonLocked = (lessonIndex) => {
  if (lessonIndex === 0) return false;
  const previousLesson = lessons.value[lessonIndex - 1];
  return !previousLesson?.is_completed;
};

// ========== ЗАГРУЗКА ДАННЫХ ==========

const loadCourse = async () => {
  try {
    console.log('Loading course, courseId:', courseId.value);
    const { data } = await api.getMyCourses();
    console.log('Received courses:', data);

    // ИСПРАВЛЕНИЕ: API возвращает 'course_id', проверяем оба варианта
    course.value = data.find(c => c.course_id === courseId.value);

    if (!course.value) {
      console.error('Course not found with id:', courseId.value);
      console.log('Available courses:', data.map(c => ({ id: c.course_id, title: c.title })));
      return;
    }

    console.log('Found course:', course.value);
    lessons.value = course.value.lessons || [];
    console.log('Loaded lessons:', lessons.value.length, 'lessons');
  } catch (error) {
    console.error('Error loading course:', error);
  }
};

const loadLesson = async () => {
  loading.value = true;
  try {
    console.log('Loading lesson:', lessonId.value);
    const { data } = await api.getLessonDetail(lessonId.value);
    console.log('Loaded lesson data:', data);

    currentLesson.value = data;
    currentPositionSec.value = data.current_position_sec || 0;

    // Загрузка сохранённого прогресса
    const progressRes = await api.getVideoProgress(lessonId.value);
    console.log('Progress data:', progressRes.data);

    if (progressRes.data) {
      currentPositionSec.value = progressRes.data.position_sec || 0;
      watchedPercent.value = progressRes.data.watched_percent || 0;
      maxWatchedPositionSec.value = currentPositionSec.value;
      isFirstWatch.value = watchedPercent.value < 95;
    }

    // Обновляем статус в списке уроков
    const lessonInList = lessons.value.find(l => l.id === lessonId.value);
    if (lessonInList) {
      lessonInList.is_completed = data.is_completed;
    }

    // Ждём рендера и инициализируем плеер
    await nextTick();

    if (isYouTube.value) {
      initYouTubePlayer();
    } else if (videoPlayer.value) {
      videoPlayer.value.currentTime = currentPositionSec.value;
    }
  } catch (error) {
    console.error('Error loading lesson:', error);
    if (error.response?.status === 403) {
      alert('❌ Предыдущий урок не завершён. Пройдите его сначала.');
      goBack();
    }
  } finally {
    loading.value = false;
  }
};

// ========== YOUTUBE PLAYER ==========

const initYouTubePlayer = () => {
  if (!window.YT) {
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    const firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

    window.onYouTubeIframeAPIReady = createYouTubePlayer;
  } else {
    createYouTubePlayer();
  }
};

const createYouTubePlayer = () => {
  if (!embedUrl.value) return;

  youtubePlayer = new window.YT.Player('youtube-player-container', {
    height: '100%',
    width: '100%',
    videoId: embedUrl.value,
    playerVars: {
      autoplay: 0,
      controls: 1,
      disablekb: 1,
      fs: 1,
      modestbranding: 1,
      rel: 0,
      start: currentPositionSec.value,
    },
    events: {
      onReady: onYouTubePlayerReady,
      onStateChange: onYouTubePlayerStateChange,
    },
  });
};

const onYouTubePlayerReady = (event) => {
  if (currentPositionSec.value > 0) {
    event.target.seekTo(currentPositionSec.value, true);
  }

  videoDuration.value = event.target.getDuration();
  startYouTubeProgressTracking();
};

const onYouTubePlayerStateChange = (event) => {
  if (event.data === 0) {
    handleYouTubeVideoEnd();
  }
};

const startYouTubeProgressTracking = () => {
  setInterval(() => {
    if (youtubePlayer && youtubePlayer.getCurrentTime) {
      const currentTime = youtubePlayer.getCurrentTime();
      const duration = youtubePlayer.getDuration();

      currentPositionSec.value = Math.floor(currentTime);
      watchedPercent.value = Math.min(100, Math.round((currentTime / duration) * 100) || 0);

      if (currentPositionSec.value > maxWatchedPositionSec.value) {
        maxWatchedPositionSec.value = currentPositionSec.value;
      }

      if (isFirstWatch.value && currentTime > maxWatchedPositionSec.value + 2) {
        youtubePlayer.seekTo(maxWatchedPositionSec.value, true);
        alert('⏸️ Нельзя перематывать видео вперёд при первом просмотре');
      }
    }
  }, 1000);
};

const handleYouTubeVideoEnd = () => {
  watchedPercent.value = 100;
  saveProgress();
};

// ========== HTML5 VIDEO HANDLERS ==========

const onVideoLoaded = () => {
  if (videoPlayer.value) {
    videoDuration.value = videoPlayer.value.duration;
    videoPlayer.value.currentTime = currentPositionSec.value;
  }
};

const handleTimeUpdate = () => {
  if (!videoPlayer.value) return;

  currentPositionSec.value = Math.floor(videoPlayer.value.currentTime);
  watchedPercent.value = Math.min(100, Math.round((videoPlayer.value.currentTime / videoPlayer.value.duration) * 100) || 0);

  if (currentPositionSec.value > maxWatchedPositionSec.value) {
    maxWatchedPositionSec.value = currentPositionSec.value;
  }
};

const handleSeeking = () => {
  if (!videoPlayer.value || !isFirstWatch.value) return;

  const seekTime = videoPlayer.value.currentTime;

  if (seekTime > maxWatchedPositionSec.value + 2) {
    videoPlayer.value.currentTime = maxWatchedPositionSec.value;
  }
};

const handleSeeked = () => {
  if (!videoPlayer.value || !isFirstWatch.value) return;

  if (videoPlayer.value.currentTime > maxWatchedPositionSec.value + 2) {
    videoPlayer.value.currentTime = maxWatchedPositionSec.value;
    alert('⏸️ Нельзя перематывать видео вперёд при первом просмотре');
  }
};

const handleVideoEnd = () => {
  watchedPercent.value = 100;
  saveProgress();
  if (!currentLesson.value.is_completed) {
    markCompleted(true);
  }
};

// ========== СОХРАНЕНИЕ ПРОГРЕССА ==========

const saveProgress = async () => {
  if (!currentLesson.value) return;

  try {
    await api.saveVideoProgress(currentLesson.value.id, {
      position_sec: currentPositionSec.value,
      watched_percent: watchedPercent.value
    });
  } catch (error) {
    console.error('Error saving progress:', error);
  }
};

const startAutoSave = () => {
  saveProgressInterval = setInterval(() => {
    saveProgress();
  }, 10000);
};

const stopAutoSave = () => {
  if (saveProgressInterval) {
    clearInterval(saveProgressInterval);
    saveProgressInterval = null;
  }
};

// ========== ЗАВЕРШЕНИЕ УРОКА ==========

const markCompleted = async (completed = true) => {
  if (completed && watchedPercent.value < 95) {
    alert('⚠️ Досмотрите видео до конца перед завершением урока');
    return;
  }

  try {
    await api.completeLesson({
      lesson_id: currentLesson.value.id,
      completed
    });

    currentLesson.value.is_completed = completed;

    // Обновляем статус в списке уроков
    const lessonInList = lessons.value.find(l => l.id === currentLesson.value.id);
    if (lessonInList) {
      lessonInList.is_completed = completed;
    }

    if (completed) {
      alert('✅ Урок успешно завершён!');
    }
  } catch (error) {
    console.error('Error completing lesson:', error);
    alert('❌ Ошибка при завершении урока');
  }
};

// ========== НАВИГАЦИЯ ==========

const selectLesson = (lesson) => {
  const idx = lessons.value.findIndex(l => l.id === lesson.id);

  if (isLessonLocked(idx)) {
    alert('🔒 Этот урок заблокирован. Завершите предыдущие уроки.');
    return;
  }

  stopAutoSave();
  saveProgress();

  router.push(`/course/${courseId.value}/lesson/${lesson.id}`);
};

const goToNextLesson = () => {
  if (!nextLesson.value) {
    alert('🎉 Вы завершили все уроки этого курса!');
    return;
  }

  if (isLessonLocked(getNextLessonIndex())) {
    alert('🔒 Завершите текущий урок для доступа к следующему');
    return;
  }

  selectLesson(nextLesson.value);
};

const goBack = () => {
  stopAutoSave();
  saveProgress();
  router.push('/courses');
};

// ========== LIFECYCLE ==========

watch(() => route.params.lessonId, async (newId) => {
  if (newId) {
    lessonId.value = parseInt(newId);
    stopAutoSave();
    await loadLesson();
    startAutoSave();
  }
});

onMounted(async () => {
  console.log('Component mounted');
  await loadCourse();
  await loadLesson();
  startAutoSave();
});

onUnmounted(() => {
  stopAutoSave();
  saveProgress();

  if (youtubePlayer) {
    youtubePlayer.destroy();
  }
});
</script>

<style scoped>
.player-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  height: calc(100vh - 60px);
  background: var(--color-bg-primary);
}

.lessons-sidebar {
  border-right: 1px solid var(--color-border);
  padding: 20px;
  overflow-y: auto;
  background: var(--color-bg-secondary);
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  gap: 10px;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: var(--color-text);
}

.module-block {
  margin-bottom: 20px;
}

.module-title {
  font-size: 0.9rem;
  margin-bottom: 8px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  font-weight: 600;
}

.lesson-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  margin-bottom: 6px;
}

.lesson-item:hover:not(.locked) {
  background: var(--color-bg-card);
  transform: translateX(4px);
}

.lesson-item.active {
  background: rgba(99, 102, 241, 0.15);
  color: var(--color-accent);
  border-color: var(--color-accent);
}

.lesson-item.completed {
  border-color: rgba(34, 197, 94, 0.3);
}

.lesson-item.locked {
  color: var(--color-text-muted);
  cursor: not-allowed;
  opacity: 0.5;
}

.lesson-icon {
  font-size: 1.1rem;
  flex-shrink: 0;
}

.lesson-title {
  flex: 1;
  font-size: 0.9rem;
}

.no-lessons {
  text-align: center;
  padding: 20px;
}

.player-main {
  padding: 30px;
  overflow-y: auto;
}

.loading {
  text-align: center;
  padding: 60px;
  font-size: 1.2rem;
  color: var(--color-text-muted);
}

.lesson-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.lesson-header h2 {
  margin: 0;
  font-size: 1.8rem;
}

.badge {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
}

.completed-badge {
  background: #22c55e;
  color: white;
}

.video-container {
  border-radius: 14px;
  overflow: hidden;
  background: #000;
  aspect-ratio: 16/9;
  position: relative;
  margin-bottom: 20px;
}

#youtube-player-container {
  width: 100%;
  height: 100%;
}

.video-player {
  width: 100%;
  height: 100%;
  display: block;
}

.no-video {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-muted);
  font-size: 1.2rem;
}

.progress-info {
  margin-bottom: 20px;
}

.progress-bar-container {
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #22c55e, #16a34a);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.9rem;
}

.rewatching-label {
  color: #f59e0b;
  font-weight: 600;
  margin-left: 8px;
}

.lesson-content {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
}

.lesson-content h3 {
  margin: 0 0 14px;
  font-size: 1.2rem;
}

.content-text {
  line-height: 1.8;
  color: var(--color-text);
  white-space: pre-wrap;
}

.lesson-footer {
  display: flex;
  gap: 12px;
  margin-top: 30px;
  flex-wrap: wrap;
}

.lesson-footer .btn {
  min-width: 220px;
}

.btn.primary {
  background: linear-gradient(135deg, var(--color-accent), #8b5cf6);
}

.btn.primary:hover:not(:disabled) {
  background: linear-gradient(135deg, var(--color-accent-hover), #7c3aed);
}

.no-lesson {
  text-align: center;
  padding: 60px;
  color: var(--color-text-muted);
  font-size: 1.1rem;
}

@media (max-width: 1024px) {
  .player-layout {
    grid-template-columns: 1fr;
    height: auto;
  }

  .lessons-sidebar {
    border-right: none;
    border-bottom: 1px solid var(--color-border);
    max-height: 400px;
  }

  .lesson-footer {
    flex-direction: column;
  }

  .lesson-footer .btn {
    width: 100%;
  }
}
</style>