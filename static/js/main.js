// Application entry point.
import { showToast } from './api.js';
import { initializeEvents } from './events.js';
import { refresh } from './render.js';

initializeEvents();
refresh().catch((error) => showToast(error.message));
