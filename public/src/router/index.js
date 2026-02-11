import { createRouter, createWebHistory } from 'vue-router';
import Login from '../views/Login.vue';
import Layout from '../views/Layout.vue';
import Courses from '../views/Courses.vue';
import LessonPlayer from '../views/LessonPlayer.vue';
import Standups from '../views/Standups.vue';
import Documents from '../views/Documents.vue';
import Admin from '../views/Admin.vue';
import api from '../services/api';

const routes = [
  { path: '/login', component: Login },
  {
    path: '/',
    component: Layout,
    children: [
      { path: '', redirect: '/courses' },
      { path: 'courses', component: Courses },
      { path: 'course/:courseId/lesson/:lessonId', component: LessonPlayer }, // НОВЫЙ МАРШРУТ
      { path: 'standups', component: Standups },
      { path: 'documents', component: Documents },
      { path: 'admin', component: Admin },
    ]
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach((to, from, next) => {
  const token = api.getToken();
  if (to.path !== '/login' && !token) {
    next('/login');
  } else {
    next();
  }
});

export default router;