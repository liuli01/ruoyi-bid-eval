<template>
  <div class="app-container">
    <el-form :inline="true">
      <el-form-item><el-button type="primary" icon="Plus" @click="openCreate">新建立项</el-button></el-form-item>
    </el-form>
    <el-table v-loading="loading" :data="list" @expand-change="loadDetail">
      <el-table-column type="expand" width="30">
        <template #default="s">
          <div v-if="detail && detail.id === s.row.id" style="padding:12px 20px">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="触发条件" :span="2">{{ detail.triggerReasons }}</el-descriptions-item>
              <el-descriptions-item label="经办人意见" :span="2">{{ detail.officerOpinion || '-' }}</el-descriptions-item>
              <el-descriptions-item label="领导意见" :span="2">{{ detail.leaderOpinion || '-' }}</el-descriptions-item>
              <el-descriptions-item label="核稿意见" :span="2">{{ detail.officeOpinion || '-' }}</el-descriptions-item>
            </el-descriptions>
            <el-button type="text" icon="Upload" @click="uploadFiles(detail.projectId)" style="margin-top:8px">上传材料</el-button>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="编号" prop="id" width="70" />
      <el-table-column label="项目ID" prop="projectId" width="70" />
      <el-table-column label="触发条件" prop="triggerReasons" width="200" />
      <el-table-column label="状态" prop="status" width="140">
        <template #default="s"><el-tag :type="s.row.status==='receipted'?'success':'warning'" size="small">{{ s.row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column label="创建时间" prop="createTime" width="160" />
      <el-table-column label="操作" width="350">
        <template #default="s">
          <el-button v-if="canAction(s.row.status,'officer_review')" type="text" @click="doAction(s.row,'officer_review')">经办人</el-button>
          <el-button v-if="canAction(s.row.status,'draft_doc')" type="text" @click="doAction(s.row,'draft_doc')">拟稿</el-button>
          <el-button v-if="canAction(s.row.status,'leader_approval')" type="text" @click="doAction(s.row,'leader_approval')">领导审批</el-button>
          <el-button v-if="canAction(s.row.status,'office_review')" type="text" @click="doAction(s.row,'office_review')">核稿</el-button>
          <el-button v-if="canAction(s.row.status,'submit')" type="text" @click="doAction(s.row,'submit')">报送</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog title="新建立项" v-model="createOpen" width="500px">
      <el-form label-width="120px">
        <el-form-item label="项目ID"><el-input-number v-model="form.projectId" :min="1" /></el-form-item>
        <el-form-item label="触发条件">
          <el-checkbox-group v-model="form.triggerReasons">
            <el-checkbox value="high_risk">高风险地区</el-checkbox>
            <el-checkbox value="cross_border">跨境项目</el-checkbox>
            <el-checkbox value="territory_dispute">领土争议</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createOpen=false">取消</el-button>
        <el-button type="primary" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog title="立项操作" v-model="actionOpen" width="600px">
      <p style="color:#666;margin-bottom:12px">{{ actionLabel }}</p>
      <el-input v-model="actionOpinion" type="textarea" :rows="5" :placeholder="actionPlaceholder" />
      <template #footer>
        <el-button @click="actionOpen=false">取消</el-button>
        <el-button type="primary" @click="submitAction">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script setup name="EvalApproval">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listApproval, getApproval, createApproval } from '@/api/eval/portal'
import request from '@/utils/request'

const router = useRouter()
const list = ref([]); const loading = ref(false); const detail = ref(null)
const createOpen = ref(false); const actionOpen = ref(false); const actionRow = ref(null); const actionType = ref(''); const actionOpinion = ref('')
const form = ref({ projectId: 28, triggerReasons: [] })

const STATUS = { draft:'草稿', officer_review:'经办人审核', draft_doc:'拟稿中', leader_approval:'领导审批', office_review:'核稿中', submitted:'已报送', receipted:'已批复' }
function canAction(status, action) {
  const flow = ['draft','officer_review','draft_doc','leader_approval','office_review','submitted']
  return flow.indexOf(status) === flow.indexOf(action) - 1
}
const actionLabel = ref(''); const actionPlaceholder = ref('')
function doAction(row, type) {
  actionRow.value=row; actionType.value=type; actionOpinion.value=''
  const labels = { officer_review:'填写审核意见', draft_doc:'起草立项函', leader_approval:'审批意见', office_review:'核稿意见', submit:'确认报送' }
  actionLabel.value = labels[type]||type; actionPlaceholder.value = type==='draft_doc'?'起草...':'请输入意见...'
  actionOpen.value=true
}
async function submitAction() {
  await request({ url:`/portal/approval/${actionRow.value.id}/approve`, method:'post', data:{ action:actionType.value, opinion:actionOpinion.value } })
  actionOpen.value=false; getList()
}
function uploadFiles(pid) { router.push(`/eval/project?projectId=${pid}`) }
function openCreate() { createOpen.value=true }
async function submitCreate() { await createApproval(form.value); createOpen.value=false; getList() }
async function loadDetail(row) { const r=await getApproval(row.id); detail.value=r.data||r }
async function getList() { loading.value=true; const r=await listApproval(); list.value=r.data||r||[]; loading.value=false }
onMounted(()=>{getList()})
</script>
