/**
 * GameAI Console - 前端交互逻辑
 */

// ============================
// API 提供方配置
// ============================
const API_PROVIDERS = {
    custom: {
        name: '自定义',
        baseUrl: '',
        description: '手动输入 API URL'
    },
    deepseek: {
        name: 'DeepSeek',
        baseUrl: 'https://api.deepseek.com/v1',
        description: 'DeepSeek AI'
    },
    mimo: {
        name: 'Mimo (小米)',
        baseUrl: 'https://api.mimo.ai/v1',
        description: '小米大模型'
    },
    siliconflow: {
        name: '硅基流动',
        baseUrl: 'https://api.siliconflow.cn/v1',
        description: 'SiliconFlow 云服务'
    },
    openai: {
        name: 'OpenAI',
        baseUrl: 'https://api.openai.com/v1',
        description: 'OpenAI GPT 系列'
    },
    zhipu: {
        name: '智谱AI',
        baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
        description: '智谱 GLM 系列'
    },
    moonshot: {
        name: '月之暗面',
        baseUrl: 'https://api.moonshot.cn/v1',
        description: 'Kimi 大模型'
    },
    baichuan: {
        name: '百川智能',
        baseUrl: 'https://api.baichuan-ai.com/v1',
        description: '百川大模型'
    },
    qwen: {
        name: '通义千问',
        baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        description: '阿里云通义千问'
    },
    gvmz: {
        name: 'GVMZ',
        baseUrl: 'https://gvmz.systems/v1',
        description: 'GVMZ 服务'
    }
};

// ============================
// 全局状态
// ============================
const state = {
    config: {
        provider: 'gvmz',
        baseUrl: 'https://gvmz.systems/v1',
        apiKey: '',
        model: ''
    },
    history: [],
    experiences: [],
    requestCount: 0,
    isLoading: false,
    availableModels: [],
    goalRunning: false,
    goalAborted: false,
    currentGoal: '',
    stepHistory: [],
    abortController: null,  // 用于中断请求
    slowResponseTimer: null,  // 慢响应计时器
    requestStartTime: null  // 请求开始时间
};

// ============================
// DOM 元素引用
// ============================
const elements = {
    // 输入
    provider: document.getElementById('provider'),
    baseUrl: document.getElementById('baseUrl'),
    apiKey: document.getElementById('apiKey'),
    model: document.getElementById('model'),
    goal: document.getElementById('goal'),
    maxSteps: document.getElementById('maxSteps'),
    gameState: document.getElementById('gameState'),
    screenshotInput: document.getElementById('screenshotInput'),
    uploadScreenshot: document.getElementById('uploadScreenshot'),
    screenshotPreview: document.getElementById('screenshotPreview'),
    previewImage: document.getElementById('previewImage'),
    clearScreenshot: document.getElementById('clearScreenshot'),
    ocrResult: document.getElementById('ocrResult'),
    ocrText: document.getElementById('ocrText'),
    
    // 按钮
    fetchModels: document.getElementById('fetchModels'),
    testConnection: document.getElementById('testConnection'),
    startGoal: document.getElementById('startGoal'),
    stopGoal: document.getElementById('stopGoal'),
    toggleKeyVisibility: document.getElementById('toggleKeyVisibility'),
    themeToggle: document.getElementById('themeToggle'),
    clearOutput: document.getElementById('clearOutput'),
    toggleRaw: document.getElementById('toggleRaw'),
    summarizeBtn: document.getElementById('summarizeBtn'),
    exportBtn: document.getElementById('exportBtn'),
    
    // 输出
    decisionOutput: document.getElementById('decisionOutput'),
    rawOutput: document.getElementById('rawOutput'),
    rawJson: document.getElementById('rawJson'),
    connectionStatus: document.getElementById('connectionStatus'),
    experienceList: document.getElementById('experienceList'),
    statusText: document.getElementById('statusText'),
    requestCount: document.getElementById('requestCount'),
    goalProgress: document.getElementById('goalProgress'),
    progressFill: document.getElementById('progressFill'),
    progressText: document.getElementById('progressText')
};

// ============================
// 初始化
// ============================
function init() {
    // 从 localStorage 加载配置
    loadConfig();
    
    // 绑定事件
    bindEvents();
    
    // 初始化主题
    initTheme();
    
    // 初始化提供方选择
    initProvider();
    
    // 更新状态
    updateStatus('就绪');
}

// 初始化提供方选择
function initProvider() {
    // 添加 GVMZ 选项（不在 HTML 中预设）
    const gvmzOption = document.createElement('option');
    gvmzOption.value = 'gvmz';
    gvmzOption.textContent = 'GVMZ';
    elements.provider.insertBefore(gvmzOption, elements.provider.firstChild.nextSibling);
    
    // 设置当前提供方
    if (state.config.provider && API_PROVIDERS[state.config.provider]) {
        elements.provider.value = state.config.provider;
    }
    
    // 如果有 URL 但没有提供方匹配，设为自定义
    if (state.config.baseUrl && !isProviderUrl(state.config.baseUrl)) {
        elements.provider.value = 'custom';
    }
}

// 检查 URL 是否匹配某个提供方
function isProviderUrl(url) {
    return Object.values(API_PROVIDERS).some(p => p.baseUrl === url);
}

// 加载配置
function loadConfig() {
    const saved = localStorage.getItem('gameai_config');
    if (saved) {
        try {
            const config = JSON.parse(saved);
            state.config = { ...state.config, ...config };
            elements.baseUrl.value = state.config.baseUrl;
            elements.apiKey.value = state.config.apiKey;
            
            // 恢复模型列表
            if (state.config.model) {
                updateModelSelect([state.config.model]);
                elements.model.value = state.config.model;
            }
        } catch (e) {
            console.error('Failed to load config:', e);
        }
    }
}

// 保存配置
function saveConfig() {
    state.config.provider = elements.provider.value;
    state.config.baseUrl = elements.baseUrl.value;
    state.config.apiKey = elements.apiKey.value;
    state.config.model = elements.model.value;
    localStorage.setItem('gameai_config', JSON.stringify(state.config));
}

// 绑定事件
function bindEvents() {
    // 提供方选择变化
    elements.provider.addEventListener('change', onProviderChange);
    
    // 获取模型列表
    elements.fetchModels.addEventListener('click', fetchModels);
    
    // 测试连接
    elements.testConnection.addEventListener('click', testConnection);
    
    // 开始目标执行
    elements.startGoal.addEventListener('click', startGoal);
    
    // 停止目标执行
    elements.stopGoal.addEventListener('click', stopGoal);
    
    // 截图上传
    elements.uploadScreenshot.addEventListener('click', () => {
        elements.screenshotInput.click();
    });
    elements.screenshotInput.addEventListener('change', handleScreenshotUpload);
    elements.clearScreenshot.addEventListener('click', clearScreenshot);
    
    // 切换密钥可见性
    elements.toggleKeyVisibility.addEventListener('click', toggleKeyVisibility);
    
    // 切换主题
    elements.themeToggle.addEventListener('click', toggleTheme);
    
    // 清空输出
    elements.clearOutput.addEventListener('click', clearOutput);
    
    // 切换原始JSON显示
    elements.toggleRaw.addEventListener('click', toggleRawOutput);
    
    // 总结经验
    elements.summarizeBtn.addEventListener('click', summarizeExperience);
    
    // 导出经验
    elements.exportBtn.addEventListener('click', exportExperiences);
    
    // 输入变化时保存配置
    elements.baseUrl.addEventListener('change', saveConfig);
    elements.apiKey.addEventListener('change', saveConfig);
    elements.model.addEventListener('change', saveConfig);
    
    // Ctrl+Enter 开始执行
    elements.goal.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            startGoal();
        }
    });
}

// ============================
// 提供方管理
// ============================
function onProviderChange() {
    const provider = elements.provider.value;
    const config = API_PROVIDERS[provider];
    
    if (config && config.baseUrl) {
        elements.baseUrl.value = config.baseUrl;
        state.config.baseUrl = config.baseUrl;
        state.config.provider = provider;
        saveConfig();
        
        // 清空模型选择
        elements.model.innerHTML = '<option value="">请获取模型列表</option>';
        state.availableModels = [];
    }
}

// ============================
// 模型列表获取
// ============================
async function fetchModels() {
    const baseUrl = elements.baseUrl.value.trim();
    const apiKey = elements.apiKey.value.trim();
    
    if (!baseUrl) {
        showStatus('请先填写 API URL', 'error');
        return;
    }
    
    if (!apiKey) {
        showStatus('请先填写 API Key', 'error');
        return;
    }
    
    setLoading(elements.fetchModels, true);
    updateStatus('获取模型列表...');
    
    try {
        const response = await fetch('/api/fetch-models', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ base_url: baseUrl, api_key: apiKey })
        });
        
        const data = await response.json();
        
        if (data.success && data.models.length > 0) {
            state.availableModels = data.models;
            updateModelSelect(data.models);
            showStatus(`获取到 ${data.models.length} 个模型`, 'success');
        } else {
            showStatus(data.message || '未获取到模型', 'error');
        }
    } catch (error) {
        showStatus(`获取失败: ${error.message}`, 'error');
    } finally {
        setLoading(elements.fetchModels, false);
        updateStatus('就绪');
    }
}

// 更新模型下拉框
function updateModelSelect(models) {
    const currentModel = elements.model.value;
    elements.model.innerHTML = '';
    
    if (models.length === 0) {
        elements.model.innerHTML = '<option value="">无可用模型</option>';
        return;
    }
    
    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        elements.model.appendChild(option);
    });
    
    // 恢复之前选择的模型
    if (currentModel && models.includes(currentModel)) {
        elements.model.value = currentModel;
    } else if (state.config.model && models.includes(state.config.model)) {
        elements.model.value = state.config.model;
    }
}

// ============================
// 主题管理
// ============================
function initTheme() {
    const savedTheme = localStorage.getItem('gameai_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('gameai_theme', next);
    updateThemeIcon(next);
}

function updateThemeIcon(theme) {
    elements.themeToggle.textContent = theme === 'dark' ? '☀️' : '🌙';
}

// ============================
// API 操作
// ============================
async function testConnection() {
    const baseUrl = elements.baseUrl.value.trim();
    const apiKey = elements.apiKey.value.trim();
    const model = elements.model.value;
    
    if (!baseUrl || !apiKey) {
        showStatus('请填写 API URL 和 API Key', 'error');
        return;
    }
    
    setLoading(elements.testConnection, true);
    updateStatus('测试连接中...');
    
    try {
        // 先获取模型列表
        const modelsResponse = await fetch('/api/fetch-models', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ base_url: baseUrl, api_key: apiKey })
        });
        
        const modelsData = await modelsResponse.json();
        
        if (modelsData.success) {
            state.availableModels = modelsData.models;
            updateModelSelect(modelsData.models);
            showStatus(`连接成功！获取到 ${modelsData.models.length} 个模型`, 'success');
        } else {
            showStatus(`连接失败: ${modelsData.message}`, 'error');
        }
    } catch (error) {
        showStatus(`请求失败: ${error.message}`, 'error');
    } finally {
        setLoading(elements.testConnection, false);
        updateStatus('就绪');
    }
}

// ============================
// 目标执行
// ============================
async function startGoal() {
    const goal = elements.goal.value.trim();
    const maxSteps = parseInt(elements.maxSteps.value) || 10;
    const gameState = elements.gameState.value.trim();
    
    if (!goal) {
        showStatus('请输入目标描述', 'error');
        return;
    }
    
    if (!state.config.apiKey) {
        showStatus('请先配置 API Key', 'error');
        return;
    }
    
    if (!elements.model.value) {
        showStatus('请先选择模型', 'error');
        return;
    }
    
    // 初始化状态
    state.goalRunning = true;
    state.goalAborted = false;
    state.currentGoal = goal;
    state.stepHistory = [];
    
    // 创建 AbortController
    state.abortController = new AbortController();
    
    // 更新UI
    elements.startGoal.classList.add('hidden');
    elements.stopGoal.classList.remove('hidden');
    elements.goalProgress.classList.remove('hidden');
    
    // 记录请求开始时间
    state.requestStartTime = Date.now();
    
    // 显示加载提示
    elements.decisionOutput.innerHTML = `
        <div class="loading-hint">
            <div class="spinner"></div>
            <div class="text">
                正在连接API，请耐心等待...
                <br>
                <small>如果超过20秒会提示响应较慢</small>
            </div>
        </div>
    `;
    
    // 设置20秒超时慢响应提示
    state.slowResponseTimer = setTimeout(() => {
        if (state.goalRunning && !state.goalAborted) {
            showSlowResponseWarning();
        }
    }, 20000);
    
    setLoading(elements.startGoal, true);
    updateStatus('执行目标中...');
    
    // 保存配置
    saveConfig();
    
    try {
        // 发送目标执行请求
        const response = await fetch('/api/run-goal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                base_url: state.config.baseUrl,
                api_key: state.config.apiKey,
                model: elements.model.value,
                goal: goal,
                max_steps: maxSteps,
                game_state: gameState
            }),
            signal: state.abortController.signal  // 添加 abort signal
        });
        
        // 处理流式响应
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            // 检查是否已中断
            if (state.goalAborted) {
                reader.cancel();
                break;
            }
            
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        handleGoalStreamData(data);
                    } catch (e) {
                        // 忽略解析错误
                    }
                }
            }
        }
        
        // 更新请求计数
        state.requestCount++;
        elements.requestCount.textContent = `请求次数: ${state.requestCount}`;
        
    } catch (error) {
        // 如果是用户主动中断，不显示错误
        if (error.name === 'AbortError') {
            addStepToOutput({
                type: 'warning',
                step: state.stepHistory.length + 1,
                message: '执行已被用户停止'
            });
        } else {
            addStepToOutput({
                type: 'error',
                step: state.stepHistory.length + 1,
                message: `请求失败: ${error.message}`
            });
        }
    } finally {
        state.goalRunning = false;
        state.abortController = null;
        elements.startGoal.classList.remove('hidden');
        elements.stopGoal.classList.add('hidden');
        setLoading(elements.startGoal, false);
        updateStatus('就绪');
    }
}

function stopGoal() {
    state.goalAborted = true;
    
    // 中断 fetch 请求
    if (state.abortController) {
        state.abortController.abort();
    }
    
    // 清除慢响应提示
    clearSlowResponseWarning();
    
    // 清除超时计时器
    if (state.slowResponseTimer) {
        clearTimeout(state.slowResponseTimer);
        state.slowResponseTimer = null;
    }
    
    state.goalRunning = false;
    showStatus('已停止执行', 'info');
}

// 截图上传处理
async function handleScreenshotUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // 预览图片
    const reader = new FileReader();
    reader.onload = (e) => {
        elements.previewImage.src = e.target.result;
        elements.screenshotPreview.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
    
    // 上传到服务器
    const formData = new FormData();
    formData.append('screenshot', file);
    
    try {
        showStatus('正在上传截图...', 'info');
        const response = await fetch('/api/upload-screenshot', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (data.success) {
            showStatus('截图已上传', 'success');
            // 自动进行OCR识别
            await performOCR();
        } else {
            showStatus(`上传失败: ${data.message}`, 'error');
        }
    } catch (error) {
        showStatus(`上传失败: ${error.message}`, 'error');
    }
}

// 执行OCR识别
async function performOCR() {
    try {
        elements.ocrResult.classList.remove('hidden');
        elements.ocrText.textContent = '识别中...';
        
        const response = await fetch('/api/get-ocr', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        if (data.success) {
            elements.ocrText.textContent = data.text || '未识别到文字';
        } else {
            elements.ocrText.textContent = `识别失败: ${data.message}`;
        }
    } catch (error) {
        elements.ocrText.textContent = `识别失败: ${error.message}`;
    }
}

// 清除截图
function clearScreenshot() {
    elements.screenshotInput.value = '';
    elements.screenshotPreview.classList.add('hidden');
    elements.ocrResult.classList.add('hidden');
    elements.previewImage.src = '';
    elements.ocrText.textContent = '';
}

function handleGoalStreamData(data) {
    switch (data.type) {
        case 'start':
            addStepToOutput({
                type: 'info',
                step: 0,
                message: data.message
            });
            // 显示加载提示
            updateStatus('正在连接API，请耐心等待...');
            break;
            
        case 'ocr_start':
            // OCR识别开始
            updateStatus(`步骤 ${data.step}: 正在OCR识别游戏画面...`);
            break;
            
        case 'step_start':
            updateProgress(data.step, data.max_steps);
            addStepToOutput({
                type: 'running',
                step: data.step,
                message: `步骤 ${data.step}/${data.max_steps}: 正在请求AI分析...`
            });
            updateStatus(`步骤 ${data.step}: 等待API响应...`);
            // 重新设置20秒超时提示
            state.requestStartTime = Date.now();
            state.slowResponseTimer = setTimeout(() => {
                if (state.goalRunning && !state.goalAborted) {
                    showSlowResponseWarning();
                }
            }, 20000);
            break;
            
        case 'step_action':
            // 收到响应，清除慢响应提示
            clearSlowResponseWarning();
            if (state.slowResponseTimer) {
                clearTimeout(state.slowResponseTimer);
                state.slowResponseTimer = null;
            }
            updateStepAction(data.step, data.action);
            updateStatus(`步骤 ${data.step}: 已获取决策`);
            break;
            
        case 'step_complete':
            updateStepComplete(data.step, data.result);
            state.stepHistory.push(data.result);
            // 检查是否需要自动总结经验
            autoSummarizeExperiences();
            break;
            
        case 'retry':
            // 显示重试信息
            updateStatus(`重试中: ${data.message}`);
            break;
            
        case 'goal_achieved':
            addStepToOutput({
                type: 'completed',
                step: data.step,
                message: `目标达成！${data.message}`
            });
            // 添加完成动画
            elements.decisionOutput.classList.add('goal-complete');
            setTimeout(() => {
                elements.decisionOutput.classList.remove('goal-complete');
            }, 2000);
            break;
            
        case 'goal_failed':
            addStepToOutput({
                type: 'failed',
                step: data.step,
                message: `执行失败: ${data.message}`
            });
            break;
            
        case 'max_steps_reached':
            addStepToOutput({
                type: 'warning',
                step: data.step,
                message: `已达最大步数限制，目标未完成`
            });
            break;
            
        case 'error':
            addStepToOutput({
                type: 'error',
                step: state.stepHistory.length + 1,
                message: data.message
            });
            break;
    }
}

function addStepToOutput(stepData) {
    // 生成动作列表HTML
    let actionsHtml = '';
    if (stepData.actions && stepData.actions.length > 0) {
        actionsHtml = `
            <div class="step-actions-list">
                <div class="step-action-header">动作序列 (${stepData.actions.length}个)</div>
                ${stepData.actions.map((action, index) => `
                    <div class="step-action-item-row">
                        <span class="action-index">${index + 1}.</span>
                        <span class="action-type">${action.type || '-'}</span>
                        ${action.target ? `<span class="action-detail">目标: ${action.target}</span>` : ''}
                        ${action.direction ? `<span class="action-detail">方向: ${action.direction}</span>` : ''}
                        ${action.position ? `<span class="action-detail">位置: ${action.position}</span>` : ''}
                        ${action.key ? `<span class="action-detail">按键: ${action.key}</span>` : ''}
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    const stepHtml = `
        <div class="step-card">
            <div class="step-header">
                <span class="step-number">${stepData.step > 0 ? `步骤 ${stepData.step}` : '系统'}</span>
                <span class="step-status ${stepData.type}">${getStatusText(stepData.type)}</span>
            </div>
            <div class="step-content">${stepData.message}</div>
            ${actionsHtml}
            ${stepData.confidence ? `
                <div class="step-confidence">
                    置信度: ${Math.round((stepData.confidence || 0) * 100)}%
                </div>
            ` : ''}
        </div>
    `;
    
    elements.decisionOutput.innerHTML += stepHtml;
    elements.decisionOutput.scrollTop = elements.decisionOutput.scrollHeight;
}

function updateProgress(current, max) {
    const percent = Math.round((current / max) * 100);
    elements.progressFill.style.width = `${percent}%`;
    elements.progressText.textContent = `进度: ${current}/${max}`;
}

function updateStepAction(step, action) {
    // 更新最后一步的动作信息
    const lastStep = elements.decisionOutput.lastElementChild;
    if (lastStep && action.actions) {
        const actionsHtml = `
            <div class="step-actions-list">
                <div class="step-action-header">动作序列 (${action.actions.length}个)</div>
                ${action.actions.map((a, index) => `
                    <div class="step-action-item-row">
                        <span class="action-index">${index + 1}.</span>
                        <span class="action-type">${a.type || '-'}</span>
                        ${a.target ? `<span class="action-detail">目标: ${a.target}</span>` : ''}
                        ${a.direction ? `<span class="action-detail">方向: ${a.direction}</span>` : ''}
                        ${a.position ? `<span class="action-detail">位置: ${a.position}</span>` : ''}
                        ${a.key ? `<span class="action-detail">按键: ${a.key}</span>` : ''}
                    </div>
                `).join('')}
            </div>
        `;
        lastStep.innerHTML += actionsHtml;
    }
}

function updateStepComplete(step, result) {
    // 更新最后一步的状态
    const lastStep = elements.decisionOutput.lastElementChild;
    if (lastStep) {
        const statusEl = lastStep.querySelector('.step-status');
        if (statusEl) {
            statusEl.className = 'step-status success';
            statusEl.textContent = '完成';
        }
        
        // 添加推理信息
        if (result.reasoning) {
            const reasoningHtml = `
                <div class="step-content" style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--border-color);">
                    <strong>推理:</strong> ${result.reasoning}
                </div>
            `;
            lastStep.innerHTML += reasoningHtml;
        }
        
        // 添加进度信息
        if (result.progress) {
            const progressHtml = `
                <div class="step-content" style="margin-top: 4px;">
                    <strong>进度:</strong> ${result.progress}
                </div>
            `;
            lastStep.innerHTML += progressHtml;
        }
    }
}

function getStatusText(type) {
    const statusMap = {
        'info': '信息',
        'running': '执行中',
        'success': '成功',
        'failed': '失败',
        'completed': '已完成',
        'warning': '警告',
        'error': '错误'
    };
    return statusMap[type] || type;
}

// ============================
// 显示决策结果
// ============================
function displayDecision(decision) {
    const confidencePercent = Math.round((decision.confidence || 0) * 100);
    
    const html = `
        <div class="decision-card">
            <div class="decision-header">
                <span class="decision-action">${decision.action || 'unknown'}</span>
                <div class="decision-confidence">
                    <span>${confidencePercent}%</span>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${confidencePercent}%"></div>
                    </div>
                </div>
            </div>
            <div class="decision-details">
                <div class="detail-item">
                    <span class="detail-label">目标</span>
                    <span class="detail-value">${decision.target || '-'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">方向</span>
                    <span class="detail-value">${decision.direction || '-'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">位置</span>
                    <span class="detail-value">${decision.position || '-'}</span>
                </div>
            </div>
            <div class="decision-reasoning">
                <div class="decision-reasoning-label">推理过程</div>
                <div class="decision-reasoning-text">${decision.reasoning || '无'}</div>
            </div>
        </div>
    `;
    
    elements.decisionOutput.innerHTML = html;
}

// ============================
// 经验管理
// ============================
async function loadExperiences() {
    try {
        const response = await fetch('/api/experiences');
        const data = await response.json();
        
        state.experiences = data.experiences || [];
        renderExperiences();
    } catch (error) {
        console.error('Failed to load experiences:', error);
    }
}

function renderExperiences() {
    if (state.experiences.length === 0) {
        elements.experienceList.innerHTML = '<div class="placeholder-text">暂无经验记录</div>';
        return;
    }
    
    const html = state.experiences.map(exp => `
        <div class="experience-item">
            <div class="experience-header">
                <span class="experience-id">#${exp.id}</span>
                <span class="experience-time">${exp.timestamp}</span>
            </div>
            <div class="experience-content">
                <strong>观察:</strong> ${exp.observation || ''}<br>
                <strong>动作:</strong> ${exp.action || ''}<br>
                <strong>经验:</strong> ${exp.lesson || ''}
            </div>
        </div>
    `).join('');
    
    elements.experienceList.innerHTML = html;
}

async function summarizeExperience() {
    if (state.history.length === 0) {
        showStatus('没有可总结的会话历史', 'error');
        return;
    }
    
    setLoading(elements.summarizeBtn, true);
    updateStatus('总结经验中...');
    
    try {
        const response = await fetch('/api/summarize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                base_url: state.config.baseUrl,
                api_key: state.config.apiKey,
                model: elements.model.value
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStatus('经验总结完成', 'success');
            loadExperiences();
        } else {
            showStatus(`总结失败: ${data.message}`, 'error');
        }
    } catch (error) {
        showStatus(`请求失败: ${error.message}`, 'error');
    } finally {
        setLoading(elements.summarizeBtn, false);
        updateStatus('就绪');
    }
}

function exportExperiences() {
    if (state.experiences.length === 0) {
        showStatus('没有可导出的经验', 'error');
        return;
    }
    
    const data = JSON.stringify(state.experiences, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `gameai_experiences_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    
    URL.revokeObjectURL(url);
    showStatus('经验已导出', 'success');
}

// ============================
// UI 辅助函数
// ============================
function toggleKeyVisibility() {
    const input = elements.apiKey;
    input.type = input.type === 'password' ? 'text' : 'password';
    elements.toggleKeyVisibility.textContent = input.type === 'password' ? '👁️' : '🙈';
}

function clearOutput() {
    elements.decisionOutput.innerHTML = '<div class="placeholder-text">等待目标输入...</div>';
    elements.rawJson.textContent = '';
    elements.goalProgress.classList.add('hidden');
}

function toggleRawOutput() {
    elements.rawOutput.classList.toggle('hidden');
    elements.toggleRaw.textContent = elements.rawOutput.classList.contains('hidden') 
        ? '查看原始JSON' 
        : '隐藏原始JSON';
}

function showStatus(message, type = 'info') {
    elements.connectionStatus.textContent = message;
    elements.connectionStatus.className = `status-message ${type}`;
    elements.connectionStatus.classList.remove('hidden');
    
    // 5秒后自动隐藏
    setTimeout(() => {
        elements.connectionStatus.classList.add('hidden');
    }, 5000);
}

function updateStatus(text) {
    elements.statusText.textContent = text;
}

function setLoading(button, loading) {
    if (loading) {
        button.classList.add('loading');
        button.disabled = true;
    } else {
        button.classList.remove('loading');
        button.disabled = false;
    }
}

// 慢响应提示
function showSlowResponseWarning() {
    // 检查是否已存在提示
    let warningEl = document.getElementById('slowResponseWarning');
    if (warningEl) return;
    
    // 计算已等待时间
    const elapsed = Math.round((Date.now() - state.requestStartTime) / 1000);
    
    // 创建提示元素
    warningEl = document.createElement('div');
    warningEl.id = 'slowResponseWarning';
    warningEl.className = 'timeout-warning';
    warningEl.innerHTML = `
        <div class="icon">⏳</div>
        <div class="message">
            <strong>API响应较慢</strong><br>
            已等待 ${elapsed} 秒，请耐心等待或点击"停止执行"
        </div>
    `;
    
    // 插入到输出区域顶部
    elements.decisionOutput.insertBefore(warningEl, elements.decisionOutput.firstChild);
}

function clearSlowResponseWarning() {
    const warningEl = document.getElementById('slowResponseWarning');
    if (warningEl) {
        warningEl.remove();
    }
}

// 经验自动总结
async function autoSummarizeExperiences() {
    // 每5条经验自动总结一次
    if (state.experiences.length > 0 && state.experiences.length % 5 === 0) {
        console.log('经验达到5条，自动总结...');
        try {
            const response = await fetch('/api/summarize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    base_url: state.config.baseUrl,
                    api_key: state.config.apiKey,
                    model: elements.model.value
                })
            });
            
            const data = await response.json();
            if (data.success) {
                console.log('经验自动总结完成');
                loadExperiences();
            }
        } catch (error) {
            console.error('经验自动总结失败:', error);
        }
    }
}

// ============================
// 初始化应用
// ============================
document.addEventListener('DOMContentLoaded', () => {
    init();
    loadExperiences();
});
