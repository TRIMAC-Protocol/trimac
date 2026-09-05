/**
 * TRIMAC 旗艦門戶 - 聯絡表單模組
 * 處理表單驗證、提交與回饋
 */

(function() {
    'use strict';

    function initContactForm() {
        const form = document.getElementById('contact-form');
        if (!form) return;

        const submitBtn = form.querySelector('button[type="submit"]');
        const inputs = form.querySelectorAll('input, select, textarea');

        // 即時驗證
        inputs.forEach(input => {
            input.addEventListener('blur', () => validateField(input));
            input.addEventListener('input', () => {
                if (input.classList.contains('form-error')) {
                    validateField(input);
                }
            });
        });

        // 表單提交
        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            if (!validateForm(form)) {
                showToast('請填寫所有必填欄位', 'error');
                return;
            }

            // 禁用提交按鈕
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner spinner-sm"></span> 發送中...';

            try {
                // 模擬 API 提交
                await submitForm(form);
                showToast('訊息已發送，我們將在 2-3 個工作天內回覆', 'success');
                form.reset();
            } catch (error) {
                showToast('發送失敗，請稍後再試或直接電郵聯絡我們', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = '傳送訊息';
            }
        });

        // 為 select 添加樣式類
        form.querySelectorAll('select').forEach(select => {
            select.addEventListener('change', () => {
                if (select.value) {
                    select.classList.add('has-value');
                } else {
                    select.classList.remove('has-value');
                }
            });
        });
    }

    function validateField(field) {
        const value = field.value.trim();
        let isValid = true;
        let message = '';

        // 必填檢查
        if (field.hasAttribute('required') && !value) {
            isValid = false;
            message = '此欄位為必填';
        }

        // Email 格式檢查
        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                isValid = false;
                message = '請輸入有效的電郵地址';
            }
        }

        // 電話格式檢查（簡單）
        if (field.type === 'tel' && value) {
            const phoneRegex = /^[\d\s\-\+\(\)]{8,}$/;
            if (!phoneRegex.test(value)) {
                isValid = false;
                message = '請輸入有效的電話號碼';
            }
        }

        // 更新 UI
        field.classList.toggle('form-error', !isValid);
        
        // 移除舊錯誤訊息
        const oldError = field.parentNode.querySelector('.form-error-message');
        if (oldError) oldError.remove();

        if (!isValid) {
            const errorEl = document.createElement('div');
            errorEl.className = 'form-error-message';
            errorEl.textContent = message;
            field.parentNode.appendChild(errorEl);
        }

        return isValid;
    }

    function validateForm(form) {
        const fields = form.querySelectorAll('[required]');
        let allValid = true;
        fields.forEach(field => {
            if (!validateField(field)) {
                allValid = false;
            }
        });
        return allValid;
    }

    async function submitForm(form) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // 這裡可以對接實際 API
        // const response = await fetch('/api/contact', {
        //     method: 'POST',
        //     headers: { 'Content-Type': 'application/json' },
        //     body: JSON.stringify(data)
        // });
        
        // 模擬網路延遲
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // 記錄到 console（開發用）
        console.log('[TRIMAC] Contact form submitted:', data);
        
        // 如果有實際端點，取消註釋下方
        // if (!response.ok) throw new Error('Submit failed');
    }

    function showToast(message, type = 'info') {
        // 移除現有 toast
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = 'toast ' + type;
        toast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink: 0;">
                    ${type === 'success' ? '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>' : 
                      type === 'error' ? '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>' :
                      type === 'warning' ? '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>' :
                      '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>'}
                </svg>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // 觸發動畫
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });
        
        // 自動移除
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
        
        // 點擊關閉
        toast.addEventListener('click', () => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        });
    }

    // 初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initContactForm);
    } else {
        initContactForm();
    }

    // 導出
    window.TRIMAC.modules.contact = { init: initContactForm };
})();