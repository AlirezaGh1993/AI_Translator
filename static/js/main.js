// static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const form = document.getElementById('translation-form');
    const submitBtn = form.querySelector('.submit-btn');
    
    const geminiKeyInput = document.getElementById('gemini-key');
    const deepseekKeyInput = document.getElementById('deepseek-key');
    const proxyInput = document.getElementById('proxy');
    const aiProviderSelect = document.getElementById('ai-provider');
    
    const progressArea = document.getElementById('progress-area');
    const progressBar = document.getElementById('progress-bar');
    const progressStatus = document.getElementById('progress-status');
    const downloadLink = document.getElementById('download-link');

    // --- State Management (LocalStorage) ---
    const loadSettings = () => {
        geminiKeyInput.value = localStorage.getItem('geminiApiKey') || '';
        deepseekKeyInput.value = localStorage.getItem('deepseekApiKey') || '';
        proxyInput.value = localStorage.getItem('proxyUrl') || '';
        aiProviderSelect.value = localStorage.getItem('aiProvider') || 'gemini';
    };

    const saveSettings = () => {
        localStorage.setItem('geminiApiKey', geminiKeyInput.value);
        localStorage.setItem('deepseekApiKey', deepseekKeyInput.value);
        localStorage.setItem('proxyUrl', proxyInput.value);
        localStorage.setItem('aiProvider', aiProviderSelect.value);
    };

    // --- Event Listeners ---
    [geminiKeyInput, deepseekKeyInput, proxyInput, aiProviderSelect].forEach(el => {
        el.addEventListener('change', saveSettings);
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const activeTab = document.querySelector('.tab-content.active');
        const fileInput = activeTab.querySelector('input[type="file"]');
        const file = fileInput.files[0];

        if (!file) {
            alert('لطفاً یک فایل را برای ترجمه انتخاب کنید.');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('gemini_key', geminiKeyInput.value);
        formData.append('deepseek_key', deepseekKeyInput.value);
        formData.append('proxy_url', proxyInput.value);
        formData.append('ai_provider', document.getElementById('ai-provider').value);
        formData.append('style', document.getElementById('translation-style').value);
        formData.append('target_lang', document.getElementById('target-lang').value);
        formData.append('file_type', activeTab.id === 'docs' ? 'document' : 'subtitle');

        // Reset UI
        submitBtn.disabled = true;
        submitBtn.textContent = 'در حال ترجمه...';
        progressArea.classList.remove('hidden');
        progressBar.style.width = '0%';
        progressStatus.textContent = 'در حال ارسال فایل...';
        downloadLink.classList.add('hidden');

        try {
            const response = await fetch('/translate', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'خطا در شروع فرآیند ترجمه.');
            }

            const data = await response.json();
            const taskId = data.task_id;
            listenForProgress(taskId);

        } catch (error) {
            progressStatus.textContent = `خطا: ${error.message}`;
            submitBtn.disabled = false;
            submitBtn.textContent = 'شروع ترجمه';
        }
    });

    // --- Server-Sent Events (SSE) for Progress ---
    const listenForProgress = (taskId) => {
        const eventSource = new EventSource(`/progress/${taskId}`);

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            progressBar.style.width = `${data.progress}%`;
            progressStatus.textContent = data.message;

            if (data.status === 'completed') {
                eventSource.close();
                submitBtn.disabled = false;
                submitBtn.textContent = 'شروع ترجمه';
                progressStatus.textContent = 'ترجمه با موفقیت انجام شد!';
                downloadLink.href = data.download_url;
                downloadLink.classList.remove('hidden');
            } else if (data.status === 'error') {
                eventSource.close();
                submitBtn.disabled = false;
                submitBtn.textContent = 'شروع ترجمه';
                progressStatus.textContent = `خطا در ترجمه: ${data.message}`;
            }
        };

        eventSource.onerror = () => {
            progressStatus.textContent = 'ارتباط با سرور قطع شد. لطفاً دوباره تلاش کنید.';
            submitBtn.disabled = false;
            submitBtn.textContent = 'شروع ترجمه';
            eventSource.close();
        };
    };

    // --- Initialize ---
    loadSettings();
});

// --- Tab Switcher Logic ---
function openTab(evt, tabName) {
    const tabContents = document.getElementsByClassName('tab-content');
    for (let i = 0; i < tabContents.length; i++) {
        tabContents[i].classList.remove('active');
    }

    const tabLinks = document.getElementsByClassName('tab-link');
    for (let i = 0; i < tabLinks.length; i++) {
        tabLinks[i].classList.remove('active');
    }

    document.getElementById(tabName).classList.add('active');
    evt.currentTarget.classList.add('active');

    // Also update the form's file input name based on the active tab
    const fileInputs = document.querySelectorAll('.tab-content input[type="file"]');
    fileInputs.forEach(input => input.name = ''); // Clear name from all
    document.querySelector(`#${tabName} input[type="file"]`).name = 'file'; // Set name on active one
}
