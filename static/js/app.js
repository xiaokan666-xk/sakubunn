document.addEventListener('DOMContentLoaded', function() {
    loadEssays();
    loadSources();
    loadStats();

    document.getElementById('search-btn').addEventListener('click', function() {
        loadEssays();
    });

    document.getElementById('keyword').addEventListener('keyup', function(e) {
        if (e.key === 'Enter') {
            loadEssays();
        }
    });

    document.getElementById('source-filter').addEventListener('change', function() {
        loadEssays();
    });

    document.getElementById('crawl-btn').addEventListener('click', function() {
        startCrawl();
    });

    document.getElementById('prev-page').addEventListener('click', function() {
        currentPage--;
        loadEssays();
    });

    document.getElementById('next-page').addEventListener('click', function() {
        currentPage++;
        loadEssays();
    });

    document.querySelector('.close').addEventListener('click', function() {
        document.getElementById('essay-modal').style.display = 'none';
    });

    window.addEventListener('click', function(e) {
        const modal = document.getElementById('essay-modal');
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });

    document.getElementById('export-btn').addEventListener('click', function() {
        exportCurrentEssay();
    });
});

let currentPage = 1;
let currentEssayId = null;

function loadEssays() {
    const keyword = document.getElementById('keyword').value;
    const source = document.getElementById('source-filter').value;
    
    fetch(`/api/essays?keyword=${encodeURIComponent(keyword)}&source=${encodeURIComponent(source)}`)
        .then(response => response.json())
        .then(data => {
            renderEssayList(data);
        })
        .catch(error => {
            console.error('Error loading essays:', error);
        });
}

function loadSources() {
    fetch('/api/sources')
        .then(response => response.json())
        .then(sources => {
            const select = document.getElementById('source-filter');
            sources.forEach(source => {
                const option = document.createElement('option');
                option.value = source;
                option.textContent = source;
                select.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading sources:', error);
        });
}

function loadStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(stats => {
            document.getElementById('total-count').textContent = stats.total || 0;
        })
        .catch(error => {
            console.error('Error loading stats:', error);
        });
}

function renderEssayList(essays) {
    const tbody = document.getElementById('essay-table-body');
    
    if (essays.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty">暂无数据，请先执行抓取</td></tr>';
        return;
    }

    tbody.innerHTML = '';
    
    essays.forEach(essay => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="title-cell" onclick="showEssay(${essay.id})">${essay.title}</td>
            <td>${essay.source_name}</td>
            <td>${essay.word_count}</td>
            <td>${essay.crawl_time}</td>
            <td><button class="action-btn" onclick="exportEssay(${essay.id})">导出</button></td>
        `;
        tbody.appendChild(tr);
    });
}

function showEssay(essayId) {
    currentEssayId = essayId;
    
    fetch(`/api/essay/${essayId}`)
        .then(response => response.json())
        .then(essay => {
            document.getElementById('modal-title').textContent = essay.title;
            document.getElementById('modal-source').textContent = essay.source_name;
            document.getElementById('modal-word-count').textContent = essay.word_count;
            document.getElementById('modal-content').textContent = essay.content;
            document.getElementById('essay-modal').style.display = 'block';
        })
        .catch(error => {
            console.error('Error loading essay:', error);
        });
}

function exportEssay(essayId) {
    window.location.href = `/api/export/${essayId}`;
}

function exportCurrentEssay() {
    if (currentEssayId) {
        exportEssay(currentEssayId);
    }
}

function startCrawl() {
    const sourceName = document.getElementById('source-filter').value || '全部';
    
    fetch('/api/crawl', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ source_name: sourceName })
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
        setTimeout(() => {
            loadEssays();
            loadStats();
        }, 2000);
    })
    .catch(error => {
        console.error('Error starting crawl:', error);
        alert('抓取失败，请查看日志');
    });
}
