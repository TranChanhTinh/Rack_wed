(() => {
  const search = document.getElementById('sidebar-q');
  const suggestions = document.getElementById('search-suggestions');
  const contextMenu = document.getElementById('rack-context-menu');
  const toast = document.getElementById('save-toast');
  let toastTimer;
  let selectedCell = null;
  let moveSource = null;
  let rightDragSource = null;
  let rightDragTarget = null;
  let rightDragging = false;
  let suppressNextContextMenu = false;
  let suggestTimer = null;
  let moveMode = false;
  const selectedForColor = new Set();
  let lastRightClickedCell = null;

  function showToast(message, isError = false) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.toggle('error', isError);
    toast.classList.add('visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('visible'), 3500);
  }

  async function postJSON(url, payload) {
    const response = await fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.message || 'Thao tác thất bại.');
    return result;
  }

  async function runRackAction(payload) {
    try {
      const result = await postJSON('/rack-action', payload);
      showToast(result.message || 'Đã lưu vào rack.xlsx.');
      if (result.reload) setTimeout(() => window.location.reload(), 450);
      return true;
    } catch (error) {
      showToast(error.message || 'Không thể cập nhật Excel.', true);
      return false;
    }
  }

  // Search suggestions in the left sidebar.
  if (search && suggestions) {
    search.addEventListener('keydown', event => {
      if (event.key === 'Escape') {
        search.value = '';
        suggestions.hidden = true;
      }
      if (event.key === 'Enter') suggestions.hidden = true;
    });
    search.addEventListener('input', () => {
      clearTimeout(suggestTimer);
      const query = search.value.trim();
      suggestions.replaceChildren();
      if (!query) { suggestions.hidden = true; return; }
      suggestTimer = setTimeout(async () => {
        try {
          const response = await fetch(`/suggest?q=${encodeURIComponent(query)}`);
          const data = await response.json();
          suggestions.replaceChildren();
          data.results.forEach(item => {
            const link = document.createElement('a');
            link.className = 'search-suggestion';
            link.href = `/?q=${encodeURIComponent(item.code)}&sheet=${encodeURIComponent(item.sheet)}#rack-map`;
            const code = document.createElement('strong');
            code.textContent = item.code;
            const location = document.createElement('span');
            location.textContent = `${item.sheet} · ${item.cell}`;
            link.append(code, location);
            suggestions.appendChild(link);
          });
          const exact = document.createElement('button');
          exact.type = 'submit';
          exact.className = 'suggestion-submit';
          exact.textContent = `Tìm “${query}”`;
          suggestions.appendChild(exact);
          suggestions.hidden = false;
        } catch {
          suggestions.hidden = true;
        }
      }, 180);
    });
    document.addEventListener('click', event => {
      if (!event.target.closest('.sidebar-search')) suggestions.hidden = true;
    });
  }

  function canEditCell(cell) {
    return !!cell && cell.dataset.kind !== 'label' && cell.dataset.cell && cell.dataset.sheet;
  }

  function hideMenu() {
    if (contextMenu) contextMenu.hidden = true;
  }

  function showMenu(cell, x, y) {
    if (!contextMenu) return;
    selectedCell = cell;
    lastRightClickedCell = cell;
    if (!selectedForColor.size) {
      selectedForColor.add(cell);
      cell.classList.add('color-selected');
    } else if (!selectedForColor.has(cell)) {
      // Right-clicking a different cell starts a new selection.
      selectedForColor.forEach(item => item.classList.remove('color-selected'));
      selectedForColor.clear();
      selectedForColor.add(cell);
      cell.classList.add('color-selected');
    }
    const kind = cell.dataset.kind;
    const occupied = kind === 'box' && (cell.dataset.value || '').trim() !== '';
    contextMenu.querySelector('[data-action="add"]').hidden = occupied;
    contextMenu.querySelector('[data-action="edit"]').hidden = !occupied;
    contextMenu.querySelector('[data-action="delete"]').hidden = !occupied;
    contextMenu.querySelector('[data-action="move"]').hidden = !occupied;
    contextMenu.style.left = `${Math.max(8, Math.min(x, window.innerWidth - 230))}px`;
    contextMenu.style.top = `${Math.max(8, Math.min(y, window.innerHeight - 190))}px`;
    contextMenu.hidden = false;
  }

  // Ctrl+click toggles multiple cells for batch coloring. Plain click clears selection.
  document.addEventListener('click', event => {
    const cell = event.target.closest('.rack-cell');
    if (!cell || !canEditCell(cell)) return;
    if (event.ctrlKey || event.metaKey) {
      if (selectedForColor.has(cell)) {
        selectedForColor.delete(cell);
        cell.classList.remove('color-selected');
      } else {
        selectedForColor.add(cell);
        cell.classList.add('color-selected');
      }
    } else if (!event.target.closest('#rack-context-menu')) {
      selectedForColor.forEach(item => item.classList.remove('color-selected'));
      selectedForColor.clear();
    }
  }, true);

  async function applyCellColor(color) {
    if (!selectedCell) return;
    const cells = [...selectedForColor].filter(cell => cell.dataset.sheet === selectedCell.dataset.sheet);
    const chosen = cells.length ? cells : [selectedCell];
    const coordinates = chosen.map(cell => cell.dataset.cell);
    try {
      const response = await fetch('/color-cells', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          sheet: selectedCell.dataset.sheet,
          cells: coordinates,
          color: color === 'CLEAR' ? 'FFFFFF' : color
        })
      });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.message || 'Không tô màu được.');
      showToast(result.message || 'Đã cập nhật màu.');
      setTimeout(() => window.location.reload(), 350);
    } catch (error) {
      showToast(error.message, true);
    }
  }

  contextMenu?.addEventListener('click', event => {
    const swatch = event.target.closest('[data-color]');
    if (swatch) {
      event.preventDefault();
      event.stopPropagation();
      applyCellColor(swatch.dataset.color);
    }
  });

  const customColor = document.getElementById('custom-cell-color');
  customColor?.addEventListener('change', () => applyCellColor(customColor.value));

  document.addEventListener('contextmenu', event => {
    const cell = event.target.closest('.rack-cell');
    if (!cell || !canEditCell(cell)) return;
    event.preventDefault();
    if (suppressNextContextMenu) { suppressNextContextMenu = false; return; }
    showMenu(cell, event.clientX, event.clientY);
  });

  document.addEventListener('click', event => {
    if (!event.target.closest('#rack-context-menu')) hideMenu();
  });

  contextMenu?.addEventListener('click', async event => {
    const button = event.target.closest('[data-action]');
    if (!button || !selectedCell) return;
    const action = button.dataset.action;
    const cell = selectedCell;
    const sheet = cell.dataset.sheet;
    const coordinate = cell.dataset.cell;
    const oldValue = cell.dataset.value || '';
    hideMenu();

    if (action === 'add' || action === 'edit') {
      const value = window.prompt(action === 'add' ? `Nhập mã thùng cho ô ${coordinate}:` : `Sửa mã thùng tại ${coordinate}:`, action === 'edit' ? oldValue : '');
      if (value === null) return;
      if (!value.trim()) { showToast('Mã thùng không được để trống.', true); return; }
      try {
        if (action === 'add') await postJSON('/rack-action', {action: 'add', sheet, cell: coordinate, value: value.trim()});
        else await postJSON('/edit', {sheet, cell: coordinate, value: value.trim()});
        showToast('Đã lưu thay đổi vào rack.xlsx.');
        setTimeout(() => window.location.reload(), 400);
      } catch (error) { showToast(error.message, true); }
      return;
    }

    if (action === 'delete') {
      if (!window.confirm(`Bạn chắc chắn muốn xóa thùng “${oldValue}” tại ${coordinate}?`)) return;
      await runRackAction({action: 'delete', sheet, cell: coordinate});
      return;
    }

    if (action === 'move') {
      moveSource = cell;
      moveMode = true;
      cell.classList.add('move-source');
      showToast('Đang chọn thùng. Nhấp vào ô trống hoặc giữ chuột phải kéo đến ô trống.');
    }
  });

  async function moveBox(source, target) {
    if (!source || !target || source === target) return;
    if (source.dataset.sheet !== target.dataset.sheet) {
      showToast('Hiện chỉ hỗ trợ di chuyển trong cùng một sheet.', true); return;
    }
    if ((target.dataset.value || '').trim()) {
      showToast('Ô đích đã có dữ liệu. Hãy chọn ô trống.', true); return;
    }
    const ok = await runRackAction({action: 'move', sheet: source.dataset.sheet, cell: source.dataset.cell, target: target.dataset.cell});
    if (ok) {
      moveSource?.classList.remove('move-source');
      moveSource = null;
      moveMode = false;
    }
  }

  // Right mouse button drag. A normal right-click still opens the context menu.
  document.addEventListener('mousedown', event => {
    if (event.button !== 2) return;
    const cell = event.target.closest('.rack-cell');
    if (!cell || cell.dataset.kind !== 'box' || !(cell.dataset.value || '').trim()) return;
    rightDragSource = cell;
    rightDragTarget = cell;
    rightDragging = false;
  });

  document.addEventListener('mouseover', event => {
    if (!rightDragSource) return;
    const target = event.target.closest('.rack-cell');
    if (!target || !canEditCell(target) || target === rightDragSource) return;
    rightDragTarget = target;
    rightDragging = true;
    document.querySelectorAll('.rack-cell.drop-target').forEach(cell => cell.classList.remove('drop-target'));
    target.classList.add('drop-target');
  });

  document.addEventListener('mouseup', async event => {
    if (event.button !== 2 || !rightDragSource) return;
    const source = rightDragSource;
    const target = event.target.closest('.rack-cell') || rightDragTarget;
    const shouldMove = rightDragging && target && target !== source;
    rightDragSource = null;
    rightDragTarget = null;
    rightDragging = false;
    document.querySelectorAll('.rack-cell.drop-target').forEach(cell => cell.classList.remove('drop-target'));
    if (!shouldMove) return;
    event.preventDefault();
    suppressNextContextMenu = true;
    await moveBox(source, target);
  });

  // Click-to-place fallback for touchpads or mice that make right-drag difficult.
  document.addEventListener('click', async event => {
    if (!moveMode) return;
    const target = event.target.closest('.rack-cell');
    if (!target || !moveSource || target === moveSource) return;
    if (!canEditCell(target)) return;
    const source = moveSource;
    await moveBox(source, target);
  });
})();
