import { ref } from 'vue';

const toast = ref({
  visible: false,
  message: '',
  type: 'info'
});

let timeout = null;

export function useToast() {
  const showToast = (message, type = 'info', duration = 3000) => {
    if (timeout) {
      clearTimeout(timeout);
    }

    toast.value = {
      visible: true,
      message,
      type
    };

    timeout = setTimeout(() => {
      toast.value.visible = false;
    }, duration);
  };

  return {
    toast,
    showToast
  };
}