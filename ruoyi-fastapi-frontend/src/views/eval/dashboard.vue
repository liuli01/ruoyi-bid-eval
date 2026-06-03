<template>
  <div class="app-container">
    <!-- 四门户入口卡片 -->
    <el-row :gutter="20" style="margin-bottom:20px">
      <el-col :span="6" v-for="card in portalCards" :key="card.path">
        <el-card shadow="hover" class="portal-card" :style="{ borderTop: `3px solid ${card.color}` }" @click="goPortal(card.path)">
          <div class="portal-icon" :style="{ color: card.color }">{{ card.icon }}</div>
          <div class="portal-title">{{ card.title }}</div>
          <div class="portal-desc">{{ card.desc }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 统计卡片 -->
    <el-row :gutter="20">
      <el-col :span="6" v-for="s in statCards" :key="s.label">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value" :style="{ color: s.color }">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>项目状态分布</span></template>
          <div v-for="s in statusList" :key="s.key" class="status-row">
            <span class="status-name">{{ s.label }}</span>
            <el-progress :percentage="s.pct" :color="s.color" :stroke-width="20" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>最近评审</span></template>
          <div v-if="stats.recentReviews && stats.recentReviews.length">
            <div v-for="r in stats.recentReviews" :key="r.reviewId" class="recent-item" @click="go(`/eval/review-progress/${r.reviewId}`)">
              <el-tag :type="r.status==='done'?'success':'warning'" size="small">{{ r.status }}</el-tag>
              <span class="recent-text">评审 #{{ r.reviewId }} 项目 #{{ r.projectId }}</span>
              <span class="recent-time">{{ fmtTime(r.createTime) }}</span>
            </div>
          </div>
          <el-empty v-else description="暂无评审" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup name="EvalDashboard">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '@/utils/request'

const router = useRouter()
const stats = ref({})

const portalCards = [
  { title:'项目评审', icon:'📋', desc:'AI 评审流水线，上传材料启动智能审查', path:'/eval/project', color:'#409EFF' },
  { title:'风险会商', icon:'📢', desc:'重大项目风险会商，≥10亿美元报送商务部', path:'/eval/consultation', color:'#E6A23C' },
  { title:'项目立项', icon:'📌', desc:'高风险/跨境项目立项审批', path:'/eval/approval', color:'#67C23A' },
  { title:'一事一议', icon:'📝', desc:'受限国别/用股份公司牌子申请审批', path:'/eval/yiyi', color:'#F56C6C' },
]

const statCards = computed(() => [
  { label:'项目总数', value: stats.value.totalProjects || 0, color:'#409EFF' },
  { label:'评审运行中', value: stats.value.runningReviews || 0, color:'#E6A23C' },
  { label:'评审完成', value: stats.value.doneReviews || 0, color:'#67C23A' },
  { label:'风险会商', value: stats.value.totalConsultations || 0, color:'#F56C6C' },
])

const statusList = computed(() => {
  const d = stats.value.projectStatusDistribution || {}
  const total = stats.value.totalProjects || 1
  return [
    { key:'pending', label:'待处理', pct:Math.round((d.pending||0)/total*100), color:'#909399' },
    { key:'running', label:'运行中', pct:Math.round((d.running||0)/total*100), color:'#409EFF' },
    { key:'completed', label:'已完成', pct:Math.round((d.completed||0)/total*100), color:'#67C23A' },
    { key:'failed', label:'失败', pct:Math.round((d.failed||0)/total*100), color:'#F56C6C' },
  ]
})

function fmtTime(t) { return t ? t.slice(0,16).replace('T',' ') : '' }
function goPortal(p) { router.push(p) }
function go(p) { router.push(p) }

onMounted(async () => {
  const res = await request({ url:'/eval/dashboard', method:'get' })
  stats.value = res.data || res || {}
  // 补充会商统计
  const cr = await request({ url:'/portal/consultation/list', method:'get' })
  stats.value.totalConsultations = (cr.data||cr||[]).length
})
</script>

<style scoped>
.portal-card { cursor: pointer; text-align: center; padding: 8px 0; transition: all .2s; }
.portal-card:hover { transform: translateY(-4px); box-shadow: 0 4px 12px rgba(0,0,0,.12); }
.portal-icon { font-size: 32px; margin-bottom: 8px; }
.portal-title { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.portal-desc { font-size: 12px; color: #909399; }
.stat-card { text-align: center; }
.stat-value { font-size: 32px; font-weight: bold; }
.stat-label { font-size: 14px; color: #606266; margin-top: 4px; }
.status-row { display: flex; align-items: center; margin-bottom: 16px; }
.status-name { width: 60px; font-size: 13px; color: #606266; flex-shrink: 0; }
.status-row .el-progress { flex: 1; }
.recent-item { display: flex; align-items: center; padding: 8px 4px; cursor: pointer; border-bottom:1px solid #f0f0f0; }
.recent-item:hover { background:#f5f7fa; }
.recent-text { flex:1; margin-left:8px; font-size:13px; }
.recent-time { font-size:12px; color:#999; }
</style>
