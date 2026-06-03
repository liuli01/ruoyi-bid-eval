<template>
  <div class="app-container">
    <el-form :inline="true">
      <el-form-item>
        <el-button type="primary" icon="Plus" @click="openCreate">新建会商</el-button>
      </el-form-item>
    </el-form>

    <el-table v-loading="loading" :data="list" @expand-change="loadDetail">
      <el-table-column type="expand" width="30">
        <template #default="s">
          <div v-if="detail && detail.id === s.row.id" style="padding:12px 20px">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="经办人">{{ detail.initiator }}</el-descriptions-item>
              <el-descriptions-item label="状态">{{ statusLabel(detail.status) }}</el-descriptions-item>
              <el-descriptions-item label="经办人意见" :span="2">{{ detail.officerOpinion || '-' }}</el-descriptions-item>
              <el-descriptions-item label="领导意见" :span="2">{{ detail.leaderOpinion || '-' }}</el-descriptions-item>
              <el-descriptions-item label="核稿意见" :span="2">{{ detail.officeOpinion || '-' }}</el-descriptions-item>
            </el-descriptions>
            <div v-if="detail.draftDoc" style="margin-top:8px">
              <h4>发函草稿</h4>
              <pre style="background:#f5f7fa;padding:12px;white-space:pre-wrap">{{ detail.draftDoc }}</pre>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="编号" prop="id" width="70" />
      <el-table-column label="项目ID" prop="projectId" width="70" />
      <el-table-column label="经办人" prop="initiator" width="120" />
      <el-table-column label="状态" prop="status" width="140">
        <template #default="s">
          <el-tag :type="tagType(s.row.status)" size="small">{{ statusLabel(s.row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" prop="createTime" width="160" />
      <el-table-column label="操作" width="300">
        <template #default="s">
          <el-button v-if="canAction(s.row.status, 'officer_review')" type="text" @click="doAction(s.row, 'officer_review')">经办人审核</el-button>
          <el-button v-if="canAction(s.row.status, 'draft_doc')" type="text" @click="doAction(s.row, 'draft_doc')">拟稿</el-button>
          <el-button v-if="canAction(s.row.status, 'leader_approval')" type="text" @click="doAction(s.row, 'leader_approval')">领导审批</el-button>
          <el-button v-if="canAction(s.row.status, 'office_review')" type="text" @click="doAction(s.row, 'office_review')">核稿</el-button>
          <el-button v-if="canAction(s.row.status, 'submit')" type="text" @click="doAction(s.row, 'submit')">报送商务部</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog title="新建会商" v-model="createOpen" width="600px">
      <el-form label-width="100px">
        <el-form-item label="项目ID">
          <el-input-number v-model="form.projectId" :min="1" />
        </el-form-item>
        <el-form-item label="经办人">
          <el-input v-model="form.initiator" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createOpen=false">取消</el-button>
        <el-button type="primary" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog title="会商操作" v-model="actionOpen" width="600px">
      <p style="margin-bottom:12px;color:#666">{{ actionLabel }}</p>
      <el-input v-model="actionOpinion" type="textarea" :rows="5" :placeholder="actionPlaceholder" />
      <template #footer>
        <el-button @click="actionOpen=false">取消</el-button>
        <el-button type="primary" @click="submitAction">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="EvalConsultation">
import { ref, onMounted } from 'vue'
import { listConsultation, createConsultation, getConsultation, approveConsultation } from '@/api/eval/portal'

const list = ref([])
const detail = ref(null)
const loading = ref(false)
const createOpen = ref(false)
const actionOpen = ref(false)
const actionRow = ref(null)
const actionType = ref('')
const actionOpinion = ref('')
const form = ref({ projectId: 28, initiator: '' })

const STATUS = {
  draft:'草稿', officer_review:'经办人审核', draft_doc:'拟稿中',
  leader_approval:'领导审批', office_review:'核稿中', submitted:'已报送', receipted:'已回执'
}
function statusLabel(s) { return STATUS[s] || s }
function tagType(s) { return s === 'submitted'||s==='receipted' ? 'success' : s==='draft' ? 'info' : 'warning' }
function canAction(status, action) {
  const flow = ['draft','officer_review','draft_doc','leader_approval','office_review','submitted']
  return flow.indexOf(status) === flow.indexOf(action) - 1
}

const actionLabel = ref('')
const actionPlaceholder = ref('')
function doAction(row, type) {
  actionRow.value = row; actionType.value = type; actionOpinion.value = ''
  const labels = { officer_review:'填写审核意见', draft_doc:'起草发函内容', leader_approval:'审批意见', office_review:'核稿意见', submit:'确认报送' }
  actionLabel.value = labels[type] || type
  actionPlaceholder.value = type === 'draft_doc' ? '起草会商意见函...' : '请输入意见...'
  actionOpen.value = true
}
async function submitAction() {
  await approveConsultation(actionRow.value.id, { action: actionType.value, opinion: actionOpinion.value })
  actionOpen.value = false; getList()
}
function openCreate() { createOpen.value = true }
async function submitCreate() {
  await createConsultation(form.value); createOpen.value = false; getList()
}
async function getList() {
  loading.value = true; const r = await listConsultation()
  list.value = r.data || r || []; loading.value = false
}
async function loadDetail(row) {
  const r = await getConsultation(row.id)
  detail.value = r.data || r
}
onMounted(() => { getList() })
</script>
