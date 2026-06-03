<template>
  <div class="app-container">
    <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch">
      <el-form-item label="项目ID" prop="projectId">
        <el-input v-model="queryParams.projectId" placeholder="按项目ID筛选" clearable style="width: 140px" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-select v-model="queryParams.status" placeholder="评审状态" clearable style="width: 120px">
          <el-option label="已完成" value="done" />
          <el-option label="运行中" value="running" />
          <el-option label="失败" value="error" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-table v-loading="loading" :data="reviewList" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" align="center" />
      <el-table-column label="编号" prop="reviewId" width="70" align="center" />
      <el-table-column label="项目ID" prop="projectId" width="70" align="center" />
      <el-table-column label="模式" prop="reviewMode" width="80" align="center">
        <template #default="s">
          <el-tag size="small">{{ s.row.reviewMode }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" prop="status" width="90" align="center">
        <template #default="s">
          <el-tag :type="s.row.status === 'done' ? 'success' : s.row.status === 'running' ? 'warning' : 'danger'" size="small">
            {{ s.row.status === 'done' ? '完成' : s.row.status === 'running' ? '运行中' : '失败' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="触发规则" prop="triggeredCount" width="80" align="center" />
      <el-table-column label="无法判断" prop="insufficientCount" width="80" align="center" />
      <el-table-column label="LLM调用" prop="llmCalls" width="70" align="center" />
      <el-table-column label="耗时" prop="elapsedSec" width="80" align="center">
        <template #default="s">{{ s.row.elapsedSec || '-' }}s</template>
      </el-table-column>
      <el-table-column label="创建人" prop="createBy" width="100" align="center" />
      <el-table-column label="创建时间" prop="createTime" width="160" align="center" />
      <el-table-column label="操作" width="200" align="center" fixed="right">
        <template #default="s">
          <el-button type="text" icon="View" @click="viewOpinions(s.row)">意见</el-button>
          <el-button type="text" icon="Download" @click="handleExport(s.row)">导出</el-button>
        </template>
      </el-table-column>
    </el-table>

    <pagination v-show="total > 0" :total="total" v-model:page="queryParams.pageNum" v-model:limit="queryParams.pageSize" @pagination="getList" />

    <!-- 评审意见弹窗 -->
    <el-dialog title="评审意见" v-model="opinionOpen" width="900px" append-to-body top="5vh">
      <div v-if="currentReview">
        <el-descriptions :column="4" border size="small">
          <el-descriptions-item label="评审编号">{{ currentReview.reviewId }}</el-descriptions-item>
          <el-descriptions-item label="项目ID">{{ currentReview.projectId }}</el-descriptions-item>
          <el-descriptions-item label="模式">{{ currentReview.reviewMode }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="currentReview.status === 'done' ? 'success' : 'warning'" size="small">{{ currentReview.status }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <el-divider />
        <el-table :data="opinions" v-loading="opinionLoading" empty-text="暂无意见" :max-height="500">
          <el-table-column label="规则" prop="ruleId" width="90" />
          <el-table-column label="部门" prop="department" width="90" />
          <el-table-column label="摘要" prop="title" :show-overflow-tooltip="true" />
          <el-table-column label="风险" prop="riskLevel" width="70">
            <template #default="s">
              <el-tag :type="s.row.riskLevel === 'high' ? 'danger' : s.row.riskLevel === 'medium' ? 'warning' : 'info'" size="small">{{ s.row.riskLevel }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="s">
              <el-button type="text" @click="showDetail = s.row">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div style="margin-top: 16px; text-align: right">
          <el-button type="primary" icon="Download" @click="handleExport(currentReview)">导出 Word</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 意见详情弹窗 -->
    <el-dialog title="意见详情" :model-value="showDetail !== null" @update:model-value="showDetail = null" width="700px" append-to-body>
      <div v-if="showDetail">
        <p><strong>规则编号：</strong>{{ showDetail.ruleId }}</p>
        <p><strong>所属部门：</strong>{{ showDetail.department }}</p>
        <p><strong>风险等级：</strong>
          <el-tag :type="showDetail.riskLevel === 'high' ? 'danger' : showDetail.riskLevel === 'medium' ? 'warning' : 'info'" size="small">{{ showDetail.riskLevel }}</el-tag>
        </p>
        <p><strong>判定依据：</strong></p>
        <el-input type="textarea" :rows="6" :model-value="showDetail.evidence || showDetail.content" readonly />
      </div>
      <template #footer>
        <el-button @click="showDetail = null">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="EvalReview">
import { listReview, getReviewOpinions, exportReview } from '@/api/eval/review'

const reviewList = ref([])
const opinions = ref([])
const currentReview = ref(null)
const showDetail = ref(null)
const loading = ref(false)
const opinionLoading = ref(false)
const opinionOpen = ref(false)
const showSearch = ref(true)
const ids = ref([])
const total = ref(0)

const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  projectId: undefined,
  status: undefined
})

function getList() {
  loading.value = true
  listReview(queryParams).then(res => {
    const data = res.data || res
    reviewList.value = data.rows || data || []
    total.value = data.total || reviewList.value.length
    loading.value = false
  }).catch(() => { loading.value = false })
}

function handleSelectionChange(selection) {
  ids.value = selection.map(i => i.reviewId)
}

function viewOpinions(row) {
  currentReview.value = row
  opinionOpen.value = true
  opinionLoading.value = true
  getReviewOpinions(row.reviewId).then(res => {
    const d = res.data || res
    opinions.value = Array.isArray(d) ? d : []
    opinionLoading.value = false
  }).catch(() => { opinionLoading.value = false })
}

function handleExport(row) {
  exportReview(row.reviewId).then(res => {
    const blob = new Blob([res], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `评审意见_${row.reviewId}.docx`
    link.click()
    URL.revokeObjectURL(link.href)
  })
}

function handleQuery() {
  queryParams.pageNum = 1
  getList()
}

function resetQuery() {
  queryParams.projectId = undefined
  queryParams.status = undefined
  handleQuery()
}

onMounted(() => { getList() })
</script>
