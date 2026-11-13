// Build and update the page from the current application state.
import { api } from './api.js';
import { state } from './state.js';

const $ = (selector) => document.querySelector(selector);

function escapeHTML(value) {
  const characters = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  };

  return String(value ?? '').replace(/[&<>"']/g, (character) => characters[character]);
}

export function openModal(modalId) {
  $(`#${modalId}`).classList.remove('hidden');
}

export function closeModal(modalId) {
  $(`#${modalId}`).classList.add('hidden');
}

export function showView(viewName) {
  const views = ['wardrobe', 'outfits', 'collections', 'discover'];

  views.forEach((name) => {
    $(`#${name}-view`).classList.toggle('hidden', name !== viewName);
    document.querySelector(`[data-view="${name}"]`).classList.toggle('active', name === viewName);
  });

  $('#crumb').textContent = viewName.toUpperCase();
}

function renderItemImage(item) {
  if (item.image) {
    return `<img src="${escapeHTML(item.image)}" alt="${escapeHTML(item.name)}">`;
  }

  const initial = (item.name || '?').charAt(0).toUpperCase();
  return `<span class="item-placeholder">${escapeHTML(initial)}</span>`;
}

function renderItemCard(item) {
  return `
    <article class="item-card">
      <div class="item-visual">
        ${renderItemImage(item)}
        <button class="delete-item" data-delete-item="${item.id}" title="Delete item">×</button>
      </div>
      <div class="item-meta">
        <strong>${escapeHTML(item.name)}</strong>
        <small><i class="item-color"></i>${escapeHTML(item.color)} · ${escapeHTML(item.category)}</small>
      </div>
    </article>
  `;
}

function renderFilters() {
  document.querySelectorAll('.filter').forEach((button) => {
    const category = button.dataset.filter;
    button.classList.toggle('active', category === state.activeFilter);

    if (category !== 'All') {
      const count = state.wardrobe.filter((item) => item.category === category).length;
      button.innerHTML = `${escapeHTML(category)} <span>${count}</span>`;
    }
  });
}

export function renderItems() {
  const searchTerm = $('#search').value.trim().toLowerCase();
  const visibleItems = state.wardrobe.filter((item) => {
    const matchesCategory = state.activeFilter === 'All' || item.category === state.activeFilter;
    const searchableText = `${item.name} ${item.category} ${item.color}`.toLowerCase();
    return matchesCategory && searchableText.includes(searchTerm);
  });

  $('#item-grid').innerHTML = visibleItems.map(renderItemCard).join('');
  $('#empty-items').classList.toggle('hidden', visibleItems.length > 0);
  $('#item-grid').classList.toggle('hidden', visibleItems.length === 0);
  $('#all-count').textContent = state.wardrobe.length;
  renderFilters();
}

function renderOutfitItem(item) {
  if (item.image) {
    return `<img src="${escapeHTML(item.image)}" alt="${escapeHTML(item.name)}">`;
  }

  return `<span class="outfit-thumb-placeholder">${escapeHTML(item.name.charAt(0))}</span>`;
}

function renderOutfitCard(outfit) {
  const thumbnails = outfit.items.slice(0, 3).map(renderOutfitItem).join('');
  const pieceLabel = outfit.items.length === 1 ? 'piece' : 'pieces';

  return `
    <article class="outfit-card">
      <button class="delete-outfit" data-delete-outfit="${outfit.id}" title="Delete outfit">×</button>
      <div class="outfit-thumbs">${thumbnails}</div>
      <h3>${escapeHTML(outfit.name)}</h3>
      <small>${escapeHTML(outfit.occasion)} · ${outfit.items.length} ${pieceLabel}</small>
    </article>
  `;
}

export function renderOutfits() {
  $('#outfit-grid').innerHTML = state.outfits.map(renderOutfitCard).join('');
  $('#empty-outfits').classList.toggle('hidden', state.outfits.length > 0);
  $('#outfit-grid').classList.toggle('hidden', state.outfits.length === 0);
}

function renderStats(stats) {
  $('#stat-items').textContent = String(stats.items).padStart(2, '0');
  $('#stat-outfits').textContent = String(stats.outfits).padStart(2, '0');
  $('#stat-categories').textContent = String(stats.categories).padStart(2, '0');
}

export async function refresh() {
  [state.wardrobe, state.outfits] = await Promise.all([
    api('/api/items'),
    api('/api/outfits')
  ]);

  renderItems();
  renderOutfits();
  renderStats(await api('/api/stats'));
}

export function buildItemPicker() {
  const options = state.wardrobe.map((item) => `
    <label class="pick-option">
      <input type="checkbox" name="item_ids" value="${item.id}">
      <span>${escapeHTML(item.name)} <small>(${escapeHTML(item.category)})</small></span>
    </label>
  `).join('');

  $('#item-picker').innerHTML = options || '<p>Add some wardrobe items first.</p>';
}
