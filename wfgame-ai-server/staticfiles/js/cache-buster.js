/**
 * 缓存破坏脚本
 * 防止浏览器缓存静态资源，确保总是加载最新版本
 */

(function() {
    'use strict';

    // 生成时间戳参数
    function generateCacheBuster() {
        return new Date().getTime();
    }

    // 为所有需要刷新的资源添加缓存破坏参数
    function addCacheBusterToResources() {
        const cacheBuster = generateCacheBuster();

        // 刷新CSS文件
        const linkElements = document.querySelectorAll('link[rel="stylesheet"]');
        linkElements.forEach(function(link) {
            if (link.href && !link.href.includes('_cb=')) {
                const separator = link.href.includes('?') ? '&' : '?';
                link.href = link.href + separator + '_cb=' + cacheBuster;
            }
        });

        // 刷新JavaScript文件（除了当前脚本）
        const scriptElements = document.querySelectorAll('script[src]');
        scriptElements.forEach(function(script) {
            if (script.src &&
                !script.src.includes('cache-buster.js') &&
                !script.src.includes('_cb=')) {
                const separator = script.src.includes('?') ? '&' : '?';
                script.src = script.src + separator + '_cb=' + cacheBuster;
            }
        });
    }

    // 页面加载完成后执行
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addCacheBusterToResources);
    } else {
        addCacheBusterToResources();
    }

    // 强制刷新功能
    window.forceCacheRefresh = function() {
        location.reload(true);
    };

    // 在控制台显示缓存破坏状态
    console.log('🔄 Cache Buster: 已激活缓存破坏机制');

})();
