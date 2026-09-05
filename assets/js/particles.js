/**
 * TRIMAC 旗艦門戶 - 粒子背景模組
 * 獨立粒子系統，支援效能優化與減少動畫偏好
 */

(function() {
    'use strict';

    let canvas = null;
    let ctx = null;
    let particles = [];
    let animationId = null;
    let width = 0;
    let height = 0;
    let running = false;
    let mouse = { x: -1000, y: -1000 };

    function initParticles() {
        canvas = document.getElementById('particle-canvas');
        if (!canvas) return;

        ctx = canvas.getContext('2d');
        
        // 檢查減少動畫偏好
        const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (prefersReduced) {
            canvas.style.display = 'none';
            return;
        }

        setupCanvas();
        createParticles();
        bindEvents();
        start();
    }

    function setupCanvas() {
        const rect = canvas.getBoundingClientRect();
        width = canvas.width = rect.width;
        height = canvas.height = rect.height;
    }

    function createParticles() {
        particles = [];
        // 根據螢幕大小調整粒子數量
        const density = 0.00015;
        const count = Math.min(Math.floor(width * height * density), 100);
        
        for (let i = 0; i < count; i++) {
            particles.push({
                x: Math.random() * width,
                y: Math.random() * height,
                vx: (Math.random() - 0.5) * 0.4,
                vy: (Math.random() - 0.5) * 0.4,
                radius: Math.random() * 2 + 0.5,
                baseRadius: 0,
                opacity: Math.random() * 0.4 + 0.05,
                color: Math.random() > 0.7 ? 'gold' : 'red'
            });
        }
        
        // 設定基礎半徑
        particles.forEach(p => p.baseRadius = p.radius);
    }

    function bindEvents() {
        // 滑鼠互動
        canvas.addEventListener('mousemove', (e) => {
            const rect = canvas.getBoundingClientRect();
            mouse.x = e.clientX - rect.left;
            mouse.y = e.clientY - rect.top;
        });

        canvas.addEventListener('mouseleave', () => {
            mouse.x = -1000;
            mouse.y = -1000;
        });

        // 視窗大小變更
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                setupCanvas();
                createParticles();
            }, 250);
        });

        // 頁面可見性
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                stop();
            } else if (!running) {
                start();
            }
        });

        // 滾動時暫停（效能優化）
        let scrollTimeout;
        window.addEventListener('scroll', () => {
            if (running) {
                stop();
            }
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                if (!running && !document.hidden) {
                    start();
                }
            }, 150);
        }, { passive: true });
    }

    function animate() {
        if (!running) return;

        ctx.clearRect(0, 0, width, height);

        // 繪製連線
        drawConnections();
        
        // 繪製並更新粒子
        particles.forEach(p => updateParticle(p));
        particles.forEach(p => drawParticle(p));

        animationId = requestAnimationFrame(animate);
    }

    function drawConnections() {
        const maxDist = 140;
        const mouseInfluence = 200;

        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < maxDist) {
                    const opacity = (1 - dist / maxDist) * 0.12;
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    
                    // 滑鼠附近連線變亮
                    const mx = (particles[i].x + particles[j].x) / 2;
                    const my = (particles[i].y + particles[j].y) / 2;
                    const mDist = Math.sqrt((mx - mouse.x) ** 2 + (my - mouse.y) ** 2);
                    
                    if (mDist < mouseInfluence) {
                        ctx.strokeStyle = 'rgba(212, 168, 67, ' + (opacity * 2) + ')';
                        ctx.lineWidth = 1;
                    } else {
                        ctx.strokeStyle = 'rgba(196, 30, 58, ' + opacity + ')';
                        ctx.lineWidth = 0.5;
                    }
                    ctx.stroke();
                }
            }
        }
    }

    function updateParticle(p) {
        // 基礎移動
        p.x += p.vx;
        p.y += p.vy;

        // 邊界反彈
        if (p.x <= 0 || p.x >= width) {
            p.vx *= -1;
            p.x = Math.max(0, Math.min(width, p.x));
        }
        if (p.y <= 0 || p.y >= height) {
            p.vy *= -1;
            p.y = Math.max(0, Math.min(height, p.y));
        }

        // 滑鼠排斥/吸引效果
        const dx = mouse.x - p.x;
        const dy = mouse.y - p.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        
        if (dist < 180 && dist > 0) {
            const force = (180 - dist) / 180 * 0.5;
            const angle = Math.atan2(dy, dx);
            
            // 紅色粒子被排斥，金色粒子被吸引
            const dir = p.color === 'gold' ? 1 : -1;
            p.vx += Math.cos(angle) * force * dir * 0.02;
            p.vy += Math.sin(angle) * force * dir * 0.02;
            
            // 限制最大速度
            const speed = Math.sqrt(p.vx * p.vx + p.vy * p.vy);
            if (speed > 2) {
                p.vx = (p.vx / speed) * 2;
                p.vy = (p.vy / speed) * 2;
            }
        }

        // 慢慢回歸基礎速度
        p.vx *= 0.999;
        p.vy *= 0.999;
    }

    function drawParticle(p) {
        // 滑鼠附近放大
        const dx = mouse.x - p.x;
        const dy = mouse.y - p.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        
        let radius = p.baseRadius;
        if (dist < 150) {
            radius = p.baseRadius * (1 + (150 - dist) / 150 * 2);
        }

        ctx.beginPath();
        ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
        
        if (p.color === 'gold') {
            ctx.fillStyle = 'rgba(212, 168, 67, ' + p.opacity + ')';
            // 添加發光效果
            if (dist < 100) {
                ctx.shadowColor = 'rgba(212, 168, 67, 0.8)';
                ctx.shadowBlur = 8;
            }
        } else {
            ctx.fillStyle = 'rgba(196, 30, 58, ' + p.opacity + ')';
            if (dist < 100) {
                ctx.shadowColor = 'rgba(196, 30, 58, 0.8)';
                ctx.shadowBlur = 8;
            }
        }
        ctx.fill();
        ctx.shadowBlur = 0;
    }

    function start() {
        if (running) return;
        running = true;
        animate();
    }

    function stop() {
        running = false;
        if (animationId) {
            cancelAnimationFrame(animationId);
            animationId = null;
        }
    }

    function destroy() {
        stop();
        canvas = null;
        ctx = null;
        particles = [];
    }

    // 初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initParticles);
    } else {
        initParticles();
    }

    // 導出
    window.TRIMAC.modules.particles = {
        init: initParticles,
        start,
        stop,
        destroy,
        getCanvas: () => canvas
    };
})();