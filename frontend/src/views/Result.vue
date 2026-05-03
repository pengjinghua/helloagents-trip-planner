<template>
  <div class="result-atlas">
    <div class="result-header">
      <div class="result-header__intro">
        <a-button class="back-button" size="large" @click="goBack">
          ← 返回首页
        </a-button>
        <div v-if="tripPlan" class="result-header__copy">
          <div class="result-kicker">Travel Atlas Result</div>
          <h1>{{ tripPlan.city }} 行程图册</h1>
          <p>{{ dateRangeText }} · {{ dayCount }} 天 · {{ totalAttractions }} 个景点</p>
        </div>
      </div>

      <a-space size="middle" class="result-actions">
        <a-button v-if="!editMode" @click="toggleEditMode" type="default">
          ✏️ 编辑行程
        </a-button>
        <a-button v-else @click="saveChanges" type="primary">
          💾 保存修改
        </a-button>
        <a-button v-if="editMode" @click="cancelEdit" type="default">
          取消编辑
        </a-button>

        <a-dropdown v-if="!editMode">
          <template #overlay>
            <a-menu>
              <a-menu-item key="image" @click="exportAsImage">📷 导出为图片</a-menu-item>
              <a-menu-item key="pdf" @click="exportAsPDF">📄 导出为PDF</a-menu-item>
            </a-menu>
          </template>
          <a-button type="default">
            📥 导出行程 <DownOutlined />
          </a-button>
        </a-dropdown>
      </a-space>
    </div>

    <div v-if="tripPlan" class="content-shell">
      <aside class="content-rail">
        <div class="rail-card">
          <div class="rail-card__title">章节导航</div>
          <button
            v-for="item in navSections"
            :key="item.key"
            type="button"
            class="rail-link"
            :class="{ active: activeSection === item.key }"
            @click="scrollToSectionById(item.key)"
          >
            <span>{{ item.label }}</span>
            <span>{{ item.meta }}</span>
          </button>
        </div>

        <div class="rail-card">
          <div class="rail-card__title">每日行程</div>
          <button
            v-for="(day, index) in tripPlan.days"
            :key="`day-nav-${index}`"
            type="button"
            class="rail-day"
            @click="scrollToDay(index)"
          >
            <strong>第{{ day.day_index + 1 }}天</strong>
            <span>{{ day.date }}</span>
          </button>
        </div>
      </aside>

      <div class="main-content">
        <section id="overview" class="atlas-panel hero-panel">
          <div class="hero-panel__copy">
            <div class="result-kicker">Overview</div>
            <h2>{{ tripPlan.city }} · {{ dateRangeText }}</h2>
            <p>{{ tripPlan.overall_suggestions }}</p>
          </div>

          <div class="hero-stats">
            <div class="hero-stat">
              <span class="hero-stat__value">{{ dayCount }}</span>
              <span class="hero-stat__label">行程天数</span>
            </div>
            <div class="hero-stat">
              <span class="hero-stat__value">{{ totalAttractions }}</span>
              <span class="hero-stat__label">景点总数</span>
            </div>
            <div class="hero-stat">
              <span class="hero-stat__value">{{ totalMeals }}</span>
              <span class="hero-stat__label">餐饮安排</span>
            </div>
            <div class="hero-stat">
              <span class="hero-stat__value">{{ budgetSummary }}</span>
              <span class="hero-stat__label">预算概览</span>
            </div>
          </div>
        </section>

        <section class="top-grid">
          <div class="top-grid__stack">
            <section class="atlas-panel">
              <div class="panel-heading">
                <div>
                  <div class="result-kicker">Trip Summary</div>
                  <h3>行程概览</h3>
                </div>
              </div>
              <div class="overview-grid">
                <div class="overview-item">
                  <span class="overview-item__label">目的地</span>
                  <span class="overview-item__value">{{ tripPlan.city }}</span>
                </div>
                <div class="overview-item">
                  <span class="overview-item__label">日期</span>
                  <span class="overview-item__value">{{ tripPlan.start_date }} 至 {{ tripPlan.end_date }}</span>
                </div>
                <div class="overview-item">
                  <span class="overview-item__label">结果结构</span>
                  <span class="overview-item__value">地图、预算、逐日路线、天气、引用来源</span>
                </div>
              </div>
            </section>

            <section id="rag" class="atlas-panel">
              <div class="panel-heading">
                <div>
                  <div class="result-kicker">References</div>
                  <h3>引用来源</h3>
                </div>
                <span class="count-pill">{{ referenceCount }}</span>
              </div>

              <template v-if="Array.isArray(tripPlan.rag_references)">
                <a-alert
                  v-if="tripPlan.rag_references.length === 0"
                  type="info"
                  show-icon
                  message="本次未命中知识库内容"
                  description="如果你已经导入了知识库但这里仍为空，可能是内容与本次需求不相关，或本次生成使用了旧缓存。"
                />

                <div v-else class="reference-list">
                  <div v-for="item in tripPlan.rag_references" :key="`${item.title}-${item.uri}`" class="reference-item">
                    <div class="reference-item__top">
                      <strong>{{ item.title }}</strong>
                      <span class="reference-score">score {{ item.score.toFixed(3) }}</span>
                    </div>
                    <div class="reference-meta">{{ item.source_type }}</div>
                    <div class="reference-uri">{{ item.uri }}</div>
                  </div>
                </div>
              </template>

              <a-alert
                v-else
                type="warning"
                show-icon
                message="当前行程未包含引用信息"
                description="这通常说明结果页里是旧版本 sessionStorage 数据。请返回首页重新生成。"
              />
            </section>

            <section id="budget" v-if="tripPlan.budget" class="atlas-panel budget-panel">
              <div class="panel-heading">
                <div>
                  <div class="result-kicker">Budget</div>
                  <h3>预算明细</h3>
                </div>
              </div>

              <div class="budget-grid">
                <div class="budget-item">
                  <span class="budget-item__label">景点门票</span>
                  <span class="budget-item__value">¥{{ tripPlan.budget.total_attractions }}</span>
                </div>
                <div class="budget-item">
                  <span class="budget-item__label">酒店住宿</span>
                  <span class="budget-item__value">¥{{ tripPlan.budget.total_hotels }}</span>
                </div>
                <div class="budget-item">
                  <span class="budget-item__label">餐饮费用</span>
                  <span class="budget-item__value">¥{{ tripPlan.budget.total_meals }}</span>
                </div>
                <div class="budget-item">
                  <span class="budget-item__label">交通费用</span>
                  <span class="budget-item__value">¥{{ tripPlan.budget.total_transportation }}</span>
                </div>
              </div>

              <div class="budget-total">
                <span class="total-label">预估总费用</span>
                <span class="total-value">¥{{ tripPlan.budget.total }}</span>
              </div>
            </section>
          </div>

          <section id="map" class="atlas-panel map-panel">
            <div class="panel-heading">
              <div>
                <div class="result-kicker">Map View</div>
                <h3>景点地图</h3>
              </div>
            </div>
            <div id="amap-container" class="map-canvas"></div>
          </section>
        </section>

        <section class="atlas-panel days-panel">
          <div class="panel-heading">
            <div>
              <div class="result-kicker">Day by Day</div>
              <h3>每日行程</h3>
            </div>
          </div>

          <a-collapse v-model:activeKey="activeDays" accordion>
            <a-collapse-panel
              v-for="(day, index) in tripPlan.days"
              :key="index"
              :id="`day-${index}`"
            >
              <template #header>
                <div class="day-header">
                  <div>
                    <span class="day-title">第{{ day.day_index + 1 }}天</span>
                    <span class="day-date">{{ day.date }}</span>
                  </div>
                  <span class="day-badge">{{ day.attractions.length }} 个景点</span>
                </div>
              </template>

              <div class="day-meta-card">
                <div class="day-meta-item">
                  <span>行程描述</span>
                  <strong>{{ day.description }}</strong>
                </div>
                <div class="day-meta-item">
                  <span>交通方式</span>
                  <strong>{{ day.transportation }}</strong>
                </div>
                <div class="day-meta-item">
                  <span>住宿策略</span>
                  <strong>{{ day.accommodation }}</strong>
                </div>
              </div>

              <a-divider orientation="left">景点安排</a-divider>
              <a-list
                :data-source="day.attractions"
                :grid="{ gutter: 16, column: 2 }"
              >
                <template #renderItem="{ item, index }">
                  <a-list-item>
                    <a-card :title="item.name" size="small" class="attraction-card">
                      <template #extra v-if="editMode">
                        <a-space>
                          <a-button
                            size="small"
                            @click="moveAttraction(day.day_index, index, 'up')"
                            :disabled="index === 0"
                          >
                            ↑
                          </a-button>
                          <a-button
                            size="small"
                            @click="moveAttraction(day.day_index, index, 'down')"
                            :disabled="index === day.attractions.length - 1"
                          >
                            ↓
                          </a-button>
                          <a-button
                            size="small"
                            danger
                            @click="deleteAttraction(day.day_index, index)"
                          >
                            删除
                          </a-button>
                        </a-space>
                      </template>

                      <div class="attraction-image-wrapper">
                        <img
                          :src="getAttractionImage(item.name, index)"
                          :alt="item.name"
                          class="attraction-image"
                          @error="handleImageError"
                        />
                        <div class="attraction-badge">
                          <span class="badge-number">{{ index + 1 }}</span>
                        </div>
                        <div v-if="item.ticket_price" class="price-tag">
                          ¥{{ item.ticket_price }}
                        </div>
                      </div>

                      <div v-if="editMode">
                        <p><strong>地址:</strong></p>
                        <a-input v-model:value="item.address" size="small" style="margin-bottom: 8px" />

                        <p><strong>游览时长(分钟):</strong></p>
                        <a-input-number v-model:value="item.visit_duration" :min="10" :max="480" size="small" style="width: 100%; margin-bottom: 8px" />

                        <p><strong>描述:</strong></p>
                        <a-textarea v-model:value="item.description" :rows="2" size="small" style="margin-bottom: 8px" />
                      </div>

                      <div v-else class="attraction-copy">
                        <p><strong>地址:</strong> {{ item.address }}</p>
                        <p><strong>游览时长:</strong> {{ item.visit_duration }} 分钟</p>
                        <p><strong>描述:</strong> {{ item.description }}</p>
                        <p v-if="item.rating"><strong>评分:</strong> {{ item.rating }} ★</p>
                      </div>
                    </a-card>
                  </a-list-item>
                </template>
              </a-list>

              <a-divider v-if="day.hotel" orientation="left">住宿推荐</a-divider>
              <a-card v-if="day.hotel" size="small" class="hotel-card">
                <template #title>
                  <span class="hotel-title">{{ day.hotel.name }}</span>
                </template>
                <a-descriptions :column="2" size="small">
                  <a-descriptions-item label="地址">{{ day.hotel.address }}</a-descriptions-item>
                  <a-descriptions-item label="类型">{{ day.hotel.type }}</a-descriptions-item>
                  <a-descriptions-item label="价格范围">{{ day.hotel.price_range }}</a-descriptions-item>
                  <a-descriptions-item label="评分">{{ day.hotel.rating }} ★</a-descriptions-item>
                  <a-descriptions-item label="距离" :span="2">{{ day.hotel.distance }}</a-descriptions-item>
                </a-descriptions>
              </a-card>

              <a-divider orientation="left">餐饮安排</a-divider>
              <a-descriptions :column="1" bordered size="small">
                <a-descriptions-item
                  v-for="meal in day.meals"
                  :key="meal.type"
                  :label="getMealLabel(meal.type)"
                >
                  {{ meal.name }}
                  <span v-if="meal.description"> - {{ meal.description }}</span>
                </a-descriptions-item>
              </a-descriptions>
            </a-collapse-panel>
          </a-collapse>
        </section>

        <section id="weather" v-if="tripPlan.weather_info && tripPlan.weather_info.length > 0" class="atlas-panel">
          <div class="panel-heading">
            <div>
              <div class="result-kicker">Weather</div>
              <h3>天气信息</h3>
            </div>
          </div>

          <a-list
            :data-source="tripPlan.weather_info"
            :grid="{ gutter: 16, column: 3 }"
          >
            <template #renderItem="{ item }">
              <a-list-item>
                <a-card size="small" class="weather-card">
                  <div class="weather-date">{{ item.date }}</div>
                  <div class="weather-info-row">
                    <span class="weather-icon">☀️</span>
                    <div>
                      <div class="weather-label">白天</div>
                      <div class="weather-value">{{ item.day_weather }} {{ item.day_temp }}°C</div>
                    </div>
                  </div>
                  <div class="weather-info-row">
                    <span class="weather-icon">🌙</span>
                    <div>
                      <div class="weather-label">夜间</div>
                      <div class="weather-value">{{ item.night_weather }} {{ item.night_temp }}°C</div>
                    </div>
                  </div>
                  <div class="weather-wind">💨 {{ item.wind_direction }} {{ item.wind_power }}</div>
                </a-card>
              </a-list-item>
            </template>
          </a-list>
        </section>
      </div>
    </div>

    <a-empty v-else description="没有找到旅行计划数据" class="empty-state">
      <template #image>
        <div style="font-size: 72px;">🗺️</div>
      </template>
      <template #description>
        <span style="color: #6c7d83;">暂无旅行计划数据，请先返回首页创建行程。</span>
      </template>
      <a-button type="primary" @click="goBack">返回首页</a-button>
    </a-empty>

    <a-back-top :visibility-height="300">
      <div class="back-top-button">↑</div>
    </a-back-top>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { DownOutlined } from '@ant-design/icons-vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import type { TripPlan } from '@/types'

const router = useRouter()
const tripPlan = ref<TripPlan | null>(null)
const editMode = ref(false)
const originalPlan = ref<TripPlan | null>(null)
const attractionPhotos = ref<Record<string, string>>({})
const activeSection = ref('overview')
const activeDays = ref<number[]>([0])
let map: any = null

const dayCount = computed(() => tripPlan.value?.days.length ?? 0)
const totalAttractions = computed(() => tripPlan.value?.days.reduce((sum, day) => sum + day.attractions.length, 0) ?? 0)
const totalMeals = computed(() => tripPlan.value?.days.reduce((sum, day) => sum + day.meals.length, 0) ?? 0)
const referenceCount = computed(() => tripPlan.value?.rag_references?.length ?? 0)
const budgetSummary = computed(() => tripPlan.value?.budget ? `¥${tripPlan.value.budget.total}` : '待生成')
const dateRangeText = computed(() => {
  if (!tripPlan.value) {
    return ''
  }
  return `${tripPlan.value.start_date} 至 ${tripPlan.value.end_date}`
})

const navSections = computed(() => {
  const base = [
    { key: 'overview', label: '总览', meta: `${dayCount.value} 天` },
    { key: 'rag', label: '引用来源', meta: `${referenceCount.value} 条` },
    { key: 'map', label: '地图', meta: '景点分布' }
  ]

  if (tripPlan.value?.budget) {
    base.splice(2, 0, { key: 'budget', label: '预算', meta: budgetSummary.value })
  }

  if (tripPlan.value?.weather_info?.length) {
    base.push({ key: 'weather', label: '天气', meta: `${tripPlan.value.weather_info.length} 天` })
  }

  return base
})

onMounted(async () => {
  const data = sessionStorage.getItem('tripPlan')
  if (data) {
    tripPlan.value = JSON.parse(data)
    await loadAttractionPhotos()
    await nextTick()
    initMap()
  }
})

const goBack = () => {
  router.push('/')
}

const scrollToSectionById = (id: string) => {
  activeSection.value = id
  const element = document.getElementById(id)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

const scrollToDay = (index: number) => {
  activeDays.value = [index]
  scrollToSectionById(`day-${index}`)
}

const toggleEditMode = () => {
  editMode.value = true
  originalPlan.value = JSON.parse(JSON.stringify(tripPlan.value))
  message.info('进入编辑模式')
}

const saveChanges = () => {
  editMode.value = false
  if (tripPlan.value) {
    sessionStorage.setItem('tripPlan', JSON.stringify(tripPlan.value))
  }
  message.success('修改已保存')

  if (map) {
    map.destroy()
  }
  nextTick(() => {
    initMap()
  })
}

const cancelEdit = () => {
  if (originalPlan.value) {
    tripPlan.value = JSON.parse(JSON.stringify(originalPlan.value))
  }
  editMode.value = false
  message.info('已取消编辑')
}

const deleteAttraction = (dayIndex: number, attrIndex: number) => {
  if (!tripPlan.value) return

  const day = tripPlan.value.days[dayIndex]
  if (day.attractions.length <= 1) {
    message.warning('每天至少需要保留一个景点')
    return
  }

  day.attractions.splice(attrIndex, 1)
  message.success('景点已删除')
}

const moveAttraction = (dayIndex: number, attrIndex: number, direction: 'up' | 'down') => {
  if (!tripPlan.value) return

  const day = tripPlan.value.days[dayIndex]
  const attractions = day.attractions

  if (direction === 'up' && attrIndex > 0) {
    [attractions[attrIndex], attractions[attrIndex - 1]] = [attractions[attrIndex - 1], attractions[attrIndex]]
  } else if (direction === 'down' && attrIndex < attractions.length - 1) {
    [attractions[attrIndex], attractions[attrIndex + 1]] = [attractions[attrIndex + 1], attractions[attrIndex]]
  }
}

const getMealLabel = (type: string): string => {
  const labels: Record<string, string> = {
    breakfast: '早餐',
    lunch: '午餐',
    dinner: '晚餐',
    snack: '小吃'
  }
  return labels[type] || type
}

const loadAttractionPhotos = async () => {
  if (!tripPlan.value) return

  const apiBase = 'http://localhost:8000'
  const city = tripPlan.value.city || ''
  const promises: Promise<void>[] = []

  tripPlan.value.days.forEach(day => {
    day.attractions.forEach(attraction => {
      const url = `${apiBase}/api/poi/photo?name=${encodeURIComponent(attraction.name)}&city=${encodeURIComponent(city)}`
      const promise = fetch(url)
        .then(res => res.json())
        .then(data => {
          if (data.success && data.data.photo_url) {
            attractionPhotos.value[attraction.name] = data.data.photo_url
          }
        })
        .catch(err => {
          console.error(`获取${attraction.name}图片失败:`, err)
        })

      promises.push(promise)
    })
  })

  await Promise.all(promises)
}

const getAttractionImage = (name: string, index: number): string => {
  if (attractionPhotos.value[name]) {
    return attractionPhotos.value[name]
  }

  const colors = [
    { start: '#1f5a5a', end: '#2f8b81' },
    { start: '#d46d3d', end: '#f3a55f' },
    { start: '#446d8c', end: '#7cb1d8' },
    { start: '#4f7d5b', end: '#9ab67f' },
    { start: '#8c4d3f', end: '#d18c74' }
  ]
  const colorIndex = index % colors.length
  const { start, end } = colors[colorIndex]

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
    <defs>
      <linearGradient id="grad${index}" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:${start};stop-opacity:1" />
        <stop offset="100%" style="stop-color:${end};stop-opacity:1" />
      </linearGradient>
    </defs>
    <rect width="400" height="300" fill="url(#grad${index})"/>
    <text x="50%" y="46%" dominant-baseline="middle" text-anchor="middle" font-family="Georgia, serif" font-size="24" font-weight="bold" fill="white">${name}</text>
    <text x="50%" y="60%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="12" letter-spacing="3" fill="rgba(255,255,255,0.88)">TRAVEL ATLAS</text>
  </svg>`

  return `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(svg)))}`
}

const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect width="400" height="300" fill="%23ece5da"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="18" fill="%236c7d83"%3E图片加载失败%3C/text%3E%3C/svg%3E'
}

const exportAsImage = async () => {
  try {
    message.loading({ content: '正在生成图片...', key: 'export', duration: 0 })

    const element = document.querySelector('.main-content') as HTMLElement
    if (!element) {
      throw new Error('未找到内容元素')
    }

    const exportContainer = document.createElement('div')
    exportContainer.style.width = element.offsetWidth + 'px'
    exportContainer.style.backgroundColor = '#f4ede2'
    exportContainer.style.padding = '20px'
    exportContainer.innerHTML = element.innerHTML

    const mapContainer = document.getElementById('amap-container')
    if (mapContainer && map) {
      const mapCanvas = mapContainer.querySelector('canvas')
      if (mapCanvas) {
        const mapSnapshot = mapCanvas.toDataURL('image/png')
        const exportMapContainer = exportContainer.querySelector('#amap-container')
        if (exportMapContainer) {
          exportMapContainer.innerHTML = `<img src="${mapSnapshot}" style="width:100%;height:100%;object-fit:cover;" />`
        }
      }
    }

    const cards = exportContainer.querySelectorAll('.ant-card')
    cards.forEach((card) => {
      const cardEl = card as HTMLElement
      cardEl.className = ''
      cardEl.style.setProperty('background-color', '#fffaf3')
      cardEl.style.setProperty('border-radius', '20px')
      cardEl.style.setProperty('box-shadow', '0 10px 22px rgba(0, 0, 0, 0.08)')
      cardEl.style.setProperty('margin-bottom', '20px')
      cardEl.style.setProperty('overflow', 'hidden')
    })

    const cardBodies = exportContainer.querySelectorAll('.ant-card-body')
    cardBodies.forEach((body) => {
      const bodyEl = body as HTMLElement
      bodyEl.style.setProperty('background-color', '#fffaf3')
      bodyEl.style.setProperty('padding', '24px')
    })

    exportContainer.style.position = 'absolute'
    exportContainer.style.left = '-9999px'
    document.body.appendChild(exportContainer)

    const canvas = await html2canvas(exportContainer, {
      backgroundColor: '#f4ede2',
      scale: 2,
      logging: false,
      useCORS: true,
      allowTaint: true
    })

    document.body.removeChild(exportContainer)

    const link = document.createElement('a')
    link.download = `旅行计划_${tripPlan.value?.city}_${new Date().getTime()}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()

    message.success({ content: '图片导出成功!', key: 'export' })
  } catch (error: any) {
    console.error('导出图片失败:', error)
    message.error({ content: `导出图片失败: ${error.message}`, key: 'export' })
  }
}

const exportAsPDF = async () => {
  try {
    message.loading({ content: '正在生成PDF...', key: 'export', duration: 0 })

    const element = document.querySelector('.main-content') as HTMLElement
    if (!element) {
      throw new Error('未找到内容元素')
    }

    const exportContainer = document.createElement('div')
    exportContainer.style.width = element.offsetWidth + 'px'
    exportContainer.style.backgroundColor = '#f4ede2'
    exportContainer.style.padding = '20px'
    exportContainer.innerHTML = element.innerHTML

    const mapContainer = document.getElementById('amap-container')
    if (mapContainer && map) {
      const mapCanvas = mapContainer.querySelector('canvas')
      if (mapCanvas) {
        const mapSnapshot = mapCanvas.toDataURL('image/png')
        const exportMapContainer = exportContainer.querySelector('#amap-container')
        if (exportMapContainer) {
          exportMapContainer.innerHTML = `<img src="${mapSnapshot}" style="width:100%;height:100%;object-fit:cover;" />`
        }
      }
    }

    exportContainer.style.position = 'absolute'
    exportContainer.style.left = '-9999px'
    document.body.appendChild(exportContainer)

    const canvas = await html2canvas(exportContainer, {
      backgroundColor: '#f4ede2',
      scale: 2,
      logging: false,
      useCORS: true,
      allowTaint: true
    })

    document.body.removeChild(exportContainer)

    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4'
    })

    const imgWidth = 210
    const imgHeight = (canvas.height * imgWidth) / canvas.width
    let heightLeft = imgHeight
    let position = 0

    pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
    heightLeft -= 297

    while (heightLeft > 0) {
      position = heightLeft - imgHeight
      pdf.addPage()
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
      heightLeft -= 297
    }

    pdf.save(`旅行计划_${tripPlan.value?.city}_${new Date().getTime()}.pdf`)
    message.success({ content: 'PDF导出成功!', key: 'export' })
  } catch (error: any) {
    console.error('导出PDF失败:', error)
    message.error({ content: `导出PDF失败: ${error.message}`, key: 'export' })
  }
}

const initMap = async () => {
  try {
    if (map) {
      map.destroy()
    }

    const AMap = await AMapLoader.load({
      key: import.meta.env.VITE_AMAP_WEB_JS_KEY,
      version: '2.0',
      plugins: ['AMap.Marker', 'AMap.Polyline', 'AMap.InfoWindow']
    })

    map = new AMap.Map('amap-container', {
      zoom: 12,
      center: [116.397128, 39.916527],
      viewMode: '3D'
    })

    addAttractionMarkers(AMap)
  } catch (error) {
    console.error('地图加载失败:', error)
    message.error('地图加载失败')
  }
}

const addAttractionMarkers = (AMap: any) => {
  if (!tripPlan.value) return

  const markers: any[] = []
  const allAttractions: any[] = []

  tripPlan.value.days.forEach((day, dayIndex) => {
    day.attractions.forEach((attraction, attrIndex) => {
      if (attraction.location && attraction.location.longitude && attraction.location.latitude) {
        allAttractions.push({
          ...attraction,
          dayIndex,
          attrIndex
        })
      }
    })
  })

  allAttractions.forEach((attraction, index) => {
    const marker = new AMap.Marker({
      position: [attraction.location.longitude, attraction.location.latitude],
      title: attraction.name,
      label: {
        content: `<div style="background:#1f5a5a;color:white;padding:4px 8px;border-radius:12px;font-size:12px;">${index + 1}</div>`,
        offset: new AMap.Pixel(0, -30)
      }
    })

    const infoWindow = new AMap.InfoWindow({
      content: `
        <div style="padding: 12px; max-width: 260px;">
          <h4 style="margin: 0 0 8px 0;">${attraction.name}</h4>
          <p style="margin: 4px 0;"><strong>地址:</strong> ${attraction.address}</p>
          <p style="margin: 4px 0;"><strong>游览时长:</strong> ${attraction.visit_duration} 分钟</p>
          <p style="margin: 4px 0;"><strong>描述:</strong> ${attraction.description}</p>
          <p style="margin: 4px 0; color: #1f5a5a;"><strong>第${attraction.dayIndex + 1}天 · 景点${attraction.attrIndex + 1}</strong></p>
        </div>
      `,
      offset: new AMap.Pixel(0, -30)
    })

    marker.on('click', () => {
      infoWindow.open(map, marker.getPosition())
    })

    markers.push(marker)
  })

  map.add(markers)

  if (allAttractions.length > 0) {
    map.setFitView(markers)
  }

  drawRoutes(AMap, allAttractions)
}

const drawRoutes = (AMap: any, attractions: any[]) => {
  if (attractions.length < 2) return

  const dayGroups: Record<number, any[]> = {}
  attractions.forEach(attr => {
    if (!dayGroups[attr.dayIndex]) {
      dayGroups[attr.dayIndex] = []
    }
    dayGroups[attr.dayIndex].push(attr)
  })

  Object.values(dayGroups).forEach((dayAttractions: any[]) => {
    if (dayAttractions.length < 2) return

    const path = dayAttractions.map((attr: any) => [
      attr.location.longitude,
      attr.location.latitude
    ])

    const polyline = new AMap.Polyline({
      path,
      strokeColor: '#d46d3d',
      strokeWeight: 4,
      strokeOpacity: 0.85,
      strokeStyle: 'solid',
      showDir: true
    })

    map.add(polyline)
  })
}
</script>

<style scoped>
.result-atlas {
  display: grid;
  gap: 22px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
}

.result-header__intro {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.result-kicker {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--atlas-deep);
}

.result-header__copy h1,
.panel-heading h3,
.hero-panel__copy h2 {
  font-family: Georgia, 'Times New Roman', 'Songti SC', serif;
}

.result-header__copy h1 {
  margin: 8px 0 6px;
  font-size: 40px;
  letter-spacing: -0.04em;
}

.result-header__copy p {
  margin: 0;
  color: var(--atlas-muted);
}

.back-button {
  border-radius: 999px;
  border-color: rgba(21, 49, 58, 0.14);
}

.result-actions :deep(.ant-btn) {
  border-radius: 999px;
}

.content-shell {
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr);
  gap: 24px;
}

.content-rail {
  position: sticky;
  top: 18px;
  align-self: start;
  display: grid;
  gap: 16px;
}

.rail-card,
.atlas-panel {
  border-radius: 26px;
  background: linear-gradient(180deg, rgba(255, 252, 247, 0.95), rgba(251, 245, 236, 0.92));
  border: 1px solid rgba(21, 49, 58, 0.1);
  box-shadow: var(--atlas-shadow);
}

.rail-card {
  padding: 18px;
}

.rail-card__title {
  font-size: 13px;
  font-weight: 700;
  color: var(--atlas-muted);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  margin-bottom: 12px;
}

.rail-link,
.rail-day {
  width: 100%;
  text-align: left;
  border: 1px solid rgba(21, 49, 58, 0.08);
  background: rgba(255, 255, 255, 0.76);
  border-radius: 18px;
  padding: 12px 14px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.rail-link + .rail-link,
.rail-day + .rail-day {
  margin-top: 10px;
}

.rail-link {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: var(--atlas-ink);
}

.rail-link span:last-child,
.rail-day span {
  color: var(--atlas-muted);
  font-size: 12px;
}

.rail-link:hover,
.rail-day:hover,
.rail-link.active {
  transform: translateY(-1px);
  border-color: rgba(31, 90, 90, 0.22);
  box-shadow: 0 14px 24px rgba(31, 90, 90, 0.08);
}

.rail-link.active {
  background: linear-gradient(135deg, rgba(228, 240, 236, 0.98), rgba(255, 255, 255, 0.96));
}

.rail-day strong {
  display: block;
  margin-bottom: 4px;
}

.main-content {
  min-width: 0;
  display: grid;
  gap: 22px;
}

.atlas-panel {
  padding: 24px;
}

.hero-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 24px;
  overflow: hidden;
  position: relative;
}

.hero-panel::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 12% 24%, rgba(31, 90, 90, 0.08), transparent 18%),
    radial-gradient(circle at 84% 22%, rgba(212, 109, 61, 0.1), transparent 18%);
}

.hero-panel__copy,
.hero-stats {
  position: relative;
  z-index: 1;
}

.hero-panel__copy h2 {
  margin: 12px 0 10px;
  font-size: 36px;
  letter-spacing: -0.04em;
}

.hero-panel__copy p {
  margin: 0;
  line-height: 1.8;
  color: var(--atlas-muted);
}

.hero-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.hero-stat {
  padding: 18px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(21, 49, 58, 0.08);
}

.hero-stat__value {
  display: block;
  color: var(--atlas-deep);
  font-size: 28px;
  font-weight: 800;
  margin-bottom: 4px;
}

.hero-stat__label {
  color: var(--atlas-muted);
  font-size: 13px;
}

.top-grid {
  display: grid;
  grid-template-columns: 420px minmax(0, 1fr);
  gap: 22px;
}

.top-grid__stack {
  display: grid;
  gap: 22px;
}

.panel-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 18px;
}

.panel-heading h3 {
  margin: 8px 0 0;
  font-size: 28px;
}

.count-pill {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(31, 90, 90, 0.08);
  color: var(--atlas-deep);
  font-size: 12px;
  font-weight: 700;
}

.overview-grid {
  display: grid;
  gap: 12px;
}

.overview-item {
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(21, 49, 58, 0.08);
}

.overview-item__label {
  display: block;
  color: var(--atlas-muted);
  font-size: 12px;
  margin-bottom: 6px;
}

.overview-item__value {
  display: block;
  line-height: 1.7;
}

.reference-list {
  display: grid;
  gap: 12px;
}

.reference-item {
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(21, 49, 58, 0.08);
}

.reference-item__top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
}

.reference-meta,
.reference-uri,
.reference-score {
  color: var(--atlas-muted);
  font-size: 13px;
}

.reference-meta {
  margin-top: 6px;
}

.reference-uri {
  margin-top: 8px;
  word-break: break-all;
  line-height: 1.6;
}

.budget-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.budget-item {
  padding: 16px;
  text-align: center;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(21, 49, 58, 0.08);
}

.budget-item__label {
  display: block;
  color: var(--atlas-muted);
  font-size: 13px;
  margin-bottom: 8px;
}

.budget-item__value {
  color: var(--atlas-accent);
  font-size: 24px;
  font-weight: 800;
}

.budget-total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(135deg, var(--atlas-deep), var(--atlas-accent));
  color: #fffdf8;
}

.total-label {
  font-weight: 700;
}

.total-value {
  font-size: 28px;
  font-weight: 800;
}

.map-panel {
  min-height: 560px;
}

.map-canvas {
  width: 100%;
  height: 470px;
  border-radius: 20px;
  overflow: hidden;
}

.days-panel :deep(.ant-collapse) {
  border: none;
  background: transparent;
}

.days-panel :deep(.ant-collapse-item) {
  margin-bottom: 16px;
  border: 1px solid rgba(21, 49, 58, 0.08);
  border-radius: 20px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.68);
}

.days-panel :deep(.ant-collapse-header) {
  padding: 18px 20px !important;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.76), rgba(244, 236, 222, 0.92));
}

.days-panel :deep(.ant-collapse-content) {
  border-top: 1px solid rgba(21, 49, 58, 0.08);
}

.days-panel :deep(.ant-collapse-content-box) {
  padding: 20px;
}

.day-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.day-title {
  display: block;
  font-size: 20px;
  font-weight: 700;
}

.day-date {
  display: block;
  margin-top: 4px;
  color: var(--atlas-muted);
}

.day-badge {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(31, 90, 90, 0.08);
  color: var(--atlas-deep);
  font-size: 12px;
  font-weight: 700;
}

.day-meta-card {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 22px;
}

.day-meta-item {
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(21, 49, 58, 0.08);
}

.day-meta-item span {
  display: block;
  color: var(--atlas-muted);
  font-size: 12px;
  margin-bottom: 8px;
}

.day-meta-item strong {
  line-height: 1.7;
}

.attraction-card :deep(.ant-card-head) {
  background: linear-gradient(135deg, #1f5a5a, #2f7b73);
  color: #fffdf8 !important;
  border-radius: 18px 18px 0 0;
}

.attraction-card :deep(.ant-card-head-title) {
  color: #fffdf8 !important;
}

.attraction-card :deep(.ant-card) {
  border-radius: 18px;
}

.attraction-image-wrapper {
  position: relative;
  margin-bottom: 12px;
  border-radius: 14px;
  overflow: hidden;
}

.attraction-image {
  width: 100%;
  height: 220px;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.attraction-image-wrapper:hover .attraction-image {
  transform: scale(1.04);
}

.attraction-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(20, 49, 58, 0.84);
  color: #fffdf8;
  font-weight: 700;
}

.price-tag {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(212, 109, 61, 0.92);
  color: #fffdf8;
  font-size: 13px;
  font-weight: 700;
}

.attraction-copy p {
  line-height: 1.7;
}

.hotel-card {
  background: linear-gradient(135deg, rgba(230, 242, 242, 0.94), rgba(244, 248, 246, 0.98));
}

.hotel-card :deep(.ant-card-head) {
  background: linear-gradient(135deg, #446d8c, #6890af);
}

.hotel-title {
  color: #fffdf8;
}

.weather-card {
  background: linear-gradient(135deg, rgba(234, 244, 242, 0.96), rgba(255, 255, 255, 0.96));
  border: none !important;
}

.weather-date {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 12px;
  text-align: center;
  color: var(--atlas-deep);
}

.weather-info-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.weather-icon {
  font-size: 24px;
}

.weather-label {
  color: var(--atlas-muted);
  font-size: 12px;
}

.weather-value {
  font-weight: 700;
}

.weather-wind {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(21, 49, 58, 0.1);
  color: var(--atlas-deep);
}

.back-top-button {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--atlas-deep), var(--atlas-accent));
  color: #fffdf8;
  font-size: 22px;
  box-shadow: 0 14px 28px rgba(31, 90, 90, 0.18);
}

.empty-state {
  padding-top: 80px;
}

@media (max-width: 1280px) {
  .content-shell,
  .top-grid,
  .hero-panel {
    grid-template-columns: minmax(0, 1fr);
  }

  .content-rail {
    position: static;
  }
}

@media (max-width: 900px) {
  .result-header,
  .result-header__intro {
    flex-direction: column;
  }

  .day-meta-card,
  .budget-grid,
  .hero-stats {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .result-header__copy h1 {
    font-size: 32px;
  }

  .atlas-panel {
    padding: 18px;
  }

  .map-canvas {
    height: 360px;
  }
}
</style>
