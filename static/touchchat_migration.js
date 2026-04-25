let touchchatSessionId = null;
let touchchatData = null;
let selectedSourceBoardId = null;
let selectedButtonIndices = new Set();
let availableDestinationBoards = [];
let pendingMissingTargets = [];
let isImportInProgress = false;
let selectedSourceAacApp = null;

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

function hideMigrationResultModal() {
  const modal = document.getElementById('migrationResultModal');
  const msg = document.getElementById('migrationResultMessage');
  const title = document.getElementById('migrationResultTitle');
  if (modal) modal.classList.remove('show');
  if (msg) msg.textContent = '';
  if (title) title.textContent = 'Migration Complete';
}

function showMigrationResultModal(title, message, options = {}) {
  const modal = document.getElementById('migrationResultModal');
  const msg = document.getElementById('migrationResultMessage');
  const titleEl = document.getElementById('migrationResultTitle');
  if (titleEl) titleEl.textContent = String(title || 'Migration Complete');
  if (msg) {
    if (options.html) {
      msg.innerHTML = options.html;
    } else {
      msg.textContent = String(message || '');
    }
  }
  if (modal) modal.classList.add('show');
}

function showImportProcessingOverlay(message = 'Please wait while TouchChat boards and buttons are being imported.') {
  const overlay = document.getElementById('importProcessingOverlay');
  const msg = document.getElementById('importProcessingMessage');
  if (msg) msg.textContent = String(message || 'Import in progress...');
  if (overlay) {
    overlay.classList.remove('hidden');
    overlay.classList.add('flex');
  }
}

function hideImportProcessingOverlay() {
  const overlay = document.getElementById('importProcessingOverlay');
  if (overlay) {
    overlay.classList.remove('flex');
    overlay.classList.add('hidden');
  }
}

function prepareForAnotherBoardImport() {
  hideMigrationResultModal();
  selectedButtonIndices.clear();
  updateSelectedButtonCount();
  document.getElementById('buttonList').innerHTML = '';
  document.getElementById('sourceBoardSelect').value = '';
  selectedSourceBoardId = null;
  updateExecuteSourceBoardContext();
  resetNavResolutionUI();
  showTab('boards');
  setStatus('Select another source board to continue migration.');
}

function getSelectedSourceBoard() {
  if (!selectedSourceBoardId || !touchchatData || !touchchatData.boards) return null;
  return touchchatData.boards[selectedSourceBoardId] || null;
}

function updateExecuteSourceBoardContext() {
  const sourceNameEl = document.getElementById('executeSourceBoardName');
  const sourceBoard = getSelectedSourceBoard();
  if (sourceNameEl) {
    sourceNameEl.textContent = sourceBoard ? String(sourceBoard.name || sourceBoard.page_id || 'Unknown board') : 'Not selected';
  }
}

function normalizeBoardNameForMatch(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ');
}

function findExistingDestinationBoardByName(boardName) {
  const target = normalizeBoardNameForMatch(boardName);
  if (!target) return null;
  return availableDestinationBoards.find((board) =>
    normalizeBoardNameForMatch(board.label || board.id) === target
  ) || null;
}

function findSourceBoardPageIdByName(boardName) {
  const target = normalizeBoardNameForMatch(boardName);
  if (!target || !touchchatData || !touchchatData.boards) return null;
  const sourceBoards = Object.values(touchchatData.boards);
  const match = sourceBoards.find((board) =>
    normalizeBoardNameForMatch(board.name || board.page_id) === target
  );
  return match ? String(match.page_id || '') : null;
}

function selectSourceBoardByName(boardName) {
  const sourceSelect = document.getElementById('sourceBoardSelect');
  if (!sourceSelect || !touchchatData || !touchchatData.boards) {
    setStatus('Upload a TouchChat file first, then select a board from the list.');
    return false;
  }

  const sourceBoardId = findSourceBoardPageIdByName(boardName);
  if (!sourceBoardId) {
    setStatus(`No source board named "${boardName}" was found in the uploaded TouchChat file.`);
    return false;
  }

  sourceSelect.value = sourceBoardId;
  sourceSelect.dispatchEvent(new Event('change'));
  return true;
}

function applySourceBoardNameToDestination() {
  const sourceBoard = getSelectedSourceBoard();
  if (!sourceBoard) {
    setStatus('Choose a source board first.');
    return;
  }
  const name = String(sourceBoard.name || '').trim();
  if (!name) {
    setStatus('Selected source board has no name to copy.');
    return;
  }
  const destinationInput = document.getElementById('newDestinationName');
  if (destinationInput) {
    destinationInput.value = name;
  }
  setStatus(`Destination board name filled with source board name: ${name}`);
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
  setupSourceAacSelectionHandlers();
  setupTabButtons();
  setupUploadHandlers();
  setupBoardAndButtonHandlers();
  setupExecuteHandlers();
  setupUnconfiguredBoardsReportHandlers();
  loadAvailableDestinationBoards();
  hideMigrationResultModal();
}

function setupSourceAacSelectionHandlers() {
  const continueBtn = document.getElementById('continueSourceAacBtn');
  const sourceSelect = document.getElementById('sourceAacAppSelect');
  if (!continueBtn || !sourceSelect) {
    return;
  }

  continueBtn.addEventListener('click', () => {
    const selected = String(sourceSelect.value || '').trim();
    if (!selected) {
      setStatus('Select a source AAC application to continue.');
      return;
    }

    if (selected !== 'touchchat') {
      setStatus('That migration source is not available yet. Please select TouchChat for now.');
      return;
    }

    selectedSourceAacApp = selected;
    enableTab('upload');
    showTab('upload');
    setStatus('Ready to upload a TouchChat .ce file.');
  });
}

function setupUnconfiguredBoardsReportHandlers() {
  const refreshBtn = document.getElementById('refreshUnconfiguredBoardsBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      loadAvailableDestinationBoards();
    });
  }
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
  if (selectedSourceAacApp !== 'touchchat') {
    setStatus('Select TouchChat in the Source step before uploading a file.');
    return;
  }

  const name = (file.name || '').toLowerCase();
  if (!(name.endsWith('.ce') || name.endsWith('.ce.zip') || name.endsWith('.zip'))) {
    setStatus('Please upload a TouchChat .ce file.');
    return;
  }

  resetNavResolutionUI();
  hideMigrationResultModal();
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
    updateExecuteSourceBoardContext();
    selectedButtonIndices.clear();
    resetNavResolutionUI();
    hideMigrationResultModal();

    if (!selectedSourceBoardId || !touchchatData || !touchchatData.boards || !touchchatData.boards[selectedSourceBoardId]) {
      document.getElementById('buttonList').innerHTML = '';
      document.getElementById('boardMeta').textContent = '';
      return;
    }

    const board = touchchatData.boards[selectedSourceBoardId];
    const fullCascadeEnabled = !!document.getElementById('importFullCascade')?.checked;
    const matchedDestination = findExistingDestinationBoardByName(board.name || board.page_id || '');
    if (matchedDestination) {
      selectExistingDestinationBoard(matchedDestination.id, matchedDestination.label || matchedDestination.id);
    }
    if (fullCascadeEnabled) {
      selectedButtonIndices = new Set(board.buttons.map((btn) => Number(btn.index)));
    }
    document.getElementById('boardMeta').textContent = `Grid ${board.layout_cols}x${board.layout_rows}`;
    renderButtonList(board);
    updateSelectedButtonCount();
    enableTab('buttons');
    enableTab('execute');
    showTab('buttons');
    if (matchedDestination) {
      setStatus(`Select buttons you want to import. Destination is preselected to existing board "${matchedDestination.label || matchedDestination.id}".`);
    } else {
      setStatus('Select buttons you want to import.');
    }
  });

  document.getElementById('importFullCascade').addEventListener('change', () => {
    const fullCascadeEnabled = !!document.getElementById('importFullCascade')?.checked;
    if (!selectedSourceBoardId || !touchchatData || !touchchatData.boards || !touchchatData.boards[selectedSourceBoardId]) {
      return;
    }
    const board = touchchatData.boards[selectedSourceBoardId];
    if (fullCascadeEnabled) {
      selectedButtonIndices = new Set(board.buttons.map((btn) => Number(btn.index)));
      renderButtonList(board);
      updateSelectedButtonCount();
      setStatus('Full cascade import enabled. This will import this board and all linked boards recursively.');
    }
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
    renderUnconfiguredBoardsReport();
  } catch (error) {
    console.error(error);
    setStatus(`Failed to load destination boards: ${error.message}`);
    renderUnconfiguredBoardsReport(error);
  }
}

function selectExistingDestinationBoard(boardId, boardLabel) {
  const existingRadio = document.querySelector('input[name="destinationType"][value="existing"]');
  const newWrap = document.getElementById('newDestinationWrap');
  const existingWrap = document.getElementById('existingDestinationWrap');
  const existingSelect = document.getElementById('existingDestinationBoard');

  if (existingRadio) existingRadio.checked = true;
  if (newWrap) newWrap.classList.add('hidden');
  if (existingWrap) existingWrap.classList.remove('hidden');
  if (existingSelect) existingSelect.value = String(boardId || '');
}

function renderUnconfiguredBoardsReport(loadError = null) {
  const summaryEl = document.getElementById('unconfiguredBoardsSummary');
  const listEl = document.getElementById('unconfiguredBoardsList');
  if (!summaryEl || !listEl) return;

  if (loadError) {
    summaryEl.textContent = `Unable to load report: ${loadError.message || loadError}`;
    listEl.innerHTML = '';
    return;
  }

  const unconfiguredBoards = availableDestinationBoards
    .filter((board) => Array.isArray(board.buttons) && board.buttons.length === 0)
    .sort((a, b) => String(a.label || '').localeCompare(String(b.label || '')));

  summaryEl.textContent = `${unconfiguredBoards.length} board${unconfiguredBoards.length === 1 ? '' : 's'} currently have no buttons defined.`;
  listEl.innerHTML = '';

  if (!unconfiguredBoards.length) {
    const li = document.createElement('li');
    li.textContent = 'None. All editable boards currently have at least one button.';
    listEl.appendChild(li);
    return;
  }

  unconfiguredBoards.forEach((board) => {
    const li = document.createElement('li');
    const boardName = String(board.label || board.id || 'Untitled board');
    const hint = board.created_during_migration ? ' (created during migration)' : '';
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'text-left text-blue-700 hover:text-blue-900 hover:underline';
    button.textContent = `${boardName}${hint}`;
    button.addEventListener('click', () => {
      const sourceFound = selectSourceBoardByName(boardName);
      selectExistingDestinationBoard(board.id, boardName);
      if (sourceFound) {
        setStatus(`Selected source board "${boardName}" and mapped destination to existing board "${boardName}".`);
      } else {
        setStatus(`Selected destination board "${boardName}". Choose a source board in Boards step and select buttons.`);
      }
    });
    li.appendChild(button);
    listEl.appendChild(li);
  });
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
      hideMigrationResultModal();
    });
  });

  document.getElementById('useSourceBoardNameBtn').addEventListener('click', applySourceBoardNameToDestination);

  document.getElementById('executeImportBtn').addEventListener('click', executeTouchChatImport);
  document.getElementById('resetMigrationBtn').addEventListener('click', resetTouchChatMigration);
  document.getElementById('modalMigrateAnotherBoardBtn').addEventListener('click', () => {
    prepareForAnotherBoardImport();
  });
  document.getElementById('modalMigrationDoneBtn').addEventListener('click', () => {
    hideMigrationResultModal();
    setStatus('Migration complete. You can close this window or migrate another board.');
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({ type: 'touchchat-migration-finished' }, '*');
    }
  });
}

function showDestinationConflictModal({ requestedName, existingBoardLabel, importFullCascade }) {
  const modal = document.getElementById('destinationConflictModal');
  const requestedEl = document.getElementById('conflictRequestedName');
  const existingEl = document.getElementById('conflictExistingBoardLabel');
  const cascadeHint = document.getElementById('conflictCascadeHint');
  const renameWrap = document.getElementById('conflictRenameWrap');
  const renameInput = document.getElementById('conflictNewNameInput');

  const cancelBtn = document.getElementById('conflictCancelBtn');
  const useExistingBtn = document.getElementById('conflictUseExistingBtn');
  const replaceBtn = document.getElementById('conflictReplaceExistingBtn');
  const useDifferentBtn = document.getElementById('conflictUseDifferentNameBtn');
  const confirmDifferentBtn = document.getElementById('conflictConfirmDifferentNameBtn');

  requestedEl.textContent = String(requestedName || '');
  existingEl.textContent = String(existingBoardLabel || existingBoardLabel || 'existing board');
  cascadeHint.classList.toggle('hidden', !importFullCascade);
  renameWrap.classList.add('hidden');
  useDifferentBtn.classList.remove('hidden');
  confirmDifferentBtn.classList.add('hidden');
  renameInput.value = '';

  modal.classList.add('show');

  return new Promise((resolve) => {
    const cleanup = () => {
      cancelBtn.removeEventListener('click', onCancel);
      useExistingBtn.removeEventListener('click', onUseExisting);
      replaceBtn.removeEventListener('click', onReplaceExisting);
      useDifferentBtn.removeEventListener('click', onUseDifferent);
      confirmDifferentBtn.removeEventListener('click', onConfirmDifferent);
      modal.classList.remove('show');
    };

    const onCancel = () => {
      cleanup();
      resolve({ action: 'cancel' });
    };

    const onUseExisting = () => {
      cleanup();
      resolve({ action: 'use_existing' });
    };

    const onReplaceExisting = () => {
      cleanup();
      resolve({ action: 'replace_existing' });
    };

    const onUseDifferent = () => {
      renameWrap.classList.remove('hidden');
      useDifferentBtn.classList.add('hidden');
      confirmDifferentBtn.classList.remove('hidden');
      renameInput.focus();
    };

    const onConfirmDifferent = () => {
      const newName = String(renameInput.value || '').trim();
      if (!newName) {
        setStatus('Enter a new board name to continue.');
        renameInput.focus();
        return;
      }
      cleanup();
      resolve({ action: 'different_name', new_name: newName });
    };

    cancelBtn.addEventListener('click', onCancel);
    useExistingBtn.addEventListener('click', onUseExisting);
    replaceBtn.addEventListener('click', onReplaceExisting);
    useDifferentBtn.addEventListener('click', onUseDifferent);
    confirmDifferentBtn.addEventListener('click', onConfirmDifferent);
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

  const importFullCascade = !!document.getElementById('importFullCascade')?.checked;

  if (!touchchatSessionId || !selectedSourceBoardId) {
    setStatus('Upload a file and choose a source board first.');
    return;
  }
  if (!importFullCascade && !selectedButtonIndices.size) {
    setStatus('Select at least one button to import.');
    return;
  }

  const destinationType = document.querySelector('input[name="destinationType"]:checked').value;
  let newDestinationName = document.getElementById('newDestinationName').value.trim();
  const existingDestinationBoard = document.getElementById('existingDestinationBoard').value;

  if (destinationType === 'new' && !newDestinationName) {
    setStatus('Enter a new destination board name.');
    return;
  }
  if (destinationType === 'existing' && !existingDestinationBoard) {
    setStatus('Select an existing destination board.');
    return;
  }

  let effectiveDestinationType = destinationType;
  let effectiveDestinationBoardId = destinationType === 'existing' ? existingDestinationBoard : null;
  let effectiveDestinationBoardName = destinationType === 'new' ? newDestinationName : null;
  let effectiveMergeMode = document.getElementById('mergeMode').value;
  let cascadeRootBoardRename = null;

  if (effectiveDestinationType === 'new') {
    while (true) {
      const matchedDestination = findExistingDestinationBoardByName(effectiveDestinationBoardName);
      if (!matchedDestination) {
        break;
      }

      const resolution = await showDestinationConflictModal({
        requestedName: effectiveDestinationBoardName,
        existingBoardLabel: matchedDestination.label || matchedDestination.id,
        importFullCascade,
      });

      if (!resolution || resolution.action === 'cancel') {
        setStatus('Import cancelled. Resolve destination board naming to continue.');
        return;
      }

      if (resolution.action === 'use_existing') {
        effectiveDestinationType = 'existing';
        effectiveDestinationBoardId = String(matchedDestination.id);
        effectiveDestinationBoardName = null;
        selectExistingDestinationBoard(matchedDestination.id, matchedDestination.label || matchedDestination.id);
        break;
      }

      if (resolution.action === 'replace_existing') {
        effectiveDestinationType = 'existing';
        effectiveDestinationBoardId = String(matchedDestination.id);
        effectiveDestinationBoardName = null;
        effectiveMergeMode = 'replace';
        selectExistingDestinationBoard(matchedDestination.id, matchedDestination.label || matchedDestination.id);
        const mergeModeSelect = document.getElementById('mergeMode');
        if (mergeModeSelect) {
          mergeModeSelect.value = 'replace';
        }
        break;
      }

      if (resolution.action === 'different_name') {
        const previousName = String(effectiveDestinationBoardName || '').trim();
        effectiveDestinationBoardName = String(resolution.new_name || '').trim();
        const newNameInput = document.getElementById('newDestinationName');
        if (newNameInput) {
          newNameInput.value = effectiveDestinationBoardName;
        }
        if (!effectiveDestinationBoardName) {
          setStatus('Enter a valid destination board name.');
          return;
        }
        if (importFullCascade && previousName && effectiveDestinationBoardName && previousName !== effectiveDestinationBoardName) {
          cascadeRootBoardRename = {
            old_name: previousName,
            new_name: effectiveDestinationBoardName,
          };
        }
        continue;
      }
    }
  }

  const payload = {
    session_id: touchchatSessionId,
    source_board_id: selectedSourceBoardId,
    selected_button_indices: Array.from(selectedButtonIndices).sort((a, b) => a - b),
    destination_type: effectiveDestinationType,
    destination_board_id: effectiveDestinationType === 'existing' ? effectiveDestinationBoardId : null,
    destination_board_name: effectiveDestinationType === 'new' ? effectiveDestinationBoardName : null,
    merge_mode: effectiveMergeMode,
    navigation_resolutions: buildNavigationResolutionsFromUI(),
    import_full_cascade: importFullCascade,
    cascade_root_board_rename: cascadeRootBoardRename,
  };

  const executeBtn = document.getElementById('executeImportBtn');
  isImportInProgress = true;
  executeBtn.disabled = true;
  setStatus('Importing board...');
  showImportProcessingOverlay(importFullCascade
    ? 'Importing selected board and all cascading linked boards. This may take a minute...'
    : 'Importing selected TouchChat buttons...');

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
    const createdNavBoards = result.created_navigation_boards || [];
    const importedBoards = result.imported_boards || [];
    let resultHtml = `<p class="mb-2">${escapeHtml(`Migration complete: ${result.buttons_imported} buttons imported to ${result.target_board_label}.`)}</p>`;
    if (importedBoards.length > 1) {
      resultHtml += `<p class="text-sm text-slate-700 mb-2">Imported across ${importedBoards.length} boards in full cascade mode.</p>`;
    }
    if (createdNavBoards.length > 0) {
      resultHtml += `<div class="mt-3 p-3 bg-amber-50 border border-amber-200 rounded">`;
      resultHtml += `<p class="text-sm font-semibold text-amber-800 mb-1"><i class="fas fa-exclamation-triangle mr-1"></i>${createdNavBoards.length} navigation board${createdNavBoards.length > 1 ? 's were' : ' was'} created but still need${createdNavBoards.length === 1 ? 's' : ''} buttons configured:</p>`;
      resultHtml += `<ul class="text-sm text-amber-900 list-disc ml-5 space-y-0.5">`;
      createdNavBoards.forEach(b => {
        resultHtml += `<li>${escapeHtml(b.label)}</li>`;
      });
      resultHtml += `</ul>`;
      resultHtml += `<p class="text-xs text-amber-700 mt-2">Open the <strong>Board Builder</strong> and click <strong>"Show Migration Boards"</strong> to find and configure these boards.</p>`;
      resultHtml += `</div>`;
    }
    showMigrationResultModal('Migration Complete', '', { html: resultHtml });
    setStatus('Migration complete. Choose an option below.');
  } catch (error) {
    console.error(error);
    const failMsg = `Import failed: ${error.message}`;
    setStatus(failMsg);
    showMigrationResultModal('Migration Failed', failMsg);
  } finally {
    isImportInProgress = false;
    executeBtn.disabled = false;
    hideImportProcessingOverlay();
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
  selectedSourceAacApp = null;
  selectedSourceBoardId = null;
  updateExecuteSourceBoardContext();
  selectedButtonIndices.clear();
  resetNavResolutionUI();
  hideMigrationResultModal();

  document.getElementById('ceFileInput').value = '';
  document.getElementById('uploadSummary').classList.add('hidden');
  document.getElementById('uploadSummary').innerHTML = '';
  document.getElementById('sourceBoardSelect').innerHTML = '<option value="">-- Select source board --</option>';
  document.getElementById('buttonList').innerHTML = '';
  document.getElementById('selectedButtonCount').textContent = '0';
  const sourceAacSelect = document.getElementById('sourceAacAppSelect');
  if (sourceAacSelect) {
    sourceAacSelect.value = '';
  }

  document.querySelectorAll('.tab-button').forEach((btn) => {
    const tab = btn.getAttribute('data-tab');
    btn.disabled = !(tab === 'source');
  });
  showTab('source');
  setStatus('Select a source AAC application to begin migration.');
}
