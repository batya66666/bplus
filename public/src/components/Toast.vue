<template>
  <Transition name="toast">
    <div
      v-if="visible"
      :class="['toast', type]"
    >
      {{ message }}
    </div>
  </Transition>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
  message: {
    type: String,
    default: ''
  },
  type: {
    type: String,
    default: 'info',
    validator: (value) => ['success', 'error', 'info'].includes(value)
  },
  duration: {
    type: Number,
    default: 3000
  }
});

const visible = ref(false);
let timeout = null;

watch(() => props.message, (newVal) => {
  if (newVal) {
    visible.value = true;

    if (timeout) clearTimeout(timeout);

    timeout = setTimeout(() => {
      visible.value = false;
    }, props.duration);
  }
});
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.toast-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
</style>