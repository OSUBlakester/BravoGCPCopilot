let touchchatSessionId = null;
let touchchatData = null;
let selectedSourceBoardId = null;
let selectedButtonIndices = new Set();
let availableDestinationBoards = [];
let pendingMissingTargets = [];
let isImportInProgress = false;

function setStatus(message) {
  const el = document.getElementById('statusBar');
  if (el) el.textContent = message;
}

function showTab(tabName) {
  document.querySelectorAll('.tab-content').forEach((el) => el.classList.remove('active'));
  document.querySelectorAll('.tab-button').forEach((el) => el.classList.remove('active'));
  const tab = document.querySelector(`.tab-content[data-tab="${tabName}"]`);
  const button = document.querySelector(`.tab-button[data-tab="${tabName}"]`);
  if (tab) tab.classList.add('active');
  if (button) button.classList.add('active');
}

function enableTab(tabName) {
  const btn = document.querySelector(`.tab-button[data-tab="${tabName}"]`);
  if (btn) btn.disabled = false;
}

function resetNavResolutionUI() {
  pendingMissingTargets = [];
  const section = document.getElementById('navResolutionSection');
  const list = document.getElementById('navResolutionList');
  if (section) section.classList.add('hidden');
  if (list) list.innerHTML = '';
}

function hideImportResultPanel() {
  const panel = document.getElementById('importResultPanel');
  const msg = document.getElementById('importResultMessage');
  if (panel) panel.classList.add('hidden');
  if (msg) msg.textContent = '';
}

function showImportResultPanel(message) {
  const panel = document.getElementById('importResultPanel');
  const msg = document.getElementById('importResultMessage');
  if (msg) msg.textContent = message;
  if (panel) panel.classList.remove('hidden');
}

function escapeHtml(v) {
  return String(v || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

document.addEventListener('migrationAuthReady', initializeTouchChatMigration);

function initializeTouchChatMigration() {
  setupTabButtons();
  setupUploadHandlers();
  setupBoardAndButtonHandlers();
  setupExecuteHandlers();
  loadAvailableDestinationBoards();
  hideImportResultPanel();
}

function setupTabButtons() {
  document.querySelectorAll('.tab-button').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (!btn.disabled) {
        showTab(btn.getAttribute('data-tab'));
      }
    });
  });
}

function setupUploadHandlers() {
  const uploadZone = document.getElementById('uploadZone');
  const fileInput = document.getElementById('ceFileInput');

  uploadZone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => {
    const file = e.target.files && e.target.files[0];
    if (file) handleTouchChatFile(file);
  });

  uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
  });
  uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) handleTouchChatFile(file);
  });
}

async function handleTouchChatFile(file) {
  const name = (file.name || '').toLowerCase();
  if (!(name.endsWith('.ce') || name.endsWith('.ce.zip') || name.endsWith('.zip'))) {
    setStatus('Please upload a TouchChat .ce file.');
    return;
  }

  resetNavResolutionUI();
  hideImportResultPanel();
  setStatus('Uploading and analyzing TouchChat export...');

  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await authenticatedFetch('/api/touchchat-migration/upload-ce', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }

    const payload = await response.json();
    touchchatSessionId = payload.session_id;

    const dataResponse = await authenticatedFetch(`/api/touchchat-migration/boards/${touchchatSessionId}`);
    if (!dataResponse.ok) {
      const err = await dataResponse.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${dataResponse.status}`);
    }

    touchchatData = await dataResponse.json();
    populateSourceBoards();

    const summary = payload.summary || {};
    const summaryEl = document.getElementById('uploadSummary');
    summaryEl.classList.remove('hidden');
    summaryEl.innerHTML = `
      <div><strong>File:</strong> ${escapeHtml(summary.file || file.name)}</div>
      <div><strong>Boards:</strong> ${Number(summary.total_boards || 0)}</div>
      <div><strong>Buttons:</strong> ${Number(summary.total_buttons || 0)}</div>
    `;

    enableTab('boards');
    showTab('boards');
    setStatus('TouchChat file analyzed. Select a source board to continue.');
  } catch (error) {
    console.error(error);
    setStatus(`Upload failed: ${error.message}`);
  }
}

function populateSourceBoards() {
  const select = document.getElementById('sourceBoardSelect');
  select.innerHTML = '<option value="">-- Select source board --</option>';

  const boards = touchchatData && touchchatData.boards ? Object.values(touchchatData.boards) : [];
  boards
    .sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')))
    .forEach((board) => {
      const opt = document.createElement('option');
      opt.value = String(board.page_id);
      opt.textContent = `${board.name} (${board.button_count} buttons)`;
      select.appendChild(opt);
    });
}

function setupBoardAndButtonHandlers() {
  document.getElementById('sourceBoardSelect').addEventListener('change', (e) => {
    const value = String(e.target.value || '');
    selectedSourceBoardId = value || null;
    selectedButtonIndices.clear();
    resetNavResolutionUI();
    hideImportResultPanel();

    if (!selectedSourceBoardId || !touchchatData || !touchchatData.boards || !touchchatData.boards[selectedSourceBoardId]) {
      document.getElementById('buttonList').innerHTML = '';
      document.getElementById('boardMeta').textContent = '';
      return;
    }

    const board = touchchatData.boards[selectedSourceBoardId];
    document.getElementById('boardMeta').textContent = `Grid ${board.layout_cols}x${board.layout_rows}`;
    renderButtonList(board);
    updateSelectedButtonCount();
    enableTab('buttons');
    enableTab('execute');
    showTab('buttons');
    setStatus('Select buttons you want to import.');
  });

  document.getElementById('selectAllButtonsBtn').addEventListener('click', () => {
    if (!selectedSourceBoardId || !touchchatData || !touchchatData.boards || !touchchatData.boards[selectedSourceBoardId]) return;
    const board = touchchatData.boards[selectedSourceBoardId];
    selectedButtonIndices = new Set(board.buttons.map((btn) => Number(btn.index)));
    renderButtonList(board);
    updateSelectedButtonCount();
  });

  document.getElementById('clearAllButtonsBtn').addEventListener('click', () => {
    selectedButtonIndices.clear();
    if (selectedSourceBoardId && touchchatData && touchchatData.boards && touchchatData.boards[selectedSourceBoardId]) {
      renderButtonList(touchchatData.boards[selectedSourceBoardId]);
    }
    updateSelectedButtonCount();
  });
}

function renderButtonList(board) {
  const list = document.getElementById('buttonList');
  list.innerHTML = '';
  board.buttons.forEach((btn) => {
    const row = document.createElement('div');
    row.className = 'button-item border rounded p-2';
    if (selectedButtonIndices.has(Number(btn.index))) row.classList.add('selected');

    const checked = selectedButtonIndices.has(Number(btn.index)) ? 'checked' : '';
    const navText = btn.navigation_target_page_name
      ? `<div class="text-xs text-amber-700 mt-1"><i class="fas fa-arrow-right mr-1"></i>Navigate: ${escapeHtml(btn.navigation_target_page_name)}</div>`
      : '';

    row.innerHTML = `
      <label class="flex items-start gap-2 cursor-pointer">
        <input type="checkbox" class="mt-1" data-index="${btn.index}" ${checked}>
        <div class="flex-1">
          <div class="text-sm font-medium text-slate-800">[${btn.row},${btn.col}] ${escapeHtml(btn.label || '')}</div>
          <div class="text-xs text-slate-500">Speech: ${escapeHtml(btn.speech_text || btn.label || '')}</div>
          ${navText}
        </div>
      </label>
    `;

    const checkbox = row.querySelector('input[type="checkbox"]');
    checkbox.addEventListener('change', () => {
      const idx = Number(checkbox.getAttribute('data-index'));
      if (checkbox.checked) selectedButtonIndices.add(idx);
      else selectedButtonIndices.delete(idx);
      if (checkbox.checked) row.classList.add('selected');
      else row.classList.remove('selected');
      updateSelectedButtonCount();
      resetNavResolutionUI();
    });

    list.appendChild(row);
  });
}

function updateSelectedButtonCount() {
  document.getElementById('selectedButtonCount').textContent = String(selectedButtonIndices.size);
}

async function loadAvailableDestinationBoards() {
  try {
    const response = await authenticatedFetch('/api/tap-interface/boards');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    const boards = Array.isArray(payload.boards) ? payload.boards : [];
    availableDestinationBoards = boards.filter((b) => {
      const source = String(b.source || '').toLowerCase();
      const type = String(b.board_type || '').toLowerCase();
      return !(source === 'legacy_category' || type === 'system');
    });
    populateExistingDestinationBoards();
  } catch (error) {
    console.error(error);
    setStatus(`Failed to load destination boards: ${error.message}`);
  }
}

function populateExistingDestinationBoards() {
  const select = document.getElementById('existingDestinationBoard');
  select.innerHTML = '<option value="">-- Select existing board --</option>';
  availableDestinationBoards
    .sort((a, b) => String(a.label || '').localeCompare(String(b.label || '')))
    .forEach((board) => {
      const opt = document.createElement('option');
      opt.value = String(board.id);
      opt.textContent = String(board.label || board.id);
      select.appendChild(opt);
    });
}

function setupExecuteHandlers() {
  document.querySelectorAll('input[name="destinationType"]').forEach((radio) => {
    radio.addEventListener('change', () => {
      const type = document.querySelector('input[name="destinationType"]:checked').value;
      document.getElementById('newDestinationWrap').classList.toggle('hidden', type !== 'new');
      document.getElementById('existingDestinationWrap').classList.toggle('hidden', type !== 'existing');
      resetNavResolutionUI();
      hideImportResultPanel();
    });
  });

  document.getElementById('executeImportBtn').addEventListener('click', executeTouchChatImport);
  document.getElementById('resetMigrationBtn').addEventListener('click', resetTouchChatMigration);
  document.getElementById('migrateAnotherBoardBtn').addEventListener('click', () => {
    hideImportResultPanel();
    selectedButtonIndices.clear();
    updateSelectedButtonCount();
    document.getElementById('buttonList').innerHTML = '';
    document.getElementById('sourceBoardSelect').value = '';
    selectedSourceBoardId = null;
    resetNavResolutionUI();
    showTab('boards');
    setStatus('Select another source board to continue migration.');
  });
  document.getElementById('migrationDoneBtn').addEventListener('click', () => {
    hideImportResultPanel();
    setStatus('Migration complete. You can close this window or migrate another board.');
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({ type: 'touchchat-migration-finished' }, '*');
    }
  });
}

function buildNavigationResolutionsFromUI() {
  const resolutions = {};
  pendingMissingTargets.forEach((target) => {
    const rid = target.target_page_rid;
    const modeEl = document.getElementById(`nav_mode_${rid}`);
    if (!modeEl) return;
    const mode = modeEl.value;
    if (mode === 'create') {
      const nameEl = document.getElementById(`nav_name_${rid}`);
      resolutions[rid] = {
        action: 'create',
        board_name: (nameEl && nameEl.value.trim()) || target.target_page_name,
      };
    } else if (mode === 'existing') {
      const boardEl = document.getElementById(`nav_existing_${rid}`);
      resolutions[rid] = {
        action: 'existing',
        board_id: boardEl ? boardEl.value : '',
      };
    }
  });
  return resolutions;
}

function renderNavigationResolutionUI(targets, availableBoardsFromApi = null) {
  pendingMissingTargets = Array.isArray(targets) ? targets : [];
  const section = document.getElementById('navResolutionSection');
  const list = document.getElementById('navResolutionList');
  if (!pendingMissingTargets.length) {
    section.classList.add('hidden');
    list.innerHTML = '';
    return;
  }

  const boardOptionsRaw = Array.isArray(availableBoardsFromApi) && availableBoardsFromApi.length
    ? availableBoardsFromApi
    : availableDestinationBoards.map((b) => ({ id: b.id, label: b.label || b.id }));
  const boardOptions = [...boardOptionsRaw].sort((a, b) =>
    String(a.label || a.id || '').localeCompare(String(b.label || b.id || ''))
  );

  section.classList.remove('hidden');
  list.innerHTML = '';

  pendingMissingTargets.forEach((target) => {
    const rid = target.target_page_rid;
    const wrapper = document.createElement('div');
    wrapper.className = 'border rounded p-2 bg-white';

    const optionsHtml = boardOptions
      .map((b) => `<option value="${escapeHtml(b.id)}">${escapeHtml(b.label)}</option>`)
      .join('');

    wrapper.innerHTML = `
      <div class="text-sm font-medium text-slate-800">${escapeHtml(target.target_page_name || target.target_page_rid)}</div>
      <div class="text-xs text-slate-500 mb-2">Used by button: ${escapeHtml(target.button_label || '')}</div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-2">
        <select id="nav_mode_${rid}" class="border rounded px-2 py-1 text-sm">
          <option value="create">Create new board</option>
          <option value="existing">Map to existing board</option>
        </select>
        <input id="nav_name_${rid}" class="border rounded px-2 py-1 text-sm" value="${escapeHtml(target.target_page_name || 'New Board')}" placeholder="New board name">
        <select id="nav_existing_${rid}" class="border rounded px-2 py-1 text-sm hidden">${optionsHtml}</select>
      </div>
    `;

    const modeEl = wrapper.querySelector(`#nav_mode_${CSS.escape(rid)}`);
    const nameEl = wrapper.querySelector(`#nav_name_${CSS.escape(rid)}`);
    const existingEl = wrapper.querySelector(`#nav_existing_${CSS.escape(rid)}`);

    modeEl.addEventListener('change', () => {
      const mode = modeEl.value;
      nameEl.classList.toggle('hidden', mode !== 'create');
      existingEl.classList.toggle('hidden', mode !== 'existing');
    });

    list.appendChild(wrapper);
  });
}

async function executeTouchChatImport() {
  if (isImportInProgress) {
    return;
  }

  if (!touchchatSessionId || !selectedSourceBoardId) {
    setStatus('Upload a file and choose a source board first.');
    return;
  }
  if (!selectedButtonIndices.size) {
    setStatus('Select at least one button to import.');
    return;
  }

  const destinationType = document.querySelector('input[name="destinationType"]:checked').value;
  const newDestinationName = document.getElementById('newDestinationName').value.trim();
  const existingDestinationBoard = document.getElementById('existingDestinationBoard').value;

  if (destinationType === 'new' && !newDestinationName) {
    setStatus('Enter a new destination board name.');
    return;
  }
  if (destinationType === 'existing' && !existingDestinationBoard) {
    setStatus('Select an existing destination board.');
    return;
  }

  const payload = {
    session_id: touchchatSessionId,
    source_board_id: selectedSourceBoardId,
    selected_button_indices: Array.from(selectedButtonIndices).sort((a, b) => a - b),
    destination_type: destinationType,
    destination_board_id: destinationType === 'existing' ? existingDestinationBoard : null,
    destination_board_name: destinationType === 'new' ? newDestinationName : null,
    merge_mode: document.getElementById('mergeMode').value,
    navigation_resolutions: buildNavigationResolutionsFromUI(),
  };

  const executeBtn = document.getElementById('executeImportBtn');
  isImportInProgress = true;
  executeBtn.disabled = true;
  setStatus('Importing board...');

  try {
    const response = await authenticatedFetch('/api/touchchat-migration/import-board', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }

    const result = await response.json();

    if (result.requires_confirmation) {
      renderNavigationResolutionUI(result.missing_navigation_targets || [], result.available_destination_boards || []);
      setStatus('Resolve missing navigation targets below, then execute migration again.');
      return;
    }

    resetNavResolutionUI();
    await loadAvailableDestinationBoards();
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({ type: 'touchchat-migration-complete' }, '*');
    }
    const resultMsg = `Migration complete: ${result.buttons_imported} buttons imported to ${result.target_board_label}.`;
    showImportResultPanel(resultMsg);
    setStatus('Migration complete. Choose an option below.');
  } catch (error) {
    console.error(error);
    setStatus(`Import failed: ${error.message}`);
  } finally {
    isImportInProgress = false;
    executeBtn.disabled = false;
  }
}

async function resetTouchChatMigration() {
  if (touchchatSessionId) {
    try {
      await authenticatedFetch(`/api/touchchat-migration/session/${touchchatSessionId}`, { method: 'DELETE' });
    } catch (error) {
      console.warn('Could not delete TouchChat migration session', error);
    }
  }

  touchchatSessionId = null;
  touchchatData = null;
  selectedSourceBoardId = null;
  selectedButtonIndices.clear();
  resetNavResolutionUI();
  hideImportResultPanel();

  document.getElementById('ceFileInput').value = '';
  document.getElementById('uploadSummary').classList.add('hidden');
  document.getElementById('uploadSummary').innerHTML = '';
  document.getElementById('sourceBoardSelect').innerHTML = '<option value="">-- Select source board --</option>';
  document.getElementById('buttonList').innerHTML = '';
  document.getElementById('selectedButtonCount').textContent = '0';

  document.querySelectorAll('.tab-button').forEach((btn) => {
    const tab = btn.getAttribute('data-tab');
    btn.disabled = !(tab === 'upload');
  });
  showTab('upload');
  setStatus('Ready to upload a TouchChat .ce file.');
}
