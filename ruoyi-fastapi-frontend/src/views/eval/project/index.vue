<template>
  <div class="app-container">
    <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch">
      <el-form-item label="项目名称" prop="projectName">
        <el-input v-model="queryParams.projectName" placeholder="请输入项目名称" clearable style="width: 200px" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="国别" prop="country">
        <el-input v-model="queryParams.country" placeholder="请输入国别" clearable style="width: 160px" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-select v-model="queryParams.status" placeholder="项目状态" clearable style="width: 140px">
          <el-option label="待处理" value="pending" />
          <el-option label="评审中" value="running" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5">
        <el-button type="primary" plain icon="Plus" @click="handleAdd" v-hasPermi="['eval:project:add']">新增</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button type="danger" plain icon="Delete" :disabled="multiple" @click="handleDelete" v-hasPermi="['eval:project:remove']">删除</el-button>
      </el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList" />
    </el-row>

    <el-table v-loading="loading" :data="projectList" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" align="center" />
      <el-table-column label="编号" align="center" prop="projectId" width="80" />
      <el-table-column label="项目名称" align="center" prop="projectName" :show-overflow-tooltip="true" />
      <el-table-column label="国别" align="center" prop="country" width="120" />
      <el-table-column label="合同金额" align="center" prop="amount" width="120" />
      <el-table-column label="模式" align="center" prop="mode" width="100" />
      <el-table-column label="状态" align="center" prop="status" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.status === 'completed' ? 'success' : scope.row.status === 'running' ? 'warning' : 'info'">
            {{ scope.row.status === 'completed' ? '已完成' : scope.row.status === 'running' ? '评审中' : scope.row.status === 'failed' ? '失败' : '待处理' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" align="center" prop="createTime" width="160" />
      <el-table-column label="操作" align="center" width="280">
        <template #default="scope">
          <el-button type="text" icon="View" @click="handleDetail(scope.row)">查看</el-button>
          <el-button type="text" icon="Upload" @click="handleStartReview(scope.row)" v-hasPermi="['eval:review:start']">评审</el-button>
          <el-button type="text" icon="Delete" @click="handleDelete" v-hasPermi="['eval:project:remove']">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <pagination v-show="total > 0" :total="total" v-model:page="queryParams.pageNum" v-model:limit="queryParams.pageSize" @pagination="getList" />

    <!-- 新增项目弹窗 -->
    <el-dialog title="新增项目" v-model="open" width="600px" append-to-body>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="项目名称" prop="projectName">
          <el-input v-model="form.projectName" placeholder="请输入项目名称" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="国别" prop="country">
              <el-input v-model="form.country" placeholder="请输入国别" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="合同金额" prop="amount">
              <el-input v-model="form.amount" placeholder="如：5亿" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="阶段" prop="stage">
              <el-select v-model="form.stage" placeholder="请选择" style="width: 100%">
                <el-option label="投标" value="投标" />
                <el-option label="合同" value="合同" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="模式" prop="mode">
              <el-select v-model="form.mode" placeholder="请选择" style="width: 100%">
                <el-option label="EPC" value="EPC" />
                <el-option label="DB" value="DB" />
                <el-option label="D&B" value="D&B" />
                <el-option label="施工总承包" value="施工总承包" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="cancel">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- 项目详情弹窗 -->
    <el-dialog title="项目详情" v-model="detailOpen" width="800px" append-to-body top="5vh">
      <div v-if="currentProject">
        <el-tabs v-model="detailTab">
          <el-tab-pane label="项目信息" name="info">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="项目名称">{{ currentProject.projectName }}</el-descriptions-item>
              <el-descriptions-item label="国别">{{ currentProject.country }}</el-descriptions-item>
              <el-descriptions-item label="合同金额">{{ currentProject.amount }}</el-descriptions-item>
              <el-descriptions-item label="模式">{{ currentProject.mode }}</el-descriptions-item>
              <el-descriptions-item label="阶段">{{ currentProject.stage }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="currentProject.status === 'completed' ? 'success' : 'info'">{{ currentProject.status }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="创建人">{{ currentProject.createBy }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ currentProject.createTime }}</el-descriptions-item>
            </el-descriptions>
          </el-tab-pane>

          <el-tab-pane label="上传材料" name="materials">
            <el-upload
              :action="`/dev-api/eval/project/${currentProject.projectId}/upload`"
              :headers="{ Authorization: 'Bearer ' + getToken() }"
              :on-success="handleUploadSuccess"
              multiple
              drag
            >
              <el-icon class="el-icon--upload"><upload-filled /></el-icon>
              <div class="el-upload__text">拖拽文件到此处，或<em>点击上传</em></div>
              <template #tip>
                <div class="el-upload__tip">支持 PDF / DOCX / TXT / XLSX / ZIP / RAR，单个文件 ≤ 50MB</div>
              </template>
            </el-upload>
            <el-table :data="materials" v-loading="materialLoading" empty-text="暂无材料" style="margin-top: 12px">
              <el-table-column label="文件名" prop="fileName" :show-overflow-tooltip="true" />
              <el-table-column label="分类" prop="category" width="100" />
              <el-table-column label="大小" prop="fileSize" width="100">
                <template #default="s">{{ (s.row.fileSize / 1024).toFixed(1) }}KB</template>
              </el-table-column>
              <el-table-column label="解析状态" prop="parseStatus" width="100">
                <template #default="s">
                  <el-tag :type="s.row.parseStatus === 'done' ? 'success' : 'danger'" size="small">{{ s.row.parseStatus }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80">
                <template #default="s">
                  <el-button type="text" icon="Download" @click="downloadMaterial(s.row)">下载</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="评审历史" name="reviews">
        <el-table :data="reviewHistory" v-loading="historyLoading" empty-text="暂无评审记录">
          <el-table-column label="编号" prop="reviewId" width="80" />
          <el-table-column label="模式" prop="reviewMode" width="100" />
          <el-table-column label="状态" prop="status" width="80">
            <template #default="s">
              <el-tag :type="s.row.status === 'done' ? 'success' : 'warning'">{{ s.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="触发规则" prop="triggeredCount" width="80" />
          <el-table-column label="耗时(秒)" prop="elapsedSec" width="80" />
          <el-table-column label="创建时间" prop="createTime" width="160" />
          <el-table-column label="操作" width="200">
            <template #default="s">
              <el-button type="text" icon="View" @click="viewReview(s.row)">意见</el-button>
              <el-button type="text" icon="TrendCharts" @click="viewProgress(s.row)">进度</el-button>
              <el-button type="text" icon="Download" @click="handleExport(s.row)">导出</el-button>
            </template>
          </el-table-column>
        </el-table>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>

    <!-- 评审结果弹窗 -->
    <el-dialog title="评审结果" v-model="reviewOpen" width="900px" append-to-body top="5vh">
      <div v-if="currentReview">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="评审编号">{{ currentReview.reviewId }}</el-descriptions-item>
          <el-descriptions-item label="模式">{{ currentReview.reviewMode }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="currentReview.status === 'done' ? 'success' : 'warning'">{{ currentReview.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="触发规则">{{ currentReview.triggeredCount || 0 }}</el-descriptions-item>
          <el-descriptions-item label="无法判断">{{ currentReview.insufficientCount || 0 }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ currentReview.elapsedSec || '-' }}s</el-descriptions-item>
        </el-descriptions>

        <el-divider />
        <h4>评审意见</h4>
        <el-table :data="opinions" v-loading="opinionsLoading" empty-text="暂无意见" :max-height="400">
          <el-table-column label="规则编号" prop="ruleId" width="100" />
          <el-table-column label="部门" prop="department" width="100" />
          <el-table-column label="意见摘要" prop="title" :show-overflow-tooltip="true" />
          <el-table-column label="风险等级" prop="riskLevel" width="90">
            <template #default="s">
              <el-tag :type="s.row.riskLevel === 'high' ? 'danger' : s.row.riskLevel === 'medium' ? 'warning' : 'info'" size="small">{{ s.row.riskLevel }}</el-tag>
            </template>
          </el-table-column>
        </el-table>

        <div style="margin-top: 16px; text-align: right">
          <el-button type="primary" icon="Download" @click="handleExport(currentReview)">导出 Word</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup name="EvalProject">
import { listProject, addProject, delProject, getProject } from '@/api/eval/project'
import { startReview, getReview, getReviewOpinions, exportReview, getProjectReviews } from '@/api/eval/review'
import { listMaterials, downloadMaterial as dm } from '@/api/eval/material'
import { useRouter } from 'vue-router'

const { proxy } = getCurrentInstance()
const router = useRouter()

const projectList = ref([])
const reviewHistory = ref([])
const opinions = ref([])
const currentProject = ref(null)
const currentReview = ref(null)
const materials = ref([])
const materialLoading = ref(false)
const detailTab = ref('info')
const loading = ref(true)
const historyLoading = ref(false)
const opinionsLoading = ref(false)
const showSearch = ref(true)
const ids = ref([])
const single = ref(true)
const multiple = ref(true)
const total = ref(0)
const open = ref(false)
const detailOpen = ref(false)
const reviewOpen = ref(false)

const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  projectName: undefined,
  country: undefined,
  status: undefined
})

const form = reactive({
  projectName: undefined,
  country: undefined,
  amount: undefined,
  stage: undefined,
  mode: undefined
})

const rules = {
  projectName: [{ required: true, message: '项目名称不能为空', trigger: 'blur' }]
}

function getList() {
  loading.value = true
  listProject(queryParams).then(res => {
    const data = res.data || res
    projectList.value = data.rows || data || []
    total.value = data.total || projectList.value.length
    loading.value = false
  }).catch(() => { loading.value = false })
}

function handleSelectionChange(selection) {
  ids.value = selection.map(item => item.projectId)
  single.value = selection.length !== 1
  multiple.value = !selection.length
}

function handleAdd() {
  open.value = true
}

function submitForm() {
  if (!form.projectName) return
  addProject(form).then(res => {
    if (res.code === 200) {
      proxy.$modal.msgSuccess('新增成功')
      open.value = false
      getList()
    }
  })
}

function cancel() {
  open.value = false
}

function handleDelete(row) {
  const delIds = row.projectId ? [row.projectId] : ids.value
  if (!delIds.length) return
  proxy.$modal.confirm('确认删除所选项目？').then(() => {
    return delProject(delIds[0])
  }).then(() => {
    getList()
    proxy.$modal.msgSuccess('删除成功')
  }).catch(() => {})
}

function handleDetail(row) {
  detailOpen.value = true
  currentProject.value = row
  detailTab.value = 'info'
  loadMaterials(row.projectId)
  historyLoading.value = true
  getProjectReviews(row.projectId).then(res => {
    const data = res.data || res
    reviewHistory.value = Array.isArray(data) ? data : []
    historyLoading.value = false
  }).catch(() => { historyLoading.value = false })
}

function handleStartReview(row) {
  proxy.$modal.confirm(`确认对项目「${row.projectName}」启动评审？`).then(() => {
    return startReview({ projectId: row.projectId, reviewMode: 'standard' })
  }).then(res => {
    proxy.$modal.msgSuccess('评审已启动')
    getList()
  }).catch(() => {})
}

function viewReview(row) {
  reviewOpen.value = true
  currentReview.value = row
  opinionsLoading.value = true
  getReviewOpinions(row.reviewId).then(res => {
    const data = res.data || res
    opinions.value = Array.isArray(data) ? data : []
    opinionsLoading.value = false
  }).catch(() => { opinionsLoading.value = false })
}

function loadMaterials(pid) {
  materialLoading.value = true
  listMaterials(pid).then(res => {
    const d = res.data || res
    materials.value = Array.isArray(d) ? d : []
    materialLoading.value = false
  }).catch(() => { materialLoading.value = false })
}

function handleUploadSuccess() {
  loadMaterials(currentProject.value.projectId)
}

function downloadMaterial(row) {
  dm(row.materialId).then(res => {
    const blob = new Blob([res])
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = row.fileName
    link.click()
    URL.revokeObjectURL(link.href)
  })
}

function getToken() {
  return JSON.parse(localStorage.getItem('user-info') || '{}').token || ''
}

function viewProgress(row) {
  router.push(`/eval/review-progress/${row.reviewId}`)
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
  queryParams.projectName = undefined
  queryParams.country = undefined
  queryParams.status = undefined
  handleQuery()
}

onMounted(() => {
  getList()
})
</script>
