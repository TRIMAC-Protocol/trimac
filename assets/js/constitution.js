/**
 * TRIMAC 旗艦門戶 - 憲法章節切換模組
 */

(function() {
    'use strict';

    function initConstitutionTabs() {
        const tabs = document.querySelectorAll('.constitution-tab');
        const panels = document.querySelectorAll('.chapter-panel');
        
        if (!tabs.length || !panels.length) return;
        
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const chapter = tab.getAttribute('data-chapter');
                
                // 更新標籤狀態
                tabs.forEach(t => {
                    t.classList.remove('active');
                    t.setAttribute('aria-selected', 'false');
                });
                tab.classList.add('active');
                tab.setAttribute('aria-selected', 'true');
                
                // 更新面板顯示
                panels.forEach(panel => {
                    if (panel.getAttribute('data-chapter') === chapter) {
                        panel.classList.add('active');
                    } else {
                        panel.classList.remove('active');
                    }
                });
                
                // 平滑滾動到內容區
                const content = document.querySelector('.constitution-content');
                if (content) {
                    content.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
            
            // 鍵盤支援
            tab.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    tab.click();
                } else if (e.key === 'ArrowRight') {
                    e.preventDefault();
                    const nextTab = tab.nextElementSibling || tabs[0];
                    nextTab.focus();
                } else if (e.key === 'ArrowLeft') {
                    e.preventDefault();
                    const prevTab = tab.previousElementSibling || tabs[tabs.length - 1];
                    prevTab.focus();
                }
            });
        });
        
        // 為每個條文卡片添加進場動畫
        const articleCards = document.querySelectorAll('.article-card');
        const cardObserver = new IntersectionObserver((entries) => {
            entries.forEach((entry, index) => {
                if (entry.isIntersecting) {
                    entry.target.style.animationDelay = (index * 100) + 'ms';
                    entry.target.classList.add('animate-fade-in-up');
                    cardObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });
        
        articleCards.forEach(card => cardObserver.observe(card));
    }

    // 初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initConstitutionTabs);
    } else {
        initConstitutionTabs();
    }

    // 導出
    window.TRIMAC.modules.constitution = { init: initConstitutionTabs };
})();