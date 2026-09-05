/**
 * TRIMAC 旗艦門戶 - 主入口腳本
 * 初始化所有模組、綁定全域事件
 */

(function() {
    'use strict';

    // 全域狀態
    window.TRIMAC = {
        version: '5.0.0',
        initialized: false,
        modules: {}
    };

    // DOM 就緒初始化
    function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', bootstrap);
        } else {
            bootstrap();
        }
    }

    function bootstrap() {
        // 初始化導航
        initNavigation();
        
        // 初始化滾動進度條
        initScrollProgress();
        
        // 初始化 Intersection Observer 動畫
        initRevealAnimations();
        
        // 初始化數字計數動畫
        initCounterAnimations();
        
        // 初始化英雄區粒子
        initParticles();
        
        // 標記初始化完成
        TRIMAC.initialized = true;
        document.body.classList.add('initialized');
        
        console.log('[TRIMAC] 旗艦門戶已啟動 v' + TRIMAC.version);
    }

    // 導航功能
    function initNavigation() {
        const navbar = document.querySelector('.navbar');
        const navToggle = document.querySelector('.nav-toggle');
        const navMenu = document.querySelector('.nav-menu');
        const navLinks = document.querySelectorAll('.nav-link');
        
        // 滾動時導航欄效果
        let lastScroll = 0;
        window.addEventListener('scroll', () => {
            const currentScroll = window.pageYOffset;
            if (currentScroll > 100) {
                navbar.style.background = 'rgba(10, 10, 11, 0.98)';
                navbar.style.boxShadow = 'var(--shadow-md)';
            } else {
                navbar.style.background = 'rgba(10, 10, 11, 0.9)';
                navbar.style.boxShadow = 'none';
            }
            lastScroll = currentScroll;
        }, { passive: true });
        
        // 漢堡選單切換
        if (navToggle && navMenu) {
            navToggle.addEventListener('click', () => {
                const expanded = navToggle.getAttribute('aria-expanded') === 'true';
                navToggle.setAttribute('aria-expanded', !expanded);
                navMenu.classList.toggle('active');
                document.body.style.overflow = expanded ? '' : 'hidden';
            });
            
            // 點擊連結關閉選單
            navLinks.forEach(link => {
                link.addEventListener('click', () => {
                    navToggle.setAttribute('aria-expanded', 'false');
                    navMenu.classList.remove('active');
                    document.body.style.overflow = '';
                });
            });
        }
        
        // 平滑滾動
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                const targetId = this.getAttribute('href');
                if (targetId === '#') return;
                const target = document.querySelector(targetId);
                if (target) {
                    e.preventDefault();
                    const offset = 72; // navbar height
                    const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - offset;
                    window.scrollTo({ top: targetPosition, behavior: 'smooth' });
                }
            });
        });
        
        // 滾動時高亮當前區段
        const sections = document.querySelectorAll('section[id]');
        const observerOptions = {
            rootMargin: '-72px 0px -60% 0px',
            threshold: 0
        };
        
        const sectionObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const id = entry.target.getAttribute('id');
                    navLinks.forEach(link => {
                        link.classList.toggle('active', link.getAttribute('href') === '#' + id);
                    });
                }
            });
        }, observerOptions);
        
        sections.forEach(section => sectionObserver.observe(section));
    }

    // 滾動進度條
    function initScrollProgress() {
        const progressBar = document.createElement('div');
        progressBar.className = 'scroll-progress';
        document.body.appendChild(progressBar);
        
        window.addEventListener('scroll', () => {
            const scrollTop = window.pageYOffset;
            const docHeight = document.documentElement.scrollHeight - window.innerHeight;
            const progress = scrollTop / docHeight;
            progressBar.style.transform = 'scaleX(' + progress + ')';
        }, { passive: true });
    }

    // Intersection Observer 動畫
    function initRevealAnimations() {
        const revealElements = document.querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-scale');
        
        const revealObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('active');
                    revealObserver.unobserve(entry.target);
                }
            });
        }, {
            rootMargin: '0px 0px -50px 0px',
            threshold: 0.1
        });
        
        revealElements.forEach(el => revealObserver.observe(el));
    }

    // 數字計數動畫
    function initCounterAnimations() {
        const counters = document.querySelectorAll('[data-count]');
        
        const counterObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    counterObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        
        counters.forEach(counter => counterObserver.observe(counter));
    }
    
    function animateCounter(element) {
        const target = parseInt(element.getAttribute('data-count'), 10);
        const duration = 2000;
        const startTime = performance.now();
        const startValue = 0;
        
        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = easeOutQuart(progress);
            const current = Math.floor(startValue + (target - startValue) * eased);
            element.textContent = current.toLocaleString();
            
            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                element.textContent = target.toLocaleString();
            }
        }
        
        requestAnimationFrame(update);
    }
    
    function easeOutQuart(t) {
        return 1 - Math.pow(1 - t, 4);
    }

    // 粒子背景
    function initParticles() {
        const canvas = document.getElementById('particle-canvas');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        let particles = [];
        let animationId = null;
        let width = 0, height = 0;
        
        function resize() {
            width = canvas.width = canvas.offsetWidth;
            height = canvas.height = canvas.offsetHeight;
        }
        
        function createParticles() {
            particles = [];
            const count = Math.min(Math.floor((width * height) / 15000), 80);
            for (let i = 0; i < count; i++) {
                particles.push({
                    x: Math.random() * width,
                    y: Math.random() * height,
                    vx: (Math.random() - 0.5) * 0.3,
                    vy: (Math.random() - 0.5) * 0.3,
                    radius: Math.random() * 1.5 + 0.5,
                    opacity: Math.random() * 0.5 + 0.1
                });
            }
        }
        
        function animate() {
            ctx.clearRect(0, 0, width, height);
            
            // 繪製連線
            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const dx = particles[i].x - particles[j].x;
                    const dy = particles[i].y - particles[j].y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    
                    if (dist < 120) {
                        const opacity = (1 - dist / 120) * 0.1;
                        ctx.beginPath();
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                        ctx.strokeStyle = 'rgba(196, 30, 58, ' + opacity + ')';
                        ctx.lineWidth = 0.5;
                        ctx.stroke();
                    }
                }
            }
            
            // 繪製粒子
            particles.forEach(p => {
                p.x += p.vx;
                p.y += p.vy;
                
                if (p.x < 0 || p.x > width) p.vx *= -1;
                if (p.y < 0 || p.y > height) p.vy *= -1;
                
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(196, 30, 58, ' + p.opacity + ')';
                ctx.fill();
            });
            
            animationId = requestAnimationFrame(animate);
        }
        
        function start() {
            resize();
            createParticles();
            animate();
            window.addEventListener('resize', () => {
                resize();
                createParticles();
            });
        }
        
        function stop() {
            if (animationId) {
                cancelAnimationFrame(animationId);
                animationId = null;
            }
        }
        
        // 檢查是否支援 prefers-reduced-motion
        const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (!prefersReduced) {
            start();
        }
        
        // 導出控制函數
        TRIMAC.modules.particles = { start, stop };
    }

    // 工具函數
    window.TRIMAC.utils = {
        debounce: function(fn, delay) {
            let timeoutId;
            return function(...args) {
                clearTimeout(timeoutId);
                timeoutId = setTimeout(() => fn.apply(this, args), delay);
            };
        },
        throttle: function(fn, limit) {
            let inThrottle;
            return function(...args) {
                if (!inThrottle) {
                    fn.apply(this, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            };
        },
        formatNumber: function(num) {
            return num.toLocaleString();
        },
        getColor: function(name) {
            return getComputedStyle(document.documentElement).getPropertyValue('--color-' + name).trim();
        }
    };

    // 公開 API
    window.TRIMAC.init = init;
    window.TRIMAC.bootstrap = bootstrap;

    // 自動啟動
    init();

})();