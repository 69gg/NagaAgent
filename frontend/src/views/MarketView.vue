<script setup lang="ts">
import { computed, h, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CONFIG } from '@/utils/config'

const router = useRouter()
const route = useRoute()

const tabs = [
  { id: 'skin', label: '界面背景' },
  { id: 'album', label: '音之巷' },
  { id: 'memory-skin', label: '角色注册' },
  { id: 'memory-trade', label: '记忆云迁' },
  { id: 'mcp', label: 'MCP工具' },
  { id: 'skill', label: '智能体技能' },
  { id: 'recharge', label: '模型充值' },
] as const

const svgIcon = (...paths: string[]) => h('svg', { 'viewBox': '0 0 24 24', 'fill': 'none', 'stroke': 'currentColor', 'stroke-width': 1.8, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'tab-icon-svg' }, paths.map(d => h('path', { d })))

const tabIcons: Record<string, { render: () => ReturnType<typeof h> }> = {
  'album': { render: () => svgIcon('M9 18V5l12-2v13', 'M9 18a3 3 0 1 0 6 0 9 9 0 0 0 6 0') },
  'mcp': { render: () => svgIcon('M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z', 'M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z') },
  'skill': { render: () => svgIcon('M13 2L3 14h9l-1 8 10-12h-9l1-8z') },
  'skin': { render: () => svgIcon('M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2', 'M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z') },
  'memory-skin': { render: () => svgIcon('M2 10c3 0 5 2 8 0s5-2 8 0', 'M2 14c3 0 5 2 8 0s5-2 8 0') },
  'memory-trade': { render: () => svgIcon('M7 16V4m0 0L3 8m4-4l4 4', 'M17 8v12m0 0l4-4m-4 4l-4-4') },
  'recharge': { render: () => svgIcon('M12 2L3 9l4 12h10l4-12-9-7z') },
}

type TabId = typeof tabs[number]['id']
const initTab = route.query.tab as string | undefined
const activeTab = ref<TabId>(
  tabs.some(t => t.id === initTab) ? initTab as TabId : 'skin',
)

// 专辑数据：仅保留沙之书，左上角角标为 NEW
const albumItems = [
  { id: 1, title: '沙之书', subtitle: '', daysLeft: 0, price: 0, image: '/assets/just.png', bannerLabel: 'NEW' as const },
]

// ── 拖动横向滚动（通用） ──
const albumSection = ref<HTMLElement | null>(null)
const characterSectionRef = ref<HTMLElement | null>(null)

let wasDragging = false
const DRAG_THRESHOLD = 4

function initDragScroll(container: HTMLElement) {
  container.addEventListener('mousedown', (e: MouseEvent) => {
    let startX = e.clientX
    let startScrollLeft = container.scrollLeft
    let moved = false

    container.style.cursor = 'grabbing'
    document.body.style.cursor = 'grabbing'

    function onMove(ev: MouseEvent) {
      const dx = ev.clientX - startX
      if (Math.abs(dx) > DRAG_THRESHOLD) moved = true
      container.scrollLeft = startScrollLeft - dx
    }

    function onUp() {
      wasDragging = moved
      container.style.cursor = 'grab'
      document.body.style.cursor = ''
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
      // 在 click 事件触发后再重置标记
      setTimeout(() => { wasDragging = false }, 0)
    }

    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  })

  container.addEventListener('wheel', (e: WheelEvent) => {
    e.preventDefault()
    container.scrollLeft += e.deltaY
  }, { passive: false })
}

onMounted(() => {
  if (albumSection.value) initDragScroll(albumSection.value)
  if (characterSectionRef.value) initDragScroll(characterSectionRef.value)
})

// ── 角色注册 ──
interface CharacterCard {
  id: string
  name: string
  bio: string
  portraitUrl: string
}

const expandedCard = ref<string | null>(null)
const charCardRefs: Record<string, HTMLElement> = {}

const characters: CharacterCard[] = [
  {
    id: 'nadezhda',
    name: '娜杰日达',
    bio: '由创造者柏斯阔落亲手创造的AI智能体，亦称娜迦。',
    portraitUrl: 'naga-char://娜杰日达/Naga.png',
  },
]

// 立绘统一比例 3:4（宽:高），直接显示完整画布
// 展开 = cardH × 3/4（原图宽高比）
// 收缩 = cardH × 2/5
function computeAllCardWidths() {
  for (const char of characters) {
    const el = charCardRefs[char.id]
    if (!el) continue
    const h = el.offsetHeight
    if (h <= 0) continue
    el.style.setProperty('--collapsed-w', `${Math.round(h * 2 / 5)}px`)
    el.style.setProperty('--expanded-w', `${Math.round(h * 3 / 4)}px`)
  }
  // custom card
  const customEl = charCardRefs['custom']
  if (customEl) {
    const ch = customEl.offsetHeight
    if (ch > 0) {
      customEl.style.setProperty('--collapsed-w', `${Math.round(ch * 2 / 5)}px`)
      customEl.style.setProperty('--expanded-w', `${Math.round(ch * 3 / 4)}px`)
    }
  }
}

function setCardRef(charId: string, el: any) {
  if (el) charCardRefs[charId] = el as HTMLElement
}

function toggleCard(id: string) {
  if (wasDragging) return
  expandedCard.value = expandedCard.value === id ? null : id
}

function onSectionClick() {
  if (!wasDragging) expandedCard.value = null
}

function applyCharacter(name: string) {
  CONFIG.value.system.active_character = name
}

// ── 自定义角色 ──
const customChar = reactive({ name: '', modelFile: null as File | null, prompt: '' })
const customReady = computed(() =>
  customChar.name.trim() !== '' && customChar.modelFile !== null && customChar.prompt.trim() !== '',
)
const fileInputRef = ref<HTMLInputElement | null>(null)

function triggerFileInput() {
  fileInputRef.value?.click()
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    customChar.modelFile = input.files[0] ?? null
  }
}

function applyCustomCharacter() {
  CONFIG.value.system.ai_name = customChar.name
  CONFIG.value.system.active_character = ''
}

// 标签可见时实时计算宽度（v-show 隐藏时 offsetHeight 为 0）
watch(activeTab, (tab) => {
  if (tab === 'memory-skin') {
    nextTick(computeAllCardWidths)
  }
})
</script>

<template>
  <div class="market-page">
    <!-- 顶部栏：返回 + 标题 -->
    <header class="market-header">
      <div class="header-left">
        <button type="button" class="back-btn" title="返回" @click="router.back">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
        <h1 class="market-title">
          枢机集市
        </h1>
      </div>
    </header>

    <!-- 标签导航 -->
    <nav class="market-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="tab-btn"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        <component :is="tabIcons[tab.id]" />
        <span class="tab-label">{{ tab.label }}</span>
      </button>
    </nav>

    <!-- 内容区 -->
    <main class="market-content">
      <!-- 专辑 -->
      <section
        v-show="activeTab === 'album'"
        ref="albumSection"
        class="album-section"
      >
        <div class="album-grid">
          <div
            v-for="item in albumItems"
            :key="item.id"
            class="album-card"
          >
            <div class="card-illust">
              <img :src="item.image" :alt="item.title" class="card-img">
              <div class="card-illust-gradient" />
              <div class="card-watermark">NagaAgent</div>
              <div class="card-banner">
                {{ item.bannerLabel ?? `剩余${item.daysLeft}天` }}
              </div>
            </div>
            <div class="card-info">
              <div class="card-title-main">{{ item.title }}</div>
              <div class="card-title-sub">{{ item.subtitle }}</div>
            </div>
            <div class="card-price-bar">
              <span class="price-icon">◆</span>
              <span class="price-num">{{ item.price }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 角色注册 -->
      <section v-show="activeTab === 'memory-skin'" ref="characterSectionRef" class="character-section" @click="onSectionClick">
        <div class="character-grid">
          <div
            v-for="char in characters"
            :key="char.id"
            :ref="(el: any) => setCardRef(char.id, el)"
            class="char-card"
            :class="{ expanded: expandedCard === char.id }"
            @click.stop="toggleCard(char.id)"
          >
            <img
              :src="char.portraitUrl"
              :alt="char.name"
              class="char-portrait-img"
            >
            <!-- 底部渐变遮罩 -->
            <div class="char-portrait-gradient" />
            <!-- 收缩态角色名 -->
            <div class="char-name-tag">
              {{ char.name }}
            </div>
            <!-- 展开态简介面板：绝对定位覆盖在卡片底部 -->
            <div class="char-desc-panel">
              <h3 class="char-desc-title">
                {{ char.name }}
              </h3>
              <p class="char-desc-text">
                {{ char.bio }}
              </p>
              <button
                type="button"
                class="char-apply-btn"
                @click.stop="applyCharacter(char.name)"
              >
                录入角色
              </button>
            </div>
          </div>

          <!-- 自定义角色卡 -->
          <div
            :ref="(el: any) => setCardRef('custom', el)"
            class="char-card custom-card"
            :class="{ expanded: expandedCard === 'custom' }"
            @click.stop="toggleCard('custom')"
          >
            <!-- 收缩态：+ 图标 + 文字 -->
            <div v-if="expandedCard !== 'custom'" class="custom-collapsed">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              <span class="custom-label">自定义角色</span>
            </div>
            <!-- 展开态：表单 -->
            <div v-else class="custom-form" @click.stop>
              <label class="custom-field">
                <span class="custom-field-label">角色名称</span>
                <input
                  v-model="customChar.name"
                  type="text"
                  class="custom-input"
                  placeholder="输入角色名称"
                >
              </label>
              <div class="custom-field">
                <span class="custom-field-label">L2D 模型</span>
                <input
                  ref="fileInputRef"
                  type="file"
                  accept=".model3.json"
                  style="display:none"
                  @change="onFileChange"
                >
                <button type="button" class="custom-file-btn" @click="triggerFileInput">
                  {{ customChar.modelFile ? customChar.modelFile.name : '选择 .model3.json 文件' }}
                </button>
              </div>
              <label class="custom-field custom-field-grow">
                <span class="custom-field-label">系统提示词</span>
                <textarea
                  v-model="customChar.prompt"
                  class="custom-textarea"
                  placeholder="输入系统提示词"
                />
              </label>
              <button
                type="button"
                class="char-apply-btn"
                :class="{ disabled: !customReady }"
                :disabled="!customReady"
                @click.stop="customReady && applyCustomCharacter()"
              >
                录入角色
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 其他标签占位 -->
      <section v-show="activeTab !== 'album' && activeTab !== 'memory-skin'" class="placeholder-section">
        <div class="placeholder-text">
          {{ tabs.find(t => t.id === activeTab)?.label }} — 敬请期待
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
/* ── 面板容器：窗口宽度 × 3/4 高度，垂直居中 ── */
.market-page {
  position: fixed;
  top: 12.5vh;         /* (100 - 75) / 2 = 12.5 → 垂直居中 */
  left: 0;
  right: 0;
  height: 75vh;
  z-index: 200;
  display: flex;
  flex-direction: column;
  background: rgba(15, 17, 21, 0.95);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(212, 175, 55, 0.3);
  overflow: hidden;
  /* 不设自定义 animation，由 Vue Router Transition (slide-in / slide-out) 接管 */
}

.market-page::before {
  content: '';
  position: absolute;
  top: 0;
  left: 10%;
  right: 10%;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(251, 191, 36, 0.9) 50%,
    transparent 100%
  );
  z-index: 1;
  pointer-events: none;
}

/* ── 顶部 Header ── */
.market-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 16px 8px;
  background: rgba(20, 22, 28, 0.5);
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  flex-shrink: 0;
  min-height: 48px;
  position: relative;
  z-index: 1;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.07);
  color: rgba(248, 250, 252, 0.75);
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.13);
  border-color: rgba(212, 175, 55, 0.45);
  color: #fff;
}

.market-title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: rgba(248, 250, 252, 0.95);
  font-family: 'Noto Serif SC', serif;
  letter-spacing: 0.05em;
}

/* ── Tab 栏 ── */
.market-tabs {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  width: 100%;
  flex-shrink: 0;
  background: rgba(12, 14, 18, 0.8);
  border-bottom: 1px solid rgba(148, 163, 184, 0.15);
  min-height: 56px;
}

.tab-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 8px 4px 10px;
  border: none;
  border-radius: 0;
  border-right: 1px solid rgba(148, 163, 184, 0.1);
  background: transparent;
  color: rgba(248, 250, 252, 0.45);
  font-size: 11px;
  cursor: pointer;
  transition: color 0.2s, background 0.2s;
  white-space: nowrap;
  position: relative;
  overflow: hidden;
}

.tab-btn:last-child {
  border-right: none;
}

.tab-btn:hover {
  color: rgba(248, 250, 252, 0.85);
  background: rgba(255, 255, 255, 0.05);
}

.tab-btn.active {
  color: rgba(251, 191, 36, 0.98);
  background: rgba(251, 191, 36, 0.08);
}

.tab-btn.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(
    90deg,
    transparent 10%,
    rgba(251, 191, 36, 0.9) 50%,
    transparent 90%
  );
  border-radius: 1px 1px 0 0;
}

.tab-btn.active .tab-icon-svg {
  color: rgba(251, 191, 36, 0.98);
}

.tab-icon-svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  color: inherit;
}

.tab-label {
  white-space: nowrap;
  line-height: 1;
}

/* ── 内容区 ── */
.market-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.album-section {
  flex: 1;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 14px 16px;
  cursor: grab;
  user-select: none;
}

.album-section::-webkit-scrollbar {
  height: 4px;
}

.album-section::-webkit-scrollbar-track {
  background: transparent;
}

.album-section::-webkit-scrollbar-thumb {
  background: rgba(212, 175, 55, 0.25);
  border-radius: 2px;
}

.album-section::-webkit-scrollbar-thumb:hover {
  background: rgba(212, 175, 55, 0.45);
}

.album-grid {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  gap: 12px;
  height: 100%;
  align-items: stretch;
  min-width: min-content;
}

/* ── 卡片 ── */
.album-card {
  position: relative;
  flex-shrink: 0;
  width: calc(75vh - 218px);
  min-width: 100px;
  height: 100%;
  border-radius: 10px;
  overflow: hidden;
  background: rgba(22, 26, 35, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.12);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  display: flex;
  flex-direction: column;
  cursor: pointer;
}

.album-card:hover {
  transform: translateY(-4px) scale(1.02);
  border-color: rgba(251, 191, 36, 0.5);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.5),
    0 0 20px rgba(251, 191, 36, 0.18);
}

/* 图片区域 */
.card-illust {
  position: relative;
  width: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.card-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

/* 底部渐变蒙版 */
.card-illust-gradient {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to bottom,
    transparent 50%,
    rgba(0, 0, 0, 0.75) 100%
  );
  pointer-events: none;
  z-index: 1;
}

/* 水印文字 */
.card-watermark {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) rotate(-30deg);
  font-size: 18px;
  font-weight: 900;
  font-family: 'Noto Serif SC', serif;
  color: rgba(255, 255, 255, 0.12);
  white-space: nowrap;
  pointer-events: none;
  user-select: none;
  z-index: 2;
  letter-spacing: 0.05em;
}

/* 剩余天数徽章 */
.card-banner {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 3px 8px;
  background: linear-gradient(
    135deg,
    rgba(220, 38, 38, 0.92),
    rgba(234, 88, 12, 0.88)
  );
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  border-radius: 10px;
  letter-spacing: 0.03em;
  z-index: 3;
  line-height: 1.4;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.4);
}

/* 卡片信息区 */
.card-info {
  padding: 8px 10px 6px;
  flex-shrink: 0;
}

.card-title-main {
  font-size: 13px;
  font-weight: 600;
  color: rgba(248, 250, 252, 0.95);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-title-sub {
  font-size: 11px;
  color: rgba(148, 163, 184, 0.65);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 价格栏 */
.card-price-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 7px 12px;
  background: linear-gradient(
    135deg,
    rgba(234, 179, 8, 0.95),
    rgba(217, 119, 6, 0.9)
  );
  flex-shrink: 0;
}

.price-icon {
  font-size: 11px;
  color: rgba(30, 41, 59, 0.85);
}

.price-num {
  font-size: 15px;
  font-weight: 800;
  color: #1e293b;
  letter-spacing: 0.02em;
}

/* ── 角色注册 ── */
.character-section {
  flex: 1;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 16px 24px;
  display: flex;
  align-items: stretch;
  min-height: 0;
  cursor: grab;
  user-select: none;
}

.character-section::-webkit-scrollbar {
  height: 4px;
}

.character-section::-webkit-scrollbar-track {
  background: transparent;
}

.character-section::-webkit-scrollbar-thumb {
  background: rgba(212, 175, 55, 0.25);
  border-radius: 2px;
}

.character-grid {
  display: flex;
  gap: 16px;
  height: 100%;
  align-items: stretch;
}

/* ── 角色卡：高度恒定，只变宽度，内部全部绝对定位 ── */
.char-card {
  position: relative;
  height: 100%;
  width: var(--collapsed-w, 130px);
  border-radius: 12px;
  overflow: hidden;
  background: rgba(22, 26, 35, 0.95);
  border: 1px solid rgba(148, 163, 184, 0.15);
  cursor: pointer;
  transition:
    width 0.5s cubic-bezier(0.33, 1, 0.68, 1),
    background 0.3s,
    border-color 0.3s,
    box-shadow 0.3s;
  flex-shrink: 0;
}

.char-card:hover {
  border-color: rgba(212, 175, 55, 0.4);
  box-shadow:
    0 4px 20px rgba(0, 0, 0, 0.4),
    0 0 12px rgba(212, 175, 55, 0.1);
}

.char-card.expanded {
  width: var(--expanded-w, 300px);
  background: transparent;
  border-color: transparent;
  box-shadow: none;
}

.char-portrait-img {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  height: 100%;
  width: auto;
  z-index: 0;
}

/* 立绘底部渐变遮罩 */
.char-portrait-gradient {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 80px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.75));
  pointer-events: none;
  z-index: 1;
}

/* 收缩态角色名：绝对定位在底部 */
.char-name-tag {
  position: absolute;
  bottom: 10px;
  left: 10px;
  font-size: 13px;
  font-weight: 600;
  color: rgba(248, 250, 252, 0.95);
  font-family: 'Noto Serif SC', serif;
  letter-spacing: 0.05em;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.8);
  z-index: 2;
  transition: opacity 0.3s;
}

.char-card.expanded .char-name-tag {
  opacity: 0;
}

/*
 * 展开态简介面板：绝对定位覆盖在卡片底部
 * 不占据任何布局空间，立绘区域高度始终不变
 */
.char-desc-panel {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 3;
  padding: 10px 12px 12px;
  background: linear-gradient(transparent, rgba(10, 12, 16, 0.92) 25%);
  display: flex;
  flex-direction: column;
  opacity: 0;
  transform: translateY(100%);
  transition:
    opacity 0.4s ease,
    transform 0.5s cubic-bezier(0.33, 1, 0.68, 1);
  pointer-events: none;
}

.char-card.expanded .char-desc-panel {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}

.char-desc-title {
  margin: 0 0 4px;
  font-size: 13px;
  font-weight: 700;
  color: rgba(251, 191, 36, 0.95);
  font-family: 'Noto Serif SC', serif;
  letter-spacing: 0.05em;
}

.char-desc-text {
  margin: 0;
  font-size: 11px;
  line-height: 1.5;
  color: rgba(203, 213, 225, 0.85);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ── "录入角色"按钮 ── */
.char-apply-btn {
  margin-top: 8px;
  padding: 4px 14px;
  font-size: 11px;
  font-weight: 600;
  color: rgba(251, 191, 36, 0.95);
  background: transparent;
  border: 1px solid rgba(251, 191, 36, 0.5);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 0.04em;
  align-self: center;
  flex-shrink: 0;
}

.char-apply-btn:hover {
  background: rgba(251, 191, 36, 0.12);
  border-color: rgba(251, 191, 36, 0.8);
}

.char-apply-btn.disabled {
  color: rgba(148, 163, 184, 0.45);
  border-color: rgba(148, 163, 184, 0.2);
  cursor: not-allowed;
}

.char-apply-btn.disabled:hover {
  background: transparent;
  border-color: rgba(148, 163, 184, 0.2);
}

/* ── 自定义角色卡 ── */
.custom-card {
  background: rgba(22, 26, 35, 0.95);
}

.custom-card.expanded {
  background: rgba(22, 26, 35, 0.95) !important;
  border-color: rgba(148, 163, 184, 0.15) !important;
  box-shadow: none !important;
}

.custom-collapsed {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 8px;
  color: rgba(248, 250, 252, 0.45);
  transition: color 0.2s;
}

.custom-card:hover .custom-collapsed {
  color: rgba(251, 191, 36, 0.8);
}

.custom-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.05em;
  writing-mode: vertical-rl;
  text-orientation: mixed;
}

.custom-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 12px;
  height: 100%;
  overflow-y: auto;
}

.custom-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.custom-field-grow {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.custom-field-label {
  font-size: 11px;
  font-weight: 600;
  color: rgba(251, 191, 36, 0.85);
  letter-spacing: 0.03em;
}

.custom-input {
  padding: 6px 8px;
  font-size: 12px;
  color: rgba(248, 250, 252, 0.9);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 6px;
  outline: none;
  transition: border-color 0.2s;
}

.custom-input:focus {
  border-color: rgba(251, 191, 36, 0.5);
}

.custom-file-btn {
  padding: 6px 8px;
  font-size: 11px;
  color: rgba(248, 250, 252, 0.7);
  background: rgba(255, 255, 255, 0.06);
  border: 1px dashed rgba(148, 163, 184, 0.25);
  border-radius: 6px;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.custom-file-btn:hover {
  border-color: rgba(251, 191, 36, 0.45);
  background: rgba(255, 255, 255, 0.08);
}

.custom-textarea {
  flex: 1;
  min-height: 60px;
  padding: 6px 8px;
  font-size: 12px;
  color: rgba(248, 250, 252, 0.9);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 6px;
  outline: none;
  resize: none;
  font-family: inherit;
  transition: border-color 0.2s;
}

.custom-textarea:focus {
  border-color: rgba(251, 191, 36, 0.5);
}

/* ── 占位区 ── */
.placeholder-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
}

.placeholder-text {
  font-size: 14px;
  color: rgba(148, 163, 184, 0.5);
}
</style>
