// HTTP requests and user feedback shared by the app modules.
export async function api(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || 'Something went wrong.');
  }

  return data;
}

export function showToast(message) {
  const toastElement = document.querySelector('#toast');
  toastElement.textContent = message;
  toastElement.classList.add('show');

  clearTimeout(showToast.timeoutId);
  showToast.timeoutId = setTimeout(() => {
    toastElement.classList.remove('show');
  }, 2300);
}
