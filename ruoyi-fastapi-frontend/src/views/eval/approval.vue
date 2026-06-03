<template>
  <div class="app-container">
    <el-form :inline="true">
      <el-form-item><el-button type="primary" icon="Plus" @click="openCreate">新建立项</el-button></el-form-item>
    </el-form>
    <el-table v-loading="loading" :data="list">
      <el-table-column label="编号" prop="id" width="70" />
      <el-table-column label="项目ID" prop="projectId" width="70" />
      <el-table-column label="触发条件" prop="triggerReasons" width="200" />
      <el-table-column label="状态" prop="status" width="140">
        <template #default="s"><el-tag :type="s.row.status==='receipted'?'success':'warning'" size="small">{{ s.row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column label="创建时间" prop="createTime" width="160" />
      <el-table-column label="操作" width="150">
        <template #default="s">
          <el-button type="text" @click="viewDetail(s.row)">详情</el-button>
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
    <el-dialog title="立项详情" v-model="detailOpen" width="700px">
      <div v-if="detail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="项目ID">{{ detail.projectId }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ detail.status }}</el-descriptions-item>
          <el-descriptions-item label="触发条件" :span="2">{{ detail.triggerReasons }}</el-descriptions-item>
          <el-descriptions-item label="经办人意见" :span="2">{{ detail.officerOpinion || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>
<script setup name="EvalApproval">
import { ref, onMounted } from 'vue'
import { listApproval, getApproval, createApproval } from '@/api/eval/portal'
const list = ref([]); const loading = ref(false); const detail = ref(null)
const createOpen = ref(false); const detailOpen = ref(false)
const form = ref({ projectId: 28, triggerReasons: [] })
async function getList() { loading.value=true; const r=await listApproval(); list.value=r.data||r||[]; loading.value=false }
async function openCreate() { createOpen.value=true }
async function submitCreate() { await createApproval(form.value); createOpen.value=false; getList() }
async function viewDetail(row) { detailOpen.value=true; const r=await getApproval(row.id); detail.value=r.data||r }
onMounted(()=>{getList()})
</script>
