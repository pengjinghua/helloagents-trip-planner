<template>
  <div class="home-atlas">
    <section class="hero-board">
      <div class="hero-board__map"></div>
      <div class="hero-board__grid">
        <div class="hero-copy">
          <div class="eyebrow">Editorial Travel Atlas</div>
          <h1 class="hero-title">
            把一次旅行
            <span>整理成可以真正出发的路线手册</span>
          </h1>
          <p class="hero-description">
            这不是简单的景点推荐器。它会基于你的时间窗口、出行偏好、住宿倾向、补充要求和知识资料，
            生成更接近真实用户使用场景的智能旅行方案。
          </p>

          <div class="hero-stats">
            <div class="hero-stat">
              <span class="hero-stat__value">{{ heroDays }}</span>
              <span class="hero-stat__label">自动识别旅行天数</span>
            </div>
            <div class="hero-stat">
              <span class="hero-stat__value">{{ selectedPreferenceLabels.length || 0 }}</span>
              <span class="hero-stat__label">已选择兴趣主题</span>
            </div>
            <div class="hero-stat">
              <span class="hero-stat__value">{{ knowledgeFeed.length }}</span>
              <span class="hero-stat__label">已接入知识资料</span>
            </div>
          </div>

          <div class="scenario-strip">
            <div class="strip-title">快捷情境</div>
            <div class="scenario-grid">
              <button
                v-for="preset in presetTrips"
                :key="preset.name"
                type="button"
                class="scenario-card"
                @click="applyPreset(preset)"
              >
                <div class="scenario-card__top">
                  <span class="scenario-card__icon">{{ preset.icon }}</span>
                  <span class="scenario-card__duration">{{ preset.duration }}天</span>
                </div>
                <div class="scenario-card__name">{{ preset.name }}</div>
                <div class="scenario-card__description">{{ preset.description }}</div>
              </button>
            </div>
          </div>
        </div>

        <div class="hero-visual">
          <div class="hero-brief">
            <div class="hero-brief__header">
              <div>
                <div class="hero-brief__kicker">Current Brief</div>
                <div class="hero-brief__city">{{ formData.city || '等待输入目的地' }}</div>
                <div class="hero-brief__meta">{{ travelDateText }}</div>
              </div>
            </div>

            <div class="hero-brief__tags">
              <span class="brief-tag">{{ formData.transportation }}</span>
              <span class="brief-tag">{{ formData.accommodation }}</span>
              <span class="brief-tag">{{ formData.travel_days }} 天</span>
            </div>

            <div class="hero-brief__section">
              <div class="section-small-title">本次会优先整理</div>
              <div class="focus-list">
                <div v-for="item in generatedFocus" :key="item" class="focus-item">{{ item }}</div>
              </div>
            </div>

            <div class="hero-brief__section">
              <div class="section-small-title">结果页交付内容</div>
              <div class="delivery-list">
                <div v-for="item in deliveryItems" :key="item.title" class="delivery-item">
                  <span class="delivery-item__icon">{{ item.icon }}</span>
                  <div>
                    <div class="delivery-item__title">{{ item.title }}</div>
                    <div class="delivery-item__description">{{ item.description }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="planner-grid">
      <div class="planner-main planner-main--full">
        <a-card :bordered="false" class="atlas-card planner-card">
          <div class="planner-card__header">
            <div>
              <div class="section-badge">Trip Planner Workspace</div>
              <h2 class="planner-card__title">智能旅行助手</h2>
              <p class="planner-card__subtitle">
                用一套完整但不复杂的流程，把旅行意图、出行策略和知识资料交给助手。
              </p>
            </div>
            <div class="planner-steps">
              <span class="planner-step">1 目的地</span>
              <span class="planner-step">2 偏好策略</span>
              <span class="planner-step">3 关键约束</span>
              <span class="planner-step">4 知识增强</span>
            </div>
          </div>

          <a-form :model="formData" layout="vertical" @finish="handleSubmit">
            <div class="section-panel">
              <div class="section-heading">
                <div>
                  <div class="section-badge">Section 01</div>
                  <h3>目的地与出行窗口</h3>
                </div>
                <p>确定城市和日期后，系统会自动推导出本次行程跨度和结果页摘要。</p>
              </div>

              <a-row :gutter="[18, 6]">
                <a-col :xs="24" :md="10">
                  <a-form-item name="city" :rules="[{ required: true, message: '请输入目的地城市' }]">
                    <template #label>
                      <span class="field-label">目的地城市</span>
                    </template>
                    <a-input
                      v-model:value="formData.city"
                      size="large"
                      class="atlas-input"
                      placeholder="例如：北京、上海、成都"
                    >
                      <template #prefix>
                        <span>📍</span>
                      </template>
                    </a-input>
                  </a-form-item>
                </a-col>
                <a-col :xs="12" :md="5">
                  <a-form-item name="start_date" :rules="[{ required: true, message: '请选择开始日期' }]">
                    <template #label>
                      <span class="field-label">开始日期</span>
                    </template>
                    <a-date-picker
                      v-model:value="formData.start_date"
                      style="width: 100%"
                      size="large"
                      class="atlas-input"
                      placeholder="出发日期"
                      :disabled-date="disabledPastDate"
                    />
                  </a-form-item>
                </a-col>
                <a-col :xs="12" :md="5">
                  <a-form-item name="end_date" :rules="[{ required: true, message: '请选择结束日期' }]">
                    <template #label>
                      <span class="field-label">结束日期</span>
                    </template>
                    <a-date-picker
                      v-model:value="formData.end_date"
                      style="width: 100%"
                      size="large"
                      class="atlas-input"
                      placeholder="返程日期"
                      :disabled-date="disabledEndDate"
                    />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="4">
                  <a-form-item>
                    <template #label>
                      <span class="field-label">旅行天数</span>
                    </template>
                    <div class="day-pill">
                      <span class="day-pill__number">{{ formData.travel_days }}</span>
                      <span class="day-pill__unit">天</span>
                    </div>
                  </a-form-item>
                </a-col>
              </a-row>
            </div>

            <div class="section-panel">
              <div class="section-heading">
                <div>
                  <div class="section-badge">Section 02</div>
                  <h3>行程取向与兴趣偏好</h3>
                </div>
                <p>真实的旅行规划不仅看景点，更取决于通勤方式、住宿位置和你真正想花时间的事情。</p>
              </div>

              <a-row :gutter="[18, 6]">
                <a-col :xs="24" :md="12">
                  <a-form-item name="transportation">
                    <template #label>
                      <span class="field-label">交通方式</span>
                    </template>
                    <a-select v-model:value="formData.transportation" size="large" class="atlas-select">
                      <a-select-option value="公共交通">公共交通</a-select-option>
                      <a-select-option value="自驾">自驾</a-select-option>
                      <a-select-option value="步行">步行</a-select-option>
                      <a-select-option value="混合">混合</a-select-option>
                    </a-select>
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="12">
                  <a-form-item name="accommodation">
                    <template #label>
                      <span class="field-label">住宿偏好</span>
                    </template>
                    <a-select v-model:value="formData.accommodation" size="large" class="atlas-select">
                      <a-select-option value="经济型酒店">经济型酒店</a-select-option>
                      <a-select-option value="舒适型酒店">舒适型酒店</a-select-option>
                      <a-select-option value="豪华酒店">豪华酒店</a-select-option>
                      <a-select-option value="民宿">民宿</a-select-option>
                    </a-select>
                  </a-form-item>
                </a-col>
              </a-row>

              <a-form-item name="preferences">
                <template #label>
                  <span class="field-label">旅行偏好</span>
                </template>
                <div class="interest-grid">
                  <a-checkbox-group v-model:value="formData.preferences" class="interest-checkbox-group">
                    <a-checkbox
                      v-for="option in preferenceOptions"
                      :key="option.value"
                      :value="option.value"
                      class="interest-card"
                    >
                      <span class="interest-card__icon">{{ option.icon }}</span>
                      <span class="interest-card__label">{{ option.label }}</span>
                      <span class="interest-card__copy">{{ option.description }}</span>
                    </a-checkbox>
                  </a-checkbox-group>
                </div>
              </a-form-item>
            </div>

            <div class="section-panel">
              <div class="section-heading">
                <div>
                  <div class="section-badge">Section 03</div>
                  <h3>补充要求与关键限制</h3>
                </div>
                <p>把那些真正影响体验的条件写清楚，比如想住哪里、避开什么、是否适合老人孩子。</p>
              </div>

              <div class="helper-chips">
                <button
                  v-for="chip in helperRequirementChips"
                  :key="chip"
                  type="button"
                  class="helper-chip"
                  @click="appendRequirement(chip)"
                >
                  + {{ chip }}
                </button>
              </div>

              <a-form-item name="free_text_input">
                <template #label>
                  <span class="field-label">额外要求</span>
                </template>
                <a-textarea
                  v-model:value="formData.free_text_input"
                  :rows="4"
                  size="large"
                  class="atlas-textarea"
                  placeholder="例如：想把博物馆安排在上午；不希望单日步行太多；希望晚餐以本地特色为主；尽量住在地铁站附近。"
                />
              </a-form-item>

              <div class="prompt-preview">
                <div class="prompt-preview__title">生成前提示摘要</div>
                <div class="prompt-preview__body">{{ promptPreview }}</div>
              </div>
            </div>

            <div class="section-panel">
              <div class="section-heading">
                <div>
                  <div class="section-badge">Section 04</div>
                  <h3>知识库导入</h3>
                </div>
                <p>把你的私藏攻略、公司差旅制度、酒店名单、官方文章或本地文件一起交给系统参考。</p>
              </div>

              <a-tabs v-model:activeKey="kbActiveTab" class="knowledge-tabs">
                <a-tab-pane key="text" tab="文本">
                  <a-row :gutter="[16, 8]">
                    <a-col :xs="24" :md="10">
                      <a-form-item>
                        <template #label>
                          <span class="field-label">标题(可选)</span>
                        </template>
                        <a-input v-model:value="kbTextTitle" size="large" class="atlas-input" placeholder="例如：我的北京攻略" />
                      </a-form-item>
                    </a-col>
                    <a-col :xs="24" :md="14">
                      <a-form-item>
                        <template #label>
                          <span class="field-label">内容</span>
                        </template>
                        <a-textarea
                          v-model:value="kbTextContent"
                          :rows="5"
                          size="large"
                          class="atlas-textarea"
                          placeholder="粘贴你希望 AI 参考的文档、清单、制度、开放时间、预约信息等。"
                        />
                      </a-form-item>
                    </a-col>
                  </a-row>
                  <a-button type="default" :loading="kbLoading" @click="handleIngestText">导入文本资料</a-button>
                </a-tab-pane>

                <a-tab-pane key="url" tab="URL">
                  <a-row :gutter="[16, 8]">
                    <a-col :xs="24" :md="10">
                      <a-form-item>
                        <template #label>
                          <span class="field-label">标题(可选)</span>
                        </template>
                        <a-input v-model:value="kbUrlTitle" size="large" class="atlas-input" placeholder="例如：某攻略页" />
                      </a-form-item>
                    </a-col>
                    <a-col :xs="24" :md="14">
                      <a-form-item>
                        <template #label>
                          <span class="field-label">链接</span>
                        </template>
                        <a-input v-model:value="kbUrl" size="large" class="atlas-input" placeholder="https://..." />
                      </a-form-item>
                    </a-col>
                  </a-row>
                  <a-button type="default" :loading="kbLoading" @click="handleIngestUrl">导入网页资料</a-button>
                </a-tab-pane>

                <a-tab-pane key="file" tab="文件">
                  <a-row :gutter="[16, 8]">
                    <a-col :xs="24" :md="10">
                      <a-form-item>
                        <template #label>
                          <span class="field-label">标题(可选)</span>
                        </template>
                        <a-input v-model:value="kbFileTitle" size="large" class="atlas-input" placeholder="留空则使用文件名" />
                      </a-form-item>
                    </a-col>
                    <a-col :xs="24" :md="14">
                      <a-form-item>
                        <template #label>
                          <span class="field-label">上传文件</span>
                        </template>
                        <a-upload
                          :before-upload="beforeUpload"
                          :max-count="1"
                          :file-list="kbFileList"
                          @remove="handleRemoveFile"
                        >
                          <a-button>选择文件</a-button>
                        </a-upload>
                      </a-form-item>
                    </a-col>
                  </a-row>
                  <a-button type="default" :loading="kbLoading" @click="handleIngestFile">导入本地文件</a-button>
                </a-tab-pane>
              </a-tabs>

              <div class="knowledge-footnote">
                导入后会在生成行程时自动检索并引用；引用来源会在结果页展示。
              </div>
            </div>

            <div class="submit-band">
              <div>
                <div class="submit-band__title">准备生成你的旅行图册</div>
                <div class="submit-band__copy">系统会结合景点、天气、住宿和补充要求，输出可直接浏览的结果页。</div>
              </div>
              <a-button
                type="primary"
                html-type="submit"
                :loading="loading"
                size="large"
                class="submit-button"
              >
                <template v-if="!loading">开始规划我的旅行</template>
                <template v-else>正在生成中...</template>
              </a-button>
            </div>

            <div v-if="loading" class="loading-panel">
              <a-progress
                :percent="loadingProgress"
                status="active"
                :stroke-color="{ '0%': '#1f5a5a', '100%': '#d46d3d' }"
                :stroke-width="10"
              />
              <div class="loading-status">{{ loadingStatus }}</div>
            </div>
          </a-form>
        </a-card>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import type { Dayjs } from 'dayjs'
import { message } from 'ant-design-vue'
import { generateTripPlan, ingestRagFile, ingestRagText, ingestRagUrl } from '@/services/api'
import type { TripFormData } from '@/types'

interface PreferenceOption {
  value: string
  label: string
  icon: string
  description: string
}

interface PresetTrip {
  name: string
  icon: string
  description: string
  city: string
  duration: number
  transportation: string
  accommodation: string
  preferences: string[]
  note: string
}

const router = useRouter()
const loading = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('')

const kbActiveTab = ref<'text' | 'url' | 'file'>('text')
const kbLoading = ref(false)
const kbTextTitle = ref('')
const kbTextContent = ref('')
const kbUrlTitle = ref('')
const kbUrl = ref('')
const kbFileTitle = ref('')
const kbFileList = ref<any[]>([])
const kbSelectedFile = ref<File | null>(null)
const knowledgeFeed = ref<Array<{ title: string; type: string; time: string }>>([])

const preferenceOptions: PreferenceOption[] = [
  { value: '历史文化', label: '历史文化', icon: '🏛️', description: '古迹、博物馆、城市记忆' },
  { value: '自然风光', label: '自然风光', icon: '🏞️', description: '公园、山水、步道与观景线' },
  { value: '美食', label: '美食', icon: '🍜', description: '本地特色、老店和高口碑餐厅' },
  { value: '购物', label: '购物', icon: '🛍️', description: '商圈、伴手礼、风格店铺' },
  { value: '艺术', label: '艺术', icon: '🎨', description: '展览、建筑、创意空间' },
  { value: '休闲', label: '休闲', icon: '☕', description: '散步、咖啡馆、松弛时段' }
]

const presetTrips: PresetTrip[] = [
  {
    name: '周末城市采样',
    icon: '🧭',
    description: '用短时间浓缩城市的代表体验，适合双休日快速出行。',
    city: '上海',
    duration: 3,
    transportation: '公共交通',
    accommodation: '舒适型酒店',
    preferences: ['美食', '艺术', '购物'],
    note: '希望住在地铁站附近，白天安排城市漫游，晚上安排夜景和特色晚餐。'
  },
  {
    name: '轻松家庭线路',
    icon: '🏡',
    description: '减少折返和高体力活动，更适合长辈或孩子同行。',
    city: '北京',
    duration: 4,
    transportation: '混合',
    accommodation: '舒适型酒店',
    preferences: ['历史文化', '休闲'],
    note: '带长辈同行，希望单日步行不要太多，中午预留休息时间。'
  },
  {
    name: '差旅延展两日',
    icon: '💼',
    description: '把工作间隙和会后时间变成一份高效的小型旅行计划。',
    city: '深圳',
    duration: 2,
    transportation: '公共交通',
    accommodation: '经济型酒店',
    preferences: ['美食', '休闲'],
    note: '白天有固定安排，希望晚上和空档时间去离酒店近的地方。'
  }
]

const helperRequirementChips = [
  '需要无障碍设施',
  '优先本地特色餐厅',
  '希望住在地铁站附近',
  '不想单日步行太多',
  '尽量减少排队时间',
  '想安排亲子友好景点'
]

const deliveryItems = [
  { icon: '🗺️', title: '每日路线', description: '按天组织景点、住宿与餐饮安排。' },
  { icon: '📍', title: '地图分布', description: '在结果页中查看景点位置与线路。' },
  { icon: '💰', title: '预算概览', description: '如果后端返回预算，将同步展示费用结构。' }
]

const formData = reactive<Omit<TripFormData, 'start_date' | 'end_date'> & { start_date: Dayjs | null; end_date: Dayjs | null }>({
  city: '',
  start_date: null,
  end_date: null,
  travel_days: 1,
  transportation: '公共交通',
  accommodation: '经济型酒店',
  preferences: [],
  free_text_input: ''
})

const heroDays = computed(() => `${formData.travel_days}D`)

const selectedPreferenceLabels = computed(() => formData.preferences)

const travelDateText = computed(() => {
  if (!formData.start_date || !formData.end_date) {
    return '尚未选择出行日期'
  }
  return `${formData.start_date.format('MM月DD日')} - ${formData.end_date.format('MM月DD日')}`
})

const generatedFocus = computed(() => {
  const focus = [
    `${formData.transportation} 通勤路径`,
    `${formData.accommodation} 住宿取向`,
    `${formData.travel_days} 天节奏安排`
  ]

  if (formData.preferences.length > 0) {
    focus.push(`重点覆盖 ${formData.preferences.slice(0, 2).join(' / ')}`)
  }

  if (formData.free_text_input.trim()) {
    focus.push('纳入你的额外要求与限制')
  }

  return focus
})

const promptPreview = computed(() => {
  const parts = [
    `交通方式：${formData.transportation}`,
    `住宿偏好：${formData.accommodation}`,
    formData.preferences.length ? `旅行偏好：${formData.preferences.join('、')}` : '',
    formData.free_text_input.trim() ? `额外要求：${formData.free_text_input.trim()}` : ''
  ].filter(Boolean)

  return parts.join('；')
})

const disabledPastDate = (current: Dayjs) => current && current < dayjs().startOf('day')

const disabledEndDate = (current: Dayjs) => {
  if (!formData.start_date) {
    return disabledPastDate(current)
  }
  return current < formData.start_date.startOf('day')
}

watch([() => formData.start_date, () => formData.end_date], ([start, end]) => {
  if (start && end) {
    const days = end.diff(start, 'day') + 1
    if (days > 0 && days <= 30) {
      formData.travel_days = days
    } else if (days > 30) {
      message.warning('旅行天数不能超过30天')
      formData.end_date = null
    } else {
      message.warning('结束日期不能早于开始日期')
      formData.end_date = null
    }
  }
})

const appendRequirement = (chip: string) => {
  formData.free_text_input = formData.free_text_input
    ? `${formData.free_text_input}；${chip}`
    : chip
}

const applyPreset = (preset: PresetTrip) => {
  const start = dayjs().add(5, 'day')
  formData.city = preset.city
  formData.start_date = start
  formData.end_date = start.add(preset.duration - 1, 'day')
  formData.transportation = preset.transportation
  formData.accommodation = preset.accommodation
  formData.preferences = [...preset.preferences]
  formData.free_text_input = preset.note
  message.success(`已载入「${preset.name}」情境`)
}

const recordKnowledgeItem = (type: string, title: string) => {
  knowledgeFeed.value.unshift({
    type,
    title,
    time: dayjs().format('MM-DD HH:mm')
  })
  knowledgeFeed.value = knowledgeFeed.value.slice(0, 5)
}

const handleIngestText = async () => {
  if (!kbTextContent.value.trim()) {
    message.warning('请输入要导入的文本内容')
    return
  }
  kbLoading.value = true
  try {
    const res = await ingestRagText(kbTextTitle.value, kbTextContent.value)
    if (res.success) {
      message.success('知识库文本导入成功')
      recordKnowledgeItem('文本', kbTextTitle.value || '未命名文本')
      kbTextContent.value = ''
      kbTextTitle.value = ''
    } else {
      message.error(res.message || '导入失败')
    }
  } catch (e: any) {
    message.error(e.message || '导入失败')
  } finally {
    kbLoading.value = false
  }
}

const handleIngestUrl = async () => {
  if (!kbUrl.value.trim()) {
    message.warning('请输入要导入的URL')
    return
  }
  kbLoading.value = true
  try {
    const res = await ingestRagUrl(kbUrlTitle.value, kbUrl.value)
    if (res.success) {
      message.success('知识库URL导入成功')
      recordKnowledgeItem('网页', kbUrlTitle.value || kbUrl.value)
      kbUrl.value = ''
      kbUrlTitle.value = ''
    } else {
      message.error(res.message || '导入失败')
    }
  } catch (e: any) {
    message.error(e.message || '导入失败')
  } finally {
    kbLoading.value = false
  }
}

const beforeUpload = (file: File) => {
  kbSelectedFile.value = file
  kbFileList.value = [{ name: file.name, uid: String(Date.now()), status: 'done' }]
  return false
}

const handleRemoveFile = () => {
  kbSelectedFile.value = null
  kbFileList.value = []
}

const handleIngestFile = async () => {
  if (!kbSelectedFile.value) {
    message.warning('请先选择文件')
    return
  }
  kbLoading.value = true
  try {
    const res = await ingestRagFile(kbSelectedFile.value, kbFileTitle.value)
    if (res.success) {
      message.success('知识库文件导入成功')
      recordKnowledgeItem('文件', kbFileTitle.value || kbSelectedFile.value.name)
      kbFileTitle.value = ''
      handleRemoveFile()
    } else {
      message.error(res.message || '导入失败')
    }
  } catch (e: any) {
    message.error(e.message || '导入失败')
  } finally {
    kbLoading.value = false
  }
}

const handleSubmit = async () => {
  if (!formData.start_date || !formData.end_date) {
    message.error('请选择日期')
    return
  }

  loading.value = true
  loadingProgress.value = 0
  loadingStatus.value = '正在整理旅行线索...'

  const progressInterval = setInterval(() => {
    if (loadingProgress.value < 90) {
      loadingProgress.value += 10
      if (loadingProgress.value <= 30) {
        loadingStatus.value = '正在搜索景点与地理信息...'
      } else if (loadingProgress.value <= 50) {
        loadingStatus.value = '正在查询天气与通勤条件...'
      } else if (loadingProgress.value <= 70) {
        loadingStatus.value = '正在匹配酒店与餐饮建议...'
      } else {
        loadingStatus.value = '正在生成旅行图册...'
      }
    }
  }, 500)

  try {
    const requestData: TripFormData = {
      city: formData.city,
      start_date: formData.start_date.format('YYYY-MM-DD'),
      end_date: formData.end_date.format('YYYY-MM-DD'),
      travel_days: formData.travel_days,
      transportation: formData.transportation,
      accommodation: formData.accommodation,
      preferences: formData.preferences,
      free_text_input: formData.free_text_input
    }

    const response = await generateTripPlan(requestData)

    clearInterval(progressInterval)
    loadingProgress.value = 100
    loadingStatus.value = '图册已完成，准备进入结果页...'

    if (response.success && response.data) {
      sessionStorage.setItem('tripPlan', JSON.stringify(response.data))
      message.success('旅行计划生成成功!')
      setTimeout(() => {
        router.push('/result')
      }, 500)
    } else {
      message.error(response.message || '生成失败')
    }
  } catch (error: any) {
    clearInterval(progressInterval)
    message.error(error.message || '生成旅行计划失败,请稍后重试')
  } finally {
    setTimeout(() => {
      loading.value = false
      loadingProgress.value = 0
      loadingStatus.value = ''
    }, 1000)
  }
}
</script>

<style scoped>
.home-atlas {
  display: grid;
  gap: 24px;
}

.hero-board {
  position: relative;
  overflow: hidden;
  border-radius: 34px;
  background:
    linear-gradient(135deg, rgba(255, 252, 247, 0.96), rgba(246, 238, 226, 0.94)),
    linear-gradient(180deg, rgba(255, 255, 255, 0.35), rgba(255, 255, 255, 0));
  border: 1px solid rgba(21, 49, 58, 0.1);
  box-shadow: var(--atlas-shadow);
}

.hero-board__map {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.95;
  background:
    linear-gradient(180deg, rgba(244, 237, 226, 0.94) 0%, rgba(244, 237, 226, 0.9) 18%, rgba(244, 237, 226, 0.82) 34%, rgba(244, 237, 226, 0.62) 54%, rgba(244, 237, 226, 0.36) 70%, rgba(244, 237, 226, 0.18) 100%),
    linear-gradient(180deg, rgba(17, 52, 63, 0) 0%, rgba(17, 52, 63, 0.04) 52%, rgba(17, 52, 63, 0.16) 74%, rgba(17, 52, 63, 0.28) 100%),
    url('https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Misty_Mountains_%2829990500236%29.jpg/3840px-Misty_Mountains_%2829990500236%29.jpg'),
    radial-gradient(circle at 18% 28%, rgba(31, 90, 90, 0.12), transparent 20%),
    radial-gradient(circle at 82% 26%, rgba(212, 109, 61, 0.14), transparent 18%),
    linear-gradient(rgba(21, 49, 58, 0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(21, 49, 58, 0.07) 1px, transparent 1px);
  background-size: auto, auto, cover, auto, auto, 44px 44px, 44px 44px;
  background-position: center top, center top, center bottom, center, center, center, center;
  background-repeat: no-repeat, no-repeat, no-repeat, no-repeat, no-repeat, repeat, repeat;
}

.hero-board__grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 0.9fr);
  gap: 26px;
  padding: 30px;
}

.hero-copy,
.hero-brief,
.planner-card,
.sidebar-card {
  border-radius: 28px;
}

.hero-copy {
  padding: 10px 4px 8px 2px;
}

.eyebrow,
.section-badge {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--atlas-deep);
}

.hero-title,
.planner-card__title,
.section-heading h3,
.sidebar-card h3,
.hero-brief__city {
  font-family: Georgia, 'Times New Roman', 'Songti SC', serif;
}

.hero-title {
  margin: 18px 0 14px;
  font-size: clamp(34px, 4.1vw, 58px);
  line-height: 1.06;
  letter-spacing: -0.04em;
  max-width: 11ch;
}

.hero-title span {
  display: block;
  color: var(--atlas-deep);
}

.hero-description,
.planner-card__subtitle,
.section-heading p,
.scenario-card__description,
.delivery-item__description,
.notes-item__copy,
.knowledge-feed__time,
.knowledge-footnote,
.summary-date,
.hero-brief__meta {
  color: var(--atlas-muted);
}

.hero-description {
  max-width: 620px;
  margin: 0;
  line-height: 1.8;
  font-size: 15px;
}

.hero-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin: 26px 0 22px;
}

.hero-stat {
  padding: 18px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.7);
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
  font-size: 13px;
  color: var(--atlas-muted);
}

.strip-title,
.section-small-title,
.sidebar-section__title,
.prompt-preview__title,
.submit-band__title,
.scenario-card__name,
.delivery-item__title,
.knowledge-feed__title,
.notes-item__title {
  font-weight: 700;
}

.scenario-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 12px;
}

.scenario-card,
.helper-chip {
  cursor: pointer;
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
}

.scenario-card {
  text-align: left;
  padding: 18px;
  border-radius: 22px;
  border: 1px solid rgba(21, 49, 58, 0.08);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(246, 237, 224, 0.96));
  box-shadow: 0 16px 28px rgba(45, 63, 71, 0.08);
}

.scenario-card:hover,
.helper-chip:hover {
  transform: translateY(-2px);
  box-shadow: 0 20px 34px rgba(31, 90, 90, 0.12);
  border-color: rgba(31, 90, 90, 0.22);
}

.scenario-card__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.scenario-card__icon {
  font-size: 24px;
}

.scenario-card__duration {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(31, 90, 90, 0.1);
  color: var(--atlas-deep);
  font-size: 12px;
  font-weight: 700;
}

.scenario-card__name {
  font-size: 16px;
  margin-bottom: 6px;
}

.scenario-card__description {
  font-size: 13px;
  line-height: 1.6;
}

.hero-visual {
  min-height: 100%;
}

.hero-brief {
  position: relative;
  padding: 24px;
  background: linear-gradient(180deg, rgba(252, 248, 241, 0.94), rgba(234, 243, 239, 0.92));
  color: var(--atlas-ink);
  border: 1px solid rgba(21, 49, 58, 0.1);
  box-shadow: 0 24px 44px rgba(31, 90, 90, 0.12);
  border-radius: 24px;
  overflow: hidden;
}

.hero-brief::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 30%;
  background:
    linear-gradient(180deg, rgba(252, 248, 241, 0) 0%, rgba(252, 248, 241, 0.18) 24%, rgba(31, 90, 90, 0.1) 56%, rgba(31, 90, 90, 0.28) 100%);
  opacity: 1;
  pointer-events: none;
}

.hero-brief::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 78% 18%, rgba(244, 196, 138, 0.12), transparent 14%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.14) 0%, transparent 18%, transparent 56%, rgba(12, 35, 41, 0.04) 100%);
  pointer-events: none;
}

.hero-brief > * {
  position: relative;
  z-index: 1;
}

.hero-brief__header {
  display: block;
}

.hero-brief__kicker {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--atlas-deep);
}

.hero-brief__city {
  font-size: 34px;
  font-weight: 700;
  margin-top: 12px;
  margin-bottom: 8px;
  letter-spacing: -0.04em;
  color: var(--atlas-deep);
}

.hero-brief__tags,
.sidebar-tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hero-brief__tags {
  margin: 20px 0 24px;
}

.brief-tag,
.sidebar-tag {
  padding: 8px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.brief-tag {
  background: rgba(31, 90, 90, 0.1);
  color: var(--atlas-deep);
  border: 1px solid rgba(21, 49, 58, 0.08);
}

.hero-brief__section + .hero-brief__section {
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid rgba(21, 49, 58, 0.1);
}

.focus-list,
.delivery-list,
.knowledge-feed,
.notes-list {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.focus-item,
.delivery-item,
.knowledge-feed__item,
.notes-item {
  border-radius: 18px;
}

.focus-item {
  padding: 12px 14px;
  background: rgba(31, 90, 90, 0.08);
  font-size: 13px;
  color: var(--atlas-ink);
}

.delivery-item,
.notes-item {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  gap: 12px;
  padding: 14px 16px;
}

.delivery-item {
  background: rgba(31, 90, 90, 0.08);
}

.delivery-item__icon,
.notes-item__icon {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.delivery-item__icon {
  background: rgba(31, 90, 90, 0.12);
}

.delivery-item__title {
  color: var(--atlas-deep);
  margin-bottom: 4px;
}

.delivery-item__description {
  font-size: 12px;
  line-height: 1.55;
  color: var(--atlas-muted);
}

.planner-grid {
  display: block;
}

.planner-main--full {
  width: 100%;
}

.atlas-card {
  border: 1px solid rgba(21, 49, 58, 0.1);
  background: linear-gradient(180deg, rgba(255, 252, 247, 0.94), rgba(251, 245, 236, 0.9));
  box-shadow: var(--atlas-shadow);
  overflow: hidden;
}

.planner-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  padding-bottom: 24px;
  margin-bottom: 24px;
  border-bottom: 1px solid rgba(21, 49, 58, 0.1);
}

.planner-card__title {
  margin: 10px 0 8px;
  font-size: 34px;
}

.planner-card__subtitle {
  margin: 0;
  line-height: 1.75;
  max-width: 620px;
}

.planner-steps {
  display: flex;
  flex-wrap: nowrap;
  justify-content: flex-end;
  gap: 10px;
  max-width: none;
  white-space: nowrap;
}

.planner-step {
  padding: 10px 12px;
  border-radius: 999px;
  background: rgba(212, 109, 61, 0.1);
  color: var(--atlas-accent);
  font-size: 12px;
  font-weight: 700;
}

.section-panel + .section-panel {
  margin-top: 22px;
}

.section-panel {
  padding: 24px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(21, 49, 58, 0.08);
}

.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  margin-bottom: 18px;
}

.section-heading h3 {
  margin: 10px 0 0;
  font-size: 26px;
}

.section-heading p {
  max-width: 520px;
  line-height: 1.7;
  font-size: 14px;
  margin: 0;
  white-space: nowrap;
}

.field-label {
  font-weight: 700;
  color: var(--atlas-ink);
}

.atlas-input :deep(.ant-input),
.atlas-input :deep(.ant-picker),
.atlas-textarea :deep(.ant-input),
.atlas-select :deep(.ant-select-selector) {
  min-height: 52px;
  border-radius: 16px !important;
  border-color: rgba(21, 49, 58, 0.12) !important;
  background: rgba(255, 255, 255, 0.86) !important;
  box-shadow: none !important;
}

.atlas-textarea :deep(.ant-input) {
  min-height: auto;
  padding: 14px 16px;
}

.atlas-input :deep(.ant-input:hover),
.atlas-input :deep(.ant-picker:hover),
.atlas-textarea :deep(.ant-input:hover),
.atlas-select:hover :deep(.ant-select-selector) {
  border-color: rgba(31, 90, 90, 0.28) !important;
}

.atlas-input :deep(.ant-input:focus),
.atlas-input :deep(.ant-picker-focused),
.atlas-textarea :deep(.ant-input:focus),
.atlas-select :deep(.ant-select-focused .ant-select-selector) {
  border-color: rgba(31, 90, 90, 0.4) !important;
  box-shadow: 0 0 0 4px rgba(31, 90, 90, 0.08) !important;
}

.day-pill {
  min-height: 52px;
  border-radius: 16px;
  background: linear-gradient(135deg, var(--atlas-deep), #2b7e79);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fffdf8;
}

.day-pill__number {
  font-size: 24px;
  font-weight: 800;
}

.interest-grid {
  padding-top: 2px;
}

.interest-checkbox-group {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.interest-card {
  margin: 0 !important;
  padding: 16px 18px !important;
  border-radius: 20px;
  border: 1px solid rgba(21, 49, 58, 0.08);
  background: rgba(255, 255, 255, 0.82);
  min-height: 122px;
  display: flex !important;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.interest-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 30px rgba(31, 90, 90, 0.08);
  border-color: rgba(31, 90, 90, 0.22);
}

.interest-card :deep(.ant-checkbox) {
  display: none;
}

.interest-card :deep(.ant-checkbox + span) {
  padding-inline-start: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.interest-checkbox-group :deep(.ant-checkbox-wrapper-checked) {
  background: linear-gradient(180deg, rgba(228, 240, 236, 0.98), rgba(255, 255, 255, 0.98));
  border-color: rgba(31, 90, 90, 0.3);
}

.interest-card__icon {
  font-size: 22px;
}

.interest-card__label {
  font-size: 15px;
  font-weight: 700;
}

.interest-card__copy {
  color: var(--atlas-muted);
  font-size: 13px;
  line-height: 1.6;
}

.helper-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
}

.helper-chip {
  padding: 10px 14px;
  border-radius: 999px;
  border: 1px solid rgba(21, 49, 58, 0.1);
  background: rgba(255, 255, 255, 0.82);
  color: var(--atlas-ink);
  font-size: 13px;
}

.prompt-preview {
  padding: 16px 18px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(31, 90, 90, 0.08), rgba(212, 109, 61, 0.08));
  border: 1px dashed rgba(31, 90, 90, 0.2);
}

.prompt-preview__body {
  margin-top: 8px;
  line-height: 1.8;
}

.knowledge-tabs :deep(.ant-tabs-nav::before) {
  border-bottom-color: rgba(21, 49, 58, 0.08);
}

.knowledge-tabs :deep(.ant-tabs-tab) {
  font-weight: 700;
}

.knowledge-tabs :deep(.ant-tabs-ink-bar) {
  background: var(--atlas-deep);
}

.knowledge-footnote {
  margin-top: 10px;
  font-size: 13px;
}

.submit-band {
  margin-top: 24px;
  padding: 22px 24px;
  border-radius: 24px;
  background: linear-gradient(135deg, rgba(212, 109, 61, 0.12), rgba(31, 90, 90, 0.12));
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.submit-band__copy {
  color: var(--atlas-muted);
  margin-top: 6px;
}

.submit-button {
  min-width: 240px;
  height: 56px;
  border-radius: 999px;
  border: none;
  background: linear-gradient(135deg, var(--atlas-deep), var(--atlas-accent));
  font-size: 16px;
  font-weight: 700;
  box-shadow: 0 18px 34px rgba(31, 90, 90, 0.18);
}

.loading-panel {
  margin-top: 18px;
  padding: 18px 20px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(21, 49, 58, 0.08);
}

.loading-status {
  margin-top: 10px;
  color: var(--atlas-deep);
  font-weight: 600;
}

@media (max-width: 1280px) {
  .hero-board__grid,
  .planner-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .hero-visual {
    min-height: 0;
  }
}

@media (max-width: 960px) {
  .planner-card__header,
  .section-heading,
  .submit-band {
    flex-direction: column;
  }

  .hero-stats,
  .scenario-grid,
  .interest-checkbox-group {
    grid-template-columns: 1fr;
  }

  .planner-steps {
    justify-content: flex-start;
    flex-wrap: wrap;
    white-space: normal;
  }
}

@media (max-width: 640px) {
  .hero-board__grid {
    padding: 18px;
  }

  .hero-title {
    font-size: 38px;
  }

  .summary-metrics {
    grid-template-columns: 1fr;
  }

  .submit-button {
    width: 100%;
    min-width: 0;
  }
}
</style>
