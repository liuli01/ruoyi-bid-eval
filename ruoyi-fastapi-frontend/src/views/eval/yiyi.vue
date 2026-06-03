<template>
  <div class="app-container">
    <el-form :inline="true">
      <el-form-item><el-button type="primary" icon="Plus" @click="openCreate">新建申请</el-button></el-form-item>
    </el-form>
    <el-table v-loading="loading" :data="list">
      <el-table-column label="编号" prop="id" width="70" />
      <el-table-column label="项目ID" prop="projectId" width="70" />
      <el-table-column label="承接模式" prop="applyType" width="120" />
      <el-table-column label="状态" prop="status" width="140">
        <template #default="s">
          <el-tag :type="s.row.status==='approved'?'success':s.row.status==='rejected'?'danger':'warning'" size="small">{{ statusLabel(s.row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" prop="createTime" width="160" />
      <el-table-column label="操作" width="280">
        <template #default="s">
          <el-button type="text" @click="viewDetail(s.row)">详情</el-button>
          <el-button v-if="s.row.status==='draft'" type="text" @click="runCheck(s.row)">受理核验</el-button>
          <el-button v-if="s.row.status==='draft'" type="text" @click="runLlmCheck(s.row)">LLM核验</el-button>
          <el-button v-if="s.row.status==='reviewing'" type="text" @click="openApprove(s.row)">审批</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog title="新建申请" v-model="createOpen" width="500px">
      <el-form label-width="120px">
        <el-form-item label="项目ID"><el-input-number v-model="form.projectId" :min="1" /></el-form-item>
        <el-form-item label="承接模式">
          <el-radio-group v-model="form.applyType">
            <el-radio value="股份公司">股份公司</el-radio>
            <el-radio value="非股份公司">非股份公司</el-radio>
            <el-radio value="分包">分包</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createOpen=false">取消</el-button>
        <el-button type="primary" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog title="受理条件核验" v-model="checkOpen" width="650px">
      <div v-if="checkResult">
        <div v-for="(v,k) in checkResult.checks" :key="k" class="check-item">
          <el-tag :type="v.pass?'success':'danger'" size="small" style="margin-right:8px">{{ v.pass?'通过':'不通过' }}</el-tag>
          <strong>{{ checkLabel(k) }}</strong>：{{ v.value }} <span style="color:#999">(阈值: {{ v.threshold }})</span>
        </div>
        <el-alert v-if="checkResult.passed" title="全部通过，可进入审批" type="success" show-icon style="margin-top:16px" />
        <el-alert v-else title="存在不通过项，申请被驳回" type="error" show-icon style="margin-top:16px" />
      </div>
      <template #footer>
        <el-button @click="checkOpen=false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog title="审批" v-model="approveOpen" width="500px">
      <el-input v-model="approveOpinion" type="textarea" :rows="4" placeholder="审批意见" />
      <template #footer>
        <el-button @click="approveOpen=false">取消</el-button>
        <el-button type="success" @click="submitApprove('approve')">同意</el-button>
        <el-button type="danger" @click="submitApprove('reject')">拒绝</el-button>
      </template>
    </el-dialog>

    <el-dialog title="详情" v-model="detailOpen" width="700px">
      <div v-if="detail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="项目ID">{{ detail.projectId }}</el-descriptions-item>
          <el-descriptions-item label="承接模式">{{ detail.applyType }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusLabel(detail.status) }}</el-descriptions-item>
          <el-descriptions-item label="经办人意见" :span="2">{{ detail.officerOpinion || '-' }}</el-descriptions-item>
          <el-descriptions-item label="领导意见" :span="2">{{ detail.leaderOpinion || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>
<script setup name="EvalYiyi">
import { ref, onMounted } from 'vue'
import { listYiyi, createYiyi, getYiyi, checkYiyi, approveYiyi } from '@/api/eval/portal'
import request from '@/utils/request'
const list = ref([]); const loading = ref(false); const detail = ref(null); const actionRow = ref(null)
const createOpen = ref(false); const detailOpen = ref(false); const checkOpen = ref(false); const approveOpen = ref(false)
const checkResult = ref(null); const approveOpinion = ref('')
const form = ref({ projectId: 28, applyType: '股份公司', profitRate: 7 })

const STATUS = { draft:'草稿', pending_accept:'待受理', accept_rejected:'受理不通过', reviewing:'审核中', approved:'已批复', rejected:'已拒绝' }
function statusLabel(s) { return STATUS[s]||s }

const CHECK_LABELS = { market_category:'市场分类', safety_level:'安全等级', amount_threshold:'合同额门槛', funding:'资金落实', bid_procedure:'招标程序', compliance:'合规风险', org_setup:'机构设置', profit_rate:'利润率', payment_terms:'付款条件', penalty:'工期罚款' }
function checkLabel(k) { return CHECK_LABELS[k]||k }

async function getList() { loading.value=true; const r=await listYiyi(); list.value=r.data||r||[]; loading.value=false }
function openCreate() { createOpen.value=true }
async function submitCreate() {
  if (!form.value.applyType) return
  await createYiyi(form.value); createOpen.value=false; getList()
}
async function viewDetail(row) { detailOpen.value=true; const r=await getYiyi(row.id); detail.value=r.data||r }
async function runLlmCheck(row) {
  const r = await request({ url:`/portal/yiyi/${row.id}/llm-check`, method:'post' })
  checkResult.value = r.data || r; checkOpen.value = true; getList()
}
async function runCheck(row) {
  const params = { applyType: row.applyType, profitRate: 7, paymentTerms: 85, penaltyRate: 5 }
  const r = await checkYiyi(row.id, params); checkResult.value = r.data||r; checkOpen.value=true; getList()
}
function openApprove(row) { actionRow.value=row; approveOpinion.value=''; approveOpen.value=true }
async function submitApprove(action) {
  await approveYiyi(actionRow.value.id, { action, opinion: approveOpinion.value })
  approveOpen.value=false; getList()
}
onMounted(()=>{getList()})
</script>
<style scoped>
.check-item { padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
</style>
