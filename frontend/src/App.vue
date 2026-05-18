<script setup>
import { ref, onMounted, nextTick } from 'vue'

const API_BASE = 'http://localhost:8000'

const messages = ref([])
const inputMessage = ref('')
const isLoading = ref(false)
const chatContainer = ref(null)
const stocks = ref([])
const loadingStocks = ref(true)
const sessionId = ref(generateSessionId())
const TYPEWRITER_DELAY_MS = 18

function generateSessionId() {
  return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
}

// Example queries for quick start
const exampleQueries = [
  '市值最大的5只银行股是哪些？',
  '分析贵州茅台的财务状况',
  '最近新能源行业有什么新闻？'
]

onMounted(async () => {
  await fetchStocks()
})

async function fetchStocks() {
  try {
    const res = await fetch(`${API_BASE}/api/stocks`)
    const data = await res.json()
    stocks.value = data.data.slice(0, 6)
    loadingStocks.value = false
  } catch (e) {
    console.error('Failed to fetch stocks:', e)
    loadingStocks.value = false
  }
}

async function sendMessage(query = null) {
  const queryText = query || inputMessage.value.trim()
  if (!queryText || isLoading.value) return

  messages.value.push({
    role: 'user',
    content: queryText,
    timestamp: new Date()
  })

  inputMessage.value = ''
  isLoading.value = true

  // Add placeholder for assistant
  messages.value.push({
    role: 'assistant',
    content: '正在启动分析流程...',
    reasoning: [],
    reflections: [],
    timestamp: new Date(),
    isTyping: true,
    isStreaming: true
  })

  scrollToBottom()

  try {
    const res = await fetch(`${API_BASE}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: queryText,
        stream: true,
        max_iterations: 3,
        session_id: sessionId.value
      })
    })

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }

    const lastMsg = messages.value[messages.value.length - 1]
    lastMsg.isTyping = false

    await readSseStream(res.body, async (event) => {
      await applyStreamEvent(lastMsg, event)
      nextTick(scrollToBottom)
    })

    lastMsg.isStreaming = false
    lastMsg.isTyping = false
    if (!lastMsg.content || lastMsg.content === '正在启动分析流程...') {
      lastMsg.content = '分析已完成，但没有生成可展示的回答。'
    }

  } catch (e) {
    console.error('Chat error:', e)
    const lastMsg = messages.value[messages.value.length - 1]
    lastMsg.isTyping = false
    lastMsg.isStreaming = false
    lastMsg.content = '抱歉，暂时无法处理您的请求，请稍后重试。'
  } finally {
    isLoading.value = false
    nextTick(scrollToBottom)
  }
}

async function readSseStream(stream, onEvent) {
  if (!stream) return

  const reader = stream.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''

    for (const rawEvent of events) {
      const dataText = rawEvent
        .split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.replace(/^data:\s?/, ''))
        .join('\n')

      if (!dataText) continue

      try {
        await onEvent(JSON.parse(dataText))
      } catch (e) {
        console.warn('Failed to parse stream event:', dataText, e)
      }
    }
  }

  if (buffer.trim()) {
    const dataText = buffer
      .split('\n')
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.replace(/^data:\s?/, ''))
      .join('\n')

    if (dataText) {
      try {
        await onEvent(JSON.parse(dataText))
      } catch (e) {
        console.warn('Failed to parse final stream event:', dataText, e)
      }
    }
  }
}

async function applyStreamEvent(message, event) {
  if (event.node === 'error') {
    message.content = `分析过程中出现错误：${event.error || '未知错误'}`
    message.isStreaming = false
    return
  }

  const state = event.state || {}
  const reasoning = state.reasoning_steps || state.reason_steps
  const reflections = state.reflections || state.reflectons

  if (Array.isArray(reasoning)) {
    message.reasoning = reasoning
  }

  if (Array.isArray(reflections)) {
    message.reflections = reflections
  }

  if (state.final_answer) {
    await typeText(message, state.final_answer)
    return
  }

  const nodeLabels = {
    router: '正在识别问题意图...',
    planner: '正在制定分析计划...',
    executor: '正在调用工具执行分析...',
    reflector: '正在反思结果完整性...',
    critic: '正在生成最终回答...'
  }

  message.content = nodeLabels[event.node] || '正在处理请求...'
}

async function typeText(message, text) {
  message.content = ''

  for (const char of text) {
    message.content += char
    await nextTick()
    scrollToBottom()
    await sleep(TYPEWRITER_DELAY_MS)
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function scrollToBottom() {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

function formatTime(date) {
  return new Date(date).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<template>
  <div class="app-container">
    <!-- Header -->
    <header class="header">
      <div class="header-brand">
        <div class="logo">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="14" stroke="currentColor" stroke-width="1.5"/>
            <path d="M16 8v16M10 14l6-4 6 4M10 18l6 4 6-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="brand-text">
          <h1 class="display-text">Finance Analyst</h1>
          <span class="tagline">智能金融研报分析助手</span>
        </div>
      </div>
      <div class="header-status">
        <span class="status-dot"></span>
        <span class="status-text">LangGraph Powered</span>
      </div>
    </header>

    <main class="main-content">
      <!-- Sidebar: Stock Overview -->
      <aside class="sidebar">
        <div class="sidebar-header">
          <h2>市场概览</h2>
        </div>
        <div class="stock-list">
          <div v-if="loadingStocks" class="stock-loading">
            <div class="skeleton" style="height: 60px; margin-bottom: 8px;"></div>
            <div class="skeleton" style="height: 60px; margin-bottom: 8px;"></div>
            <div class="skeleton" style="height: 60px;"></div>
          </div>
          <div
            v-for="stock in stocks"
            :key="stock.stock_code"
            class="stock-card"
          >
            <div class="stock-info">
              <span class="stock-name">{{ stock.stock_name }}</span>
              <span class="stock-code">{{ stock.stock_code }}</span>
            </div>
            <div class="stock-metrics">
              <span class="stock-cap">{{ stock.market_cap?.toFixed(0) || 'N/A' }}亿</span>
              <span
                class="stock-pe"
                :class="stock.pe_ratio > 0 ? 'text-emerald' : 'text-ruby'"
              >
                PE {{ stock.pe_ratio?.toFixed(1) || 'N/A' }}
              </span>
            </div>
          </div>
        </div>

        <div class="sidebar-footer">
          <div class="capabilities">
            <span class="capability-badge">Text2SQL</span>
            <span class="capability-badge">Code Executor</span>
            <span class="capability-badge">Web Search</span>
          </div>
        </div>
      </aside>

      <!-- Chat Area -->
      <section class="chat-area">
        <div class="chat-container" ref="chatContainer">
          <!-- Welcome Message -->
          <div v-if="messages.length === 0" class="welcome">
            <div class="welcome-icon">
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="1.5"/>
                <path d="M24 14v20M16 22l8-6 8 6M16 28l8 6 8-6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </div>
            <h2 class="display-text welcome-title">您好，我是您的智能金融分析助手</h2>
            <p class="welcome-desc">我可以帮您查询股票数据、分析财务状况、解读市场资讯</p>

            <div class="example-queries">
              <span class="example-label">试试这样问：</span>
              <button
                v-for="q in exampleQueries"
                :key="q"
                class="example-btn"
                @click="sendMessage(q)"
              >
                {{ q }}
              </button>
            </div>
          </div>

          <!-- Messages -->
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="message"
            :class="[`message-${msg.role}`, { 'animate-fade-in': idx === messages.length - 1 }]"
          >
            <div class="message-avatar">
              <div v-if="msg.role === 'user'" class="avatar user-avatar">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M8 8a3 3 0 100-6 3 3 0 000 6zm-5 9v-2a5 5 0 0110 0v2H3z"/>
                </svg>
              </div>
              <div v-else class="avatar assistant-avatar">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <circle cx="8" cy="8" r="6"/>
                  <path d="M8 5v4M8 11v.01" stroke="var(--bg-primary)" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
              </div>
            </div>
            <div class="message-content">
              <div class="message-header">
                <span class="message-sender">{{ msg.role === 'user' ? '您' : '分析师' }}</span>
                <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
              </div>
              <div class="message-body">
                <div v-if="msg.isTyping && !msg.content" class="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
                <div v-else class="message-text">
                  <span v-html="formatContent(msg.content)"></span>
                  <span v-if="msg.isStreaming" class="stream-cursor"></span>
                </div>
              </div>
              <!-- Reasoning Process -->
              <div v-if="msg.reasoning && msg.reasoning.length > 0" class="reasoning-section">
                <button class="reasoning-toggle" @click="msg.showReasoning = !msg.showReasoning">
                  <svg width="12" height="12" viewBox="0 0 12 12" :class="{ rotated: msg.showReasoning }">
                    <path d="M3 5l3 3 3-3" stroke="currentColor" stroke-width="1.5" fill="none"/>
                  </svg>
                  <span>推理过程 ({{ msg.reasoning.length }}步)</span>
                </button>
                <div v-if="msg.showReasoning" class="reasoning-steps">
                  <div v-for="(step, i) in msg.reasoning" :key="i" class="reasoning-step" v-html="formatStep(step)"></div>
                </div>
              </div>
              <!-- Reflections -->
              <div v-if="msg.reflections && msg.reflections.length > 0" class="reflection-section">
                <button class="reasoning-toggle" @click="msg.showReflection = !msg.showReflection">
                  <svg width="12" height="12" viewBox="0 0 12 12" :class="{ rotated: msg.showReflection }">
                    <path d="M3 5l3 3 3-3" stroke="currentColor" stroke-width="1.5" fill="none"/>
                  </svg>
                  <span>反思 ({{ msg.reflections.length }}轮)</span>
                </button>
                <div v-if="msg.showReflection" class="reasoning-steps">
                  <div v-for="(r, i) in msg.reflections" :key="i" class="reflection-item">
                    <span class="reflection-label">第{{ r.iteration }}轮:</span>
                    <span>{{ r.reflection }}</span>
                    <span class="confidence-badge">置信度 {{ (r.confidence * 100).toFixed(0) }}%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Input Area -->
        <div class="input-area">
          <div class="input-wrapper">
            <input
              v-model="inputMessage"
              type="text"
              class="input chat-input"
              placeholder="输入您的问题..."
              @keyup.enter="sendMessage()"
              :disabled="isLoading"
            />
            <button
              class="send-btn"
              :disabled="!inputMessage.trim() || isLoading"
              @click="sendMessage()"
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M3 10l14-6-6 14-2-6-6-2z" fill="currentColor"/>
              </svg>
            </button>
          </div>
          <p class="input-hint">基于 LangGraph 多智能体工作流，支持 Text2SQL、代码执行、网络搜索</p>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
function formatContent(content) {
  if (!content) return ''
  // Basic formatting
  return content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
    .replace(/`(.*?)`/g, '<code style="background: var(--bg-tertiary); padding: 2px 6px; border-radius: 4px; font-family: var(--font-mono); font-size: 0.9em;">$1</code>')
}

function formatStep(step) {
  if (!step) return ''
  // Highlight brackets content
  return step
    .replace(/\[(.*?)\]/g, '<span class="step-bracket">[$1]</span>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
}
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

/* Header */
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md) var(--space-xl);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-subtle);
}

.header-brand {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.logo {
  width: 40px;
  height: 40px;
  color: var(--accent-gold);
}

.brand-text h1 {
  font-size: 1.25rem;
  font-weight: 400;
  color: var(--text-primary);
  margin: 0;
}

.tagline {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.header-status {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.status-dot {
  width: 8px;
  height: 8px;
  background: var(--accent-emerald);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-text {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

/* Main Content */
.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* Sidebar */
.sidebar {
  width: 280px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: var(--space-lg);
  border-bottom: 1px solid var(--border-subtle);
}

.sidebar-header h2 {
  font-family: var(--font-display);
  font-size: 1.125rem;
  font-weight: 400;
  color: var(--text-primary);
}

.stock-list {
  flex: 1;
  padding: var(--space-md);
  overflow-y: auto;
}

.stock-loading {
  padding: var(--space-sm);
}

.stock-card {
  padding: var(--space-md);
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-sm);
  cursor: pointer;
  transition: all 0.2s ease;
}

.stock-card:hover {
  border-color: var(--border-gold);
  transform: translateX(4px);
}

.stock-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-xs);
}

.stock-name {
  font-weight: 500;
  color: var(--text-primary);
}

.stock-code {
  font-size: 0.75rem;
  font-family: var(--font-mono);
  color: var(--text-muted);
}

.stock-metrics {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stock-cap {
  font-size: 0.875rem;
  font-family: var(--font-mono);
  color: var(--accent-gold);
}

.stock-pe {
  font-size: 0.75rem;
  font-family: var(--font-mono);
}

.sidebar-footer {
  padding: var(--space-md);
  border-top: 1px solid var(--border-subtle);
}

.capabilities {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
}

.capability-badge {
  padding: 2px 8px;
  font-size: 0.625rem;
  font-family: var(--font-mono);
  color: var(--accent-gold);
  background: var(--accent-gold-glow);
  border: 1px solid var(--border-gold);
  border-radius: var(--radius-sm);
}

/* Chat Area */
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-xl);
}

/* Welcome */
.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  min-height: 60vh;
  animation: fadeIn 0.6s ease-out;
}

.welcome-icon {
  color: var(--accent-gold);
  margin-bottom: var(--space-lg);
  opacity: 0.8;
}

.welcome-title {
  font-size: 1.75rem;
  font-weight: 300;
  color: var(--text-primary);
  margin-bottom: var(--space-sm);
}

.welcome-desc {
  color: var(--text-secondary);
  margin-bottom: var(--space-xl);
  max-width: 400px;
}

.example-queries {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  align-items: center;
}

.example-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-bottom: var(--space-xs);
}

.example-btn {
  padding: var(--space-sm) var(--space-md);
  font-size: 0.875rem;
  color: var(--text-secondary);
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;
  max-width: 320px;
}

.example-btn:hover {
  color: var(--accent-gold);
  border-color: var(--border-gold);
  background: var(--bg-tertiary);
}

/* Messages */
.message {
  display: flex;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.message-user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-avatar {
  background: var(--accent-gold);
  color: var(--bg-primary);
}

.assistant-avatar {
  background: var(--bg-tertiary);
  color: var(--accent-gold);
}

.message-content {
  max-width: 70%;
}

.message-user .message-content {
  align-items: flex-end;
}

.message-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-xs);
}

.message-sender {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.message-time {
  font-size: 0.625rem;
  font-family: var(--font-mono);
  color: var(--text-muted);
}

.message-body {
  padding: var(--space-md);
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
}

.message-user .message-body {
  background: var(--accent-gold-glow);
  border-color: var(--border-gold);
}

.message-text {
  font-size: 0.9375rem;
  line-height: 1.7;
  color: var(--text-primary);
}

.stream-cursor {
  display: inline-block;
  width: 7px;
  height: 1em;
  margin-left: 4px;
  vertical-align: -0.15em;
  background: var(--accent-gold);
  animation: pulse 1s infinite;
}

/* Typing Indicator */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: var(--space-xs);
}

.typing-indicator span {
  width: 6px;
  height: 6px;
  background: var(--accent-gold);
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

/* Reasoning Section */
.reasoning-section,
.reflection-section {
  margin-top: var(--space-md);
  padding-top: var(--space-md);
  border-top: 1px solid var(--border-subtle);
}

.reasoning-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-sm);
  font-size: 0.75rem;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s ease;
}

.reasoning-toggle:hover {
  color: var(--accent-gold);
  border-color: var(--border-gold);
}

.reasoning-toggle svg {
  transition: transform 0.2s ease;
}

.reasoning-toggle svg.rotated {
  transform: rotate(180deg);
}

.reasoning-steps {
  margin-top: var(--space-sm);
  padding: var(--space-sm);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  font-family: var(--font-mono);
}

.reasoning-step {
  padding: var(--space-xs) 0;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-subtle);
}

.reasoning-step:last-child {
  border-bottom: none;
}

.reasoning-step :deep(.step-bracket) {
  color: var(--accent-gold);
}

.reflection-item {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
  padding: var(--space-xs) 0;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-subtle);
}

.reflection-item:last-child {
  border-bottom: none;
}

.reflection-label {
  color: var(--accent-sapphire);
  font-weight: 500;
}

.confidence-badge {
  margin-left: auto;
  padding: 1px 6px;
  font-size: 0.625rem;
  color: var(--accent-emerald);
  background: rgba(52, 211, 153, 0.1);
  border-radius: var(--radius-sm);
}

/* Input Area */
.input-area {
  padding: var(--space-lg) var(--space-xl);
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-subtle);
}

.input-wrapper {
  display: flex;
  gap: var(--space-sm);
  max-width: 800px;
  margin: 0 auto;
}

.chat-input {
  flex: 1;
  padding: var(--space-md) var(--space-lg);
  font-size: 1rem;
}

.send-btn {
  width: 48px;
  height: 48px;
  background: var(--accent-gold);
  color: var(--bg-primary);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 4px 20px rgba(212, 168, 83, 0.3);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.input-hint {
  text-align: center;
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: var(--space-sm);
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
}
</style>
