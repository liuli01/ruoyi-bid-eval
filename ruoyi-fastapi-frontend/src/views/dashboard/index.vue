<template>
  <div class="app-container">
    <!-- H2-1: 四模块入口卡片 -->
    <el-row :gutter="20" style="margin-bottom:20px">
      <el-col :span="6" v-for="card in portalCards" :key="card.path">
        <el-card shadow="hover" class="portal-card" :style="{ borderTop: `3px solid ${card.color}` }" @click="goPortal(card.path)">
          <div class="portal-icon" :style="{ color: card.color }">{{ card.icon }}</div>
          <div class="portal-title">{{ card.title }}</div>
          <div class="portal-desc">{{ card.desc }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- H2-2: 全局统计 -->
    <el-row :gutter="20" style="margin-bottom:20px">
      <el-col :span="6" v-for="s in statCards" :key="s.label">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value" :style="{ color: s.color }">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <!-- H2-3: 项目列表 -->
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>项目列表</span>
              <el-button text type="primary" @click="$router.push('/eval/project')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="projects" v-loading="projectLoading" size="small" max-height="300">
            <el-table-column prop="projectName" label="项目名称" min-width="140" />
            <el-table-column prop="country" label="国别" width="80" />
            <el-table-column prop="amount" label="合同额" width="100" />
            <el-table-column prop="stage" label="阶段" width="70" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="70" fixed="right">
              <template #default="{ row }">
                <el-button text size="small" @click="$router.push('/eval/project/' + row.projectId)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="!projectLoading && projects.length === 0" style="text-align:center;padding:20px;color:#999">暂无项目数据</div>
        </el-card>
      </el-col>

      <!-- H2-4: 最近活动 -->
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span>最近活动</span></template>
          <div v-if="activities.length > 0">
            <div v-for="a in activities" :key="a.id" class="activity-item">
              <div class="activity-dot" :style="{ background: a.color }"></div>
              <div class="activity-content">
                <div class="activity-text">{{ a.text }}</div>
                <div class="activity-time">{{ a.time }}</div>
              </div>
            </div>
          </div>
          <div v-else style="text-align:center;padding:20px;color:#999">暂无活动记录</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- H2-5: Demo 角色切换 -->
    <el-card shadow="hover" style="margin-top:20px">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>Demo 角色切换</span>
          <el-tag type="warning" size="small">演示模式</el-tag>
        </div>
      </template>
      <el-radio-group v-model="demoRole" @change="switchRole">
        <el-radio-button value="admin">管理员（全部）</el-radio-button>
        <el-radio-button value="waishi">外事专员</el-radio-button>
        <el-radio-button value="yiyi">一事一议专员</el-radio-button>
        <el-radio-button value="reviewer">评审专员</el-radio-button>
        <el-radio-button value="leader">海外部领导</el-radio-button>
      </el-radio-group>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()

const portalCards = [
  { title: '项目评审', icon: '📋', desc: 'AI 评审流水线，上传材料启动智能审查', path: '/eval/project', color: '#409EFF' },
  { title: '风险会商', icon: '📢', desc: '重大项目风险会商，≥10亿美元报送商务部', path: '/portal/consultation', color: '#E6A23C' },
  { title: '项目立项', icon: '📌', desc: '高风险/跨境项目立项审批', path: '/portal/approval', color: '#67C23A' },
  { title: '一事一议', icon: '📝', desc: '受限国别/用股份公司牌子申请审批', path: '/portal/yiyi', color: '#F56C6C' },
]

const statCards = ref([
  { label: '项目总数', value: 0, color: '#409EFF' },
  { label: '评审运行中', value: 0, color: '#E6A23C' },
  { label: '评审完成', value: 0, color: '#67C23A' },
  { label: '风险会商', value: 0, color: '#F56C6C' },
])

const projects = ref([])
const projectLoading = ref(false)
const activities = ref([])
const demoRole = ref('admin')

function goPortal(path) {
  router.push(path)
}

function statusType(status) {
  return { pending: 'info', running: 'warning', completed: 'success', failed: 'danger' }[status] || 'info'
}

function statusLabel(status) {
  return { pending: '待处理', running: '运行中', completed: '已完成', failed: '失败' }[status] || status
}

async function switchRole(role) {
  const users = { admin: 'admin', waishi: 'waishi', yiyi: 'yiyi', reviewer: 'reviewer', leader: 'leader' }
  const pwd = 'admin123'
  try {
    const form = new FormData()
    form.append('username', users[role])
    form.append('password', pwd)
    form.append('code', '')
    form.append('uuid', '')
    const resp = await fetch('/dev-api/login', { method: 'POST', body: form })
    const d = await resp.json()
    if (d.token) {
      document.cookie = `Admin-Token=${d.token}; path=/`
      ElMessage.success(`已切换为 ${role} 角色`)
      location.reload()
    } else {
      ElMessage.warning('切换失败：' + (d.msg || '未知错误'))
    }
  } catch (e) {
    ElMessage.error('角色切换请求失败')
  }
}

onMounted(async () => {
  // H2-2: 统计数据
  try {
    const r = await fetch('/dev-api/eval/dashboard', {
      headers: { 'Authorization': `Bearer ${document.cookie.match(/Admin-Token=([^;]+)/)?.[1]}` }
    })
    const d = await r.json()
    if (d.data) {
      statCards.value = [
        { label: '项目总数', value: d.data.totalProjects || 0, color: '#409EFF' },
        { label: '评审运行中', value: d.data.runningReviews || 0, color: '#E6A23C' },
        { label: '评审完成', value: d.data.doneReviews || 0, color: '#67C23A' },
        { label: '风险会商', value: d.data.consultationCount || 0, color: '#F56C6C' },
      ]
    }
  } catch (e) { /* ignore */ }

  // H2-3: 项目列表
  projectLoading.value = true
  try {
    const token = document.cookie.match(/Admin-Token=([^;]+)/)?.[1]
    if (token) {
      const r = await fetch('/dev-api/eval/project/list?pageNum=1&pageSize=10', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const d = await r.json()
      projects.value = d.rows || d.data?.rows || []
    }
  } catch (e) { /* ignore */ }
  projectLoading.value = false
})
</script>

<style scoped>
.portal-card { cursor: pointer; transition: all .3s; text-align: center; }
.portal-card:hover { transform: translateY(-4px); box-shadow: 0 4px 12px rgba(0,0,0,.12); }
.portal-icon { font-size: 36px; margin-bottom: 8px; }
.portal-title { font-size: 16px; font-weight: 600; margin-bottom: 6px; }
.portal-desc { font-size: 12px; color: #999; line-height: 1.4; }
.stat-card { text-align: center; }
.stat-value { font-size: 28px; font-weight: 700; }
.stat-label { font-size: 13px; color: #666; margin-top: 4px; }
.activity-item { display: flex; gap: 10px; margin-bottom: 14px; }
.activity-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 6px; flex-shrink: 0; }
.activity-content { flex: 1; }
.activity-text { font-size: 13px; color: #333; }
.activity-time { font-size: 11px; color: #999; margin-top: 2px; }
</style>
