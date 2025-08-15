/**
 * 渲染分页组件 js 函数
 * @param container 分页条插入的 DOM 元素（如一个 <div> 或 <nav>），用于承载分页组件
 * @param currentPage 当前页码（数字），比如 1、2、3
 * @param totalPages 总页数（数字），比如 10、20
 * @param onPageClick 点击页码时的回调函数，参数为新页码（如 function(page) {...}），用于加载对应页的数据
 */

function renderPagination(container, currentPage, totalPages, onPageClick) {
    container.innerHTML = '';
    if (totalPages <= 1) return;

    const ul = document.createElement('ul');
    ul.className = 'pagination justify-content-center';

    // 上一页
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    prevLi.innerHTML = `<a class="page-link" href="#" data-page="${currentPage - 1}">上一页</a>`;
    ul.appendChild(prevLi);

    // 页码区间逻辑
    let start = Math.max(1, currentPage - 2);
    let end = Math.min(totalPages, currentPage + 2);

    if (start > 1) {
        // 首页
        const firstLi = document.createElement('li');
        firstLi.className = 'page-item';
        firstLi.innerHTML = `<a class="page-link" href="#" data-page="1">1</a>`;
        ul.appendChild(firstLi);
        if (start > 2) {
            const ellipsisLi = document.createElement('li');
            ellipsisLi.className = 'page-item disabled';
            ellipsisLi.innerHTML = `<span class="page-link">...</span>`;
            ul.appendChild(ellipsisLi);
        }
    }

    for (let i = start; i <= end; i++) {
        const li = document.createElement('li');
        li.className = `page-item ${i === currentPage ? 'active' : ''}`;
        li.innerHTML = `<a class="page-link" href="#" data-page="${i}">${i}</a>`;
        ul.appendChild(li);
    }

    if (end < totalPages) {
        if (end < totalPages - 1) {
            const ellipsisLi = document.createElement('li');
            ellipsisLi.className = 'page-item disabled';
            ellipsisLi.innerHTML = `<span class="page-link">...</span>`;
            ul.appendChild(ellipsisLi);
        }
        // 尾页
        const lastLi = document.createElement('li');
        lastLi.className = 'page-item';
        lastLi.innerHTML = `<a class="page-link" href="#" data-page="${totalPages}">${totalPages}</a>`;
        ul.appendChild(lastLi);
    }

    // 下一页
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
    nextLi.innerHTML = `<a class="page-link" href="#" data-page="${currentPage + 1}">下一页</a>`;
    ul.appendChild(nextLi);

    container.appendChild(ul);

    // 事件绑定
    ul.querySelectorAll('.page-link').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const page = parseInt(this.getAttribute('data-page'));
            if (!isNaN(page) && page >= 1 && page <= totalPages && page !== currentPage) {
                onPageClick(page);
            }
        });
    });
}