// Wire user interactions to the page and API.
import { api, showToast } from './api.js';
import { state } from './state.js';
import {
  buildItemPicker,
  closeModal,
  openModal,
  refresh,
  renderItems,
  showView
} from './render.js';

const $ = (selector) => document.querySelector(selector);

async function handleDeleteItem(button) {
  if (!confirm('Delete this wardrobe item?')) return;

  try {
    await api(`/api/items/${button.dataset.deleteItem}`, { method: 'DELETE' });
    await refresh();
    showToast('Item removed from wardrobe.');
  } catch (error) {
    showToast(error.message);
  }
}

async function handleDeleteOutfit(button) {
  if (!confirm('Delete this saved outfit?')) return;

  try {
    await api(`/api/outfits/${button.dataset.deleteOutfit}`, { method: 'DELETE' });
    await refresh();
    showToast('Outfit deleted.');
  } catch (error) {
    showToast(error.message);
  }
}

function handleDocumentClick(event) {
  const target = event.target;
  const navButton = target.closest('[data-view]');
  const shortcutButton = target.closest('[data-go]');
  const closeButton = target.closest('[data-close]');
  const filterButton = target.closest('[data-filter]');
  const deleteItemButton = target.closest('[data-delete-item]');
  const deleteOutfitButton = target.closest('[data-delete-outfit]');

  if (navButton) showView(navButton.dataset.view);
  if (shortcutButton) showView(shortcutButton.dataset.go);
  if (closeButton) closeModal(closeButton.dataset.close);

  if (filterButton) {
    state.activeFilter = filterButton.dataset.filter;
    renderItems();
  }

  if (deleteItemButton) handleDeleteItem(deleteItemButton);
  if (deleteOutfitButton) handleDeleteOutfit(deleteOutfitButton);
}

function handleEscapeKey(event) {
  if (event.key !== 'Escape') return;

  document.querySelectorAll('.modal-backdrop').forEach((modal) => {
    modal.classList.add('hidden');
  });
}

function handleItemSubmit(event) {
  event.preventDefault();

  const form = event.currentTarget;
  const message = $('#item-message');
  message.textContent = '';

  api('/api/items', {
    method: 'POST',
    body: new FormData(form)
  }).then(async () => {
    form.reset();
    closeModal('item-modal');
    await refresh();
    showToast('Added to your wardrobe.');
  }).catch((error) => {
    message.textContent = error.message;
  });
}

function handleOutfitSubmit(event) {
  event.preventDefault();

  const form = event.currentTarget;
  const message = $('#outfit-message');
  const formData = new FormData(form);
  message.textContent = '';

  api('/api/outfits', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: formData.get('name'),
      occasion: formData.get('occasion'),
      item_ids: formData.getAll('item_ids')
    })
  }).then(async () => {
    form.reset();
    closeModal('outfit-modal');
    await refresh();
    showToast('Outfit saved.');
  }).catch((error) => {
    message.textContent = error.message;
  });
}

function openOutfitModal() {
  buildItemPicker();
  openModal('outfit-modal');
}

export function initializeEvents() {
  document.addEventListener('click', handleDocumentClick);
  document.addEventListener('keydown', handleEscapeKey);

  $('#open-add').addEventListener('click', () => openModal('item-modal'));
  $('#empty-add').addEventListener('click', () => openModal('item-modal'));
  $('#hero-outfits').addEventListener('click', () => showView('outfits'));
  $('#search').addEventListener('input', renderItems);
  $('#open-outfit').addEventListener('click', openOutfitModal);
  $('#empty-outfit').addEventListener('click', openOutfitModal);
  $('#item-form').addEventListener('submit', handleItemSubmit);
  $('#outfit-form').addEventListener('submit', handleOutfitSubmit);
}
