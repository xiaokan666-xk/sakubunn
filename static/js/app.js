// ========================================
// State
// ========================================
let allEssays = [];
let filteredEssays = [];
let selectedIds = new Set();
let currentPage = 1;
const pageSize = 15;
let currentModalId = null;

// ========================================
// Init
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    loadEssays();
    bindEvents();
});

function bindEvents() {
    document.getElementById('search-input').addEventListener('input', debounce(() => {
        currentPage = 1;
        applyFilters();
    }, 300));

    document.getElementById('site-filter').addEventListener('change', () => {
        currentPage = 1;
        applyFilters();
    });

    document.getElementById('sort-select').addEventListener('change', () => {
        currentPage = 1;
        applyFilters();
    });

    document.getElementById('select-all').addEventListener('change', handleSelectAll);
    document.getElementById('select-visible').addEventListener('click', selectVisible);
    document.getElementById('clear-selection').addEventListener('click', clearSelection);

    document.getElementById('prev-page').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderEssayList();
        }
    });

    document.getElementById('next-page').addEventListener('click', () => {
        const totalPages = Math.ceil(filteredEssays.length / pageSize);
        if (currentPage < totalPages) {
            currentPage++;
            renderEssayList();
        }
    });

    document.getElementById('refresh-btn').addEventListener('click', () => {
        showToast('正在刷新数据...');
        loadEssays();
    });

    document.getElementById('batch-export-btn').addEventListener('click', batchExport);

    // Modal events
    document.getElementById('modal-close').addEventListener('click', closeModal);
    document.getElementById('modal-close-btn').addEventListener('click', closeModal);
    document.getElementById('modal-export-btn').addEventListener('click', () => {
        if (currentModalId) exportSingle(currentModalId);
    });

    document.getElementById('preview-modal').addEventListener('click', (e) => {
        if (e.target.id === 'preview-modal') closeModal();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
}

// ========================================
// Data Loading
// ========================================
function loadEssays() {
    fetch('/api/essays')
        .then(r => r.json())
        .then(data => {
            allEssays = data || [];
            populateSiteFilter();
            applyFilters();
            updateStats();
            showToast(`已加载 ${allEssays.length} 篇作文`);
        })
        .catch(err => {
            console.error('Load essays failed:', err);
            showToast('加载失败，请重试');
        });
}

function populateSiteFilter() {
    const sites = [...new Set(allEssays.map(e => e.site).filter(Boolean))];
    const select = document.getElementById('site-filter');
    select.innerHTML = '<option value="">全部网站</option>';
    sites.forEach(site => {
        const opt = document.createElement('option');
        opt.value = site;
        opt.textContent = site;
        select.appendChild(opt);
    });
}

function updateStats() {
    document.getElementById('total-count').textContent = allEssays.length;
    const sites = new Set(allEssays.map(e => e.site));
    document.getElementById('site-count').textContent = sites.size;

    const times = allEssays.map(e => e.crawl_time).filter(Boolean);
    if (times.length > 0) {
        const latest = times.sort().pop();
        document.getElementById('last-update').textContent = `最后更新：${formatDate(latest)}`;
    }
}

// ========================================
// Filtering & Sorting
// ========================================
function applyFilters() {
    const keyword = document.getElementById('search-input').value.trim().toLowerCase();
    const site = document.getElementById('site-filter').value;
    const sort = document.getElementById('sort-select').value;

    filteredEssays = allEssays.filter(essay => {
        if (site && essay.site !== site) return false;
        if (keyword) {
            const text = `${essay.title} ${essay.author} ${essay.body}`.toLowerCase();
            return text.includes(keyword);
        }
        return true;
    });

    filteredEssays.sort((a, b) => {
        switch (sort) {
            case 'time_desc': return compareDate(b.crawl_time, a.crawl_time);
            case 'time_asc': return compareDate(a.crawl_time, b.crawl_time);
            case 'title_asc': return (a.title || '').localeCompare(b.title || '');
            case 'title_desc': return (b.title || '').localeCompare(a.title || '');
            default: return 0;
        }
    });

    currentPage = 1;
    renderEssayList();
}

function compareDate(a, b) {
    if (!a) return 1;
    if (!b) return -1;
    return new Date(b) - new Date(a);
}

// ========================================
// Rendering
// ========================================
function renderEssayList() {
    const container = document.getElementById('essay-list');
    const total = filteredEssays.length;

    if (total === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#d6756b" stroke-width="1.5">
                        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                        <line x1="16" y1="13" x2="8" y2="13"/>
                        <line x1="16" y1="17" x2="8" y2="17"/>
                    </svg>
                </div>
                <p class="empty-title">没有找到匹配的作文</p>
                <p class="empty-desc">请尝试调整搜索条件</p>
            </div>`;
        document.getElementById('pagination-bar').style.display = 'none';
        return;
    }

    const totalPages = Math.ceil(total / pageSize);
    const start = (currentPage - 1) * pageSize;
    const end = Math.min(start + pageSize, total);
    const pageItems = filteredEssays.slice(start, end);

    container.innerHTML = pageItems.map(essay => createEssayItem(essay)).join('');

    document.getElementById('pagination-bar').style.display = 'flex';
    document.getElementById('page-start').textContent = start + 1;
    document.getElementById('page-end').textContent = end;
    document.getElementById('page-total').textContent = total;

    document.getElementById('prev-page').disabled = currentPage <= 1;
    document.getElementById('next-page').disabled = currentPage >= totalPages;

    renderPageNumbers(totalPages);
    updateSelectAllState();
    bindItemEvents();
}

function createEssayItem(essay) {
    const isSelected = selectedIds.has(essay.id);
    return `
        <div class="essay-item ${isSelected ? 'selected' : ''}" data-id="${essay.id}">
            <div class="essay-checkbox">
                <label class="checkbox-wrap">
                    <input type="checkbox" class="item-checkbox" data-id="${essay.id}" ${isSelected ? 'checked' : ''}>
                    <span class="checkmark"></span>
                </label>
            </div>
            <div class="essay-content">
                <div class="essay-title">${escapeHtml(essay.title || '无标题')}</div>
                <div class="essay-meta-row">
                    <span class="essay-meta-item">
                        <span class="site-badge">${escapeHtml(essay.site || '未知')}</span>
                    </span>
                    <span class="essay-meta-item">
                        <span class="label">作者</span>
                        <span class="value">${escapeHtml(essay.author || '未知')}</span>
                    </span>
                    <span class="essay-meta-item">
                        <span class="label">更新</span>
                        <span class="value">${formatDate(essay.crawl_time)}</span>
                    </span>
                </div>
            </div>
            <div class="essay-actions">
                <button class="btn-icon" title="预览" onclick="event.stopPropagation(); previewEssay(${essay.id})">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                </button>
                <button class="btn-icon" title="导出" onclick="event.stopPropagation(); exportSingle(${essay.id})">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
                </button>
            </div>
        </div>
    `;
}

function renderPageNumbers(totalPages) {
    const container = document.getElementById('page-numbers');
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let pages = [];
    const maxVisible = 5;

    if (totalPages <= maxVisible + 2) {
        for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
        pages.push(1);
        let startPage = Math.max(2, currentPage - 1);
        let endPage = Math.min(totalPages - 1, currentPage + 1);

        if (currentPage <= 3) {
            endPage = Math.min(totalPages - 1, maxVisible);
        } else if (currentPage >= totalPages - 2) {
            startPage = Math.max(2, totalPages - maxVisible + 1);
        }

        if (startPage > 2) pages.push('...');
        for (let i = startPage; i <= endPage; i++) pages.push(i);
        if (endPage < totalPages - 1) pages.push('...');
        pages.push(totalPages);
    }

    container.innerHTML = pages.map(p => {
        if (p === '...') return `<span class="page-number" style="cursor:default">...</span>`;
        return `<button class="page-number ${p === currentPage ? 'active' : ''}" data-page="${p}">${p}</button>`;
    }).join('');

    container.querySelectorAll('[data-page]').forEach(btn => {
        btn.addEventListener('click', () => {
            currentPage = parseInt(btn.dataset.page);
            renderEssayList();
        });
    });
}

// ========================================
// Selection
// ========================================
function bindItemEvents() {
    document.querySelectorAll('.essay-item').forEach(item => {
        const id = parseInt(item.dataset.id);

        item.addEventListener('click', (e) => {
            if (e.target.closest('.checkbox-wrap') || e.target.closest('.btn-icon')) return;
            previewEssay(id);
        });
    });

    document.querySelectorAll('.item-checkbox').forEach(cb => {
        cb.addEventListener('change', (e) => {
            const id = parseInt(e.target.dataset.id);
            if (e.target.checked) {
                selectedIds.add(id);
            } else {
                selectedIds.delete(id);
            }
            updateSelectionUI();
        });
    });
}

function handleSelectAll(e) {
    const checked = e.target.checked;
    const pageItems = getCurrentPageItems();

    pageItems.forEach(essay => {
        if (checked) {
            selectedIds.add(essay.id);
        } else {
            selectedIds.delete(essay.id);
        }
    });

    renderEssayList();
    updateSelectionUI();
}

function selectVisible() {
    const pageItems = getCurrentPageItems();
    pageItems.forEach(essay => selectedIds.add(essay.id));
    renderEssayList();
    updateSelectionUI();
}

function clearSelection() {
    selectedIds.clear();
    renderEssayList();
    updateSelectionUI();
}

function getCurrentPageItems() {
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return filteredEssays.slice(start, end);
}

function updateSelectionUI() {
    const count = selectedIds.size;
    document.getElementById('selected-count').textContent = count;
    document.getElementById('batch-export-btn').disabled = count === 0;
}

function updateSelectAllState() {
    const pageItems = getCurrentPageItems();
    const allSelected = pageItems.length > 0 && pageItems.every(e => selectedIds.has(e.id));
    document.getElementById('select-all').checked = allSelected;
}

// ========================================
// Preview Modal
// ========================================
function previewEssay(id) {
    const essay = allEssays.find(e => e.id === id);
    if (!essay) return;

    currentModalId = id;
    document.getElementById('modal-title').textContent = essay.title || '无标题';
    document.getElementById('modal-site').textContent = essay.site || '未知';
    document.getElementById('modal-author').textContent = essay.author || '未知';
    document.getElementById('modal-date').textContent = formatDate(essay.crawl_time);
    document.getElementById('modal-source').textContent = essay.source || '';
    document.getElementById('modal-source').href = essay.source || '#';
    document.getElementById('modal-body').textContent = essay.body || '';

    document.getElementById('preview-modal').classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    document.getElementById('preview-modal').classList.remove('active');
    document.body.style.overflow = '';
    currentModalId = null;
}

// ========================================
// Export
// ========================================
function exportSingle(id) {
    window.location.href = `/api/export/${id}`;
    showToast('正在导出...');
}

function batchExport() {
    if (selectedIds.size === 0) {
        showToast('请先选择要导出的作文');
        return;
    }

    if (selectedIds.size === 1) {
        exportSingle([...selectedIds][0]);
        return;
    }

    const ids = [...selectedIds].join(',');
    window.location.href = `/api/export_batch?ids=${ids}`;
    showToast(`正在导出 ${selectedIds.size} 篇作文...`);
}

// ========================================
// Utilities
// ========================================
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return '--';
    const d = new Date(dateStr);
    if (isNaN(d)) return dateStr;
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

function debounce(fn, delay) {
    let timer;
    return function(...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2500);
}
