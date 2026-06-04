<template>
  <div class="app-container">
    <!-- 头部信息 -->
    <div class="review-header">
      <h2>评审流水线 #{{ reviewId }}</h2>
      <div class="header-actions">
        <el-button type="primary" :loading="starting" @click="startReview" :disabled="started">
          {{ started ? '已启动' : '启动评审' }}
        </el-button>
        <el-button @click="goBack">返回</el-button>
      </div>
    </div>

    <!-- 七步进度条 -->
    <div class="pipeline-steps">
      <div
        v-for="(step, idx) in steps"
        :key="step.key"
        class="step-item"
        :class="step.status"
      >
        <div class="step-indicator">
          <el-icon v-if="step.status === 'done'" color="#67C23A"><CircleCheck /></el-icon>
          <el-icon v-else-if="step.status === 'error'" color="#F56C6C"><CircleClose /></el-icon>
          <el-icon v-else-if="step.status === 'running'" class="spin" color="#409EFF"><Loading /></el-icon>
          <span v-else class="step-num">{{ idx + 1 }}</span>
        </div>
        <div class="step-label">{{ step.label }}</div>
        <div v-if="step.payload && step.payload.text_length !== undefined" class="step-detail">
          {{ step.payload.text_length }}字符
        </div>
        <div v-if="step.payload && step.payload.triggered !== undefined" class="step-detail">
          触发: {{ step.payload.triggered }}
        </div>
      </div>
    </div>

    <!-- 连接线 -->
    <div class="connectors">
      <div v-for="i in 6" :key="i" class="connector" :class="connectorClass(i)"></div>
    </div>

    <!-- 结果展示 -->
    <div v-if="result" class="review-result">
      <el-divider />
      <el-descriptions :column="4" border size="small">
        <el-descriptions-item label="评审编号">{{ result.reviewId }}</el-descriptions-item>
        <el-descriptions-item label="触发规则">{{ result.triggeredCount }}</el-descriptions-item>
        <el-descriptions-item label="无法判断">{{ result.insufficientCount }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ result.elapsedSec }}s</el-descriptions-item>
      </el-descriptions>
    </div>

    <!-- 意见列表 -->
    <div v-if="opinions.length > 0" class="opinion-list">
      <el-divider />
      <h3>评审意见 ({{ opinions.length }})</h3>
      <el-table :data="opinions" :max-height="400" empty-text="暂无意见">
        <el-table-column label="规则" prop="ruleId" width="90" />
        <el-table-column label="部门" prop="department" width="90" />
        <el-table-column label="摘要" prop="title" :show-overflow-tooltip="true" />
        <el-table-column label="风险" prop="riskLevel" width="70">
          <template #default="s">
            <el-tag :type="s.row.riskLevel === 'high' ? 'danger' : s.row.riskLevel === 'medium' ? 'warning' : 'info'" size="small">{{ s.row.riskLevel }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup name="ReviewProgress">
import { useRoute, useRouter } from 'vue-router'
import { startReview as startReviewApi, getReview, getReviewOpinions } from '@/api/eval/review'

const route = useRoute()
const router = useRouter()
const reviewId = ref(route.params.reviewId || '')
const projectId = ref(null)
const started = ref(false)
const starting = ref(false)
const result = ref(null)
const opinions = ref([])
const sseRef = ref(null)

const steps = reactive([
  { key: 'step0', label: '材料聚合', status: 'pending', payload: null },
  { key: 'step1', label: '完整性扫描', status: 'pending', payload: null },
  { key: 'step2', label: '规则审查', status: 'pending', payload: null },
  { key: 'step3', label: '交叉验证', status: 'pending', payload: null },
  { key: 'step4', label: '跟进意见', status: 'pending', payload: null },
  { key: 'step5', label: '意见生成', status: 'pending', payload: null },
  { key: 'step6', label: '评审完成', status: 'pending', payload: null },
])

function connectorClass(idx) {
  const before = steps[idx - 1]
  const after = steps[idx]
  if (before.status === 'done' && after.status === 'done') return 'done'
  if (before.status === 'done' && after.status === 'running') return 'active'
  return ''
}

function updateStep(stepKey, status, payload) {
  const s = steps.find(s => s.key === stepKey)
  if (s) {
    s.status = status
    if (payload) s.payload = payload
  }
}

function handleSseEvent(data) {
  try {
    const e = JSON.parse(data)
    updateStep(e.step, e.status, e.payload || null)
    if (e.status === 'done' && e.step === 'step6') {
      closeSse()
      loadResult()
    }
  } catch (e) {
    // ignore parse errors
  }
}

function connectSse(rid) {
  closeSse()
  const url = `/dev-api/eval/review/${rid}/progress`
  const es = new EventSource(url)
  es.onmessage = (event) => handleSseEvent(event.data)
  es.onerror = () => {
    // SSE connection closed, try loading result
    closeSse()
    loadResult()
  }
  sseRef.value = es
}

function closeSse() {
  if (sseRef.value) {
    sseRef.value.close()
    sseRef.value = null
  }
}

async function loadResult() {
  if (!reviewId.value) return
  const r = await getReview(reviewId.value)
  const d = r.data || r
  result.value = d
  if (d.status === 'done' || d.status === 'error') {
    const o = await getReviewOpinions(reviewId.value)
    opinions.value = Array.isArray(o.data) ? o.data : []
  }
}

async function startReview() {
  if (!projectId.value) {
    // Get project from the review
    const r = await getReview(reviewId.value || 0)
    const d = r.data || r
    if (d && d.projectId) {
      projectId.value = d.projectId
    } else {
      return
    }
  }
  starting.value = true
  try {
    const r = await startReviewApi({ projectId: projectId.value, reviewMode: 'standard' })
    const d = r.data || r
    if (d.review_id || d.reviewId) {
      const rid = d.review_id || d.reviewId
      reviewId.value = rid
      started.value = true
      connectSse(rid)
    }
  } finally {
    starting.value = false
  }
}

function goBack() {
  router.back()
}

onMounted(async () => {
  if (reviewId.value) {
    started.value = true
    // Load existing review info
    const r = await getReview(reviewId.value)
    const d = r.data || r
    if (d) {
      projectId.value = d.projectId
      result.value = d
      if (d.status === 'done') {
        loadResult()
      } else {
        connectSse(reviewId.value)
      }
    }
  }
})

onUnmounted(() => {
  closeSse()
})
</script>

<style scoped>
.review-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.pipeline-steps {
  display: flex;
  justify-content: space-between;
  position: relative;
  z-index: 1;
}
.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  text-align: center;
}
.step-indicator {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  background: #f0f2f5;
  color: #999;
  margin-bottom: 8px;
}
.step-item.done .step-indicator {
  background: #e1f3d8;
}
.step-item.running .step-indicator {
  background: #d9ecff;
}
.step-item.error .step-indicator {
  background: #fde2e2;
}
.step-num {
  font-weight: bold;
}
.step-label {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}
.step-detail {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}
.step-item.done .step-label { color: #67C23A; }
.step-item.running .step-label { color: #409EFF; }
.step-item.error .step-label { color: #F56C6C; }
.connectors {
  display: flex;
  justify-content: space-between;
  margin: -12px 20px 0;
  position: relative;
  z-index: 0;
}
.connector {
  flex: 1;
  height: 4px;
  background: #e8e8e8;
  margin: 0 2px;
  border-radius: 2px;
}
.connector.done { background: #67C23A; }
.connector.active { background: linear-gradient(90deg, #67C23A, #409EFF); }
.spin { animation: spin 1.5s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
