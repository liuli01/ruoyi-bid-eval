<template>
  <div class="app-container">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.totalProjects }}</div>
          <div class="stat-label">项目总数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card card-running">
          <div class="stat-value">{{ stats.runningReviews }}</div>
          <div class="stat-label">评审运行中</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card card-done">
          <div class="stat-value">{{ stats.doneReviews }}</div>
          <div class="stat-label">评审完成</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card card-triggered">
          <div class="stat-value">{{ stats.totalTriggered || '-' }}</div>
          <div class="stat-label">规则触发</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>项目状态分布</span></template>
          <div class="status-bars">
            <div v-for="s in statusList" :key="s.key" class="status-row">
              <span class="status-name">{{ s.label }}</span>
              <el-progress :percentage="s.pct" :color="s.color" :stroke-width="20" />
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>最近评审</span></template>
          <div v-if="stats.recentReviews && stats.recentReviews.length > 0">
            <div v-for="r in stats.recentReviews" :key="r.reviewId" class="recent-item" @click="viewProgress(r)">
              <el-tag :type="tagType(r.status)" size="small">{{ r.status }}</el-tag>
              <span class="recent-text">评审 #{{ r.reviewId }} — 项目 #{{ r.projectId }}</span>
              <span class="recent-time">{{ fmtTime(r.createTime) }}</span>
            </div>
          </div>
          <el-empty v-else description="暂无评审记录" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup name="EvalDashboard">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import request from '@/utils/request'

const router = useRouter()
const stats = ref({})

const statusList = computed(() => {
  const d = stats.value.projectStatusDistribution || {}
  const total = stats.value.totalProjects || 1
  return [
    { key: 'pending', label: '待处理', pct: Math.round((d.pending || 0) / total * 100), color: '#909399' },
    { key: 'running', label: '运行中', pct: Math.round((d.running || 0) / total * 100), color: '#409EFF' },
    { key: 'completed', label: '已完成', pct: Math.round((d.completed || 0) / total * 100), color: '#67C23A' },
    { key: 'failed', label: '失败', pct: Math.round((d.failed || 0) / total * 100), color: '#F56C6C' },
  ]
})

function tagType(s) {
  return s === 'done' ? 'success' : s === 'running' ? 'warning' : 'danger'
}

function fmtTime(t) {
  if (!t) return ''
  return t.slice(0, 16).replace('T', ' ')
}

function viewProgress(row) {
  router.push(`/eval/review-progress/${row.reviewId}`)
}

onMounted(async () => {
  const res = await request({ url: '/eval/dashboard', method: 'get' })
  stats.value = res.data || res
})
</script>

<style scoped>
.stat-card { text-align: center; cursor: default; }
.stat-card .stat-value { font-size: 36px; font-weight: bold; color: #409EFF; }
.stat-card .stat-label { font-size: 14px; color: #606266; margin-top: 4px; }
.card-running .stat-value { color: #E6A23C; }
.card-done .stat-value { color: #67C23A; }
.card-triggered .stat-value { color: #F56C6C; }
.status-bars { padding: 8px 0; }
.status-row { display: flex; align-items: center; margin-bottom: 16px; }
.status-name { width: 60px; font-size: 13px; color: #606266; flex-shrink: 0; }
.status-row .el-progress { flex: 1; }
.recent-item { display: flex; align-items: center; padding: 8px 4px; cursor: pointer; border-bottom: 1px solid #f0f0f0; }
.recent-item:hover { background: #f5f7fa; }
.recent-text { flex: 1; margin-left: 8px; font-size: 13px; }
.recent-time { font-size: 12px; color: #999; }
</style>
