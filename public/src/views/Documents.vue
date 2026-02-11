<template>
  <div class="card">
    <h2>Регламенты</h2>

    <div class="row">
      <input
        v-model="searchQuery"
        @keyup.enter="searchDocuments"
        placeholder="Поиск документов..."
      />
      <button @click="searchDocuments" class="btn secondary">Найти</button>
    </div>

    <div class="list mt">
      <div
        v-for="doc in documents"
        :key="doc.id"
        class="item accent-purple"
      >
        <div class="title">{{ doc.title }}</div>
        <div class="muted">{{ doc.description || 'Без описания' }}</div>

        <div class="row" style="margin-top: 12px; gap: 8px;">
          <a
            v-if="doc.file_url"
            :href="doc.file_url"
            target="_blank"
            class="btn secondary"
            style="text-decoration: none;"
          >
            📥 Скачать
          </a>
          <a
            v-if="doc.link"
            :href="doc.link"
            target="_blank"
            class="btn secondary"
            style="text-decoration: none;"
          >
            🔗 Открыть ссылку
          </a>
        </div>
      </div>

      <div v-if="documents.length === 0 && searched" class="muted" style="text-align: center; padding: 20px;">
        Документы не найдены
      </div>

      <div v-if="!searched" class="muted" style="text-align: center; padding: 20px;">
        Введите запрос для поиска документов
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import api from '../services/api';

const searchQuery = ref('');
const documents = ref([]);
const searched = ref(false);

const searchDocuments = async () => {
  if (!searchQuery.value.trim()) {
    return;
  }

  try {
    const res = await api.getDocuments(searchQuery.value);
    documents.value = res.data;
    searched.value = true;
  } catch (err) {
    console.error('Ошибка поиска документов:', err);
    documents.value = [];
    searched.value = true;
  }
};
</script>

<style scoped>
/* Локальные стили */
</style>