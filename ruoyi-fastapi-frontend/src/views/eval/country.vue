<template>
  <div class="app-container">
    <el-form :inline="true">
      <el-form-item><el-button type="primary" icon="Plus" @click="openAdd">新增国别</el-button></el-form-item>
    </el-form>
    <el-table v-loading="loading" :data="list" @selection-change="ids=$event.map(i=>i.id)">
      <el-table-column type="selection" width="50" />
      <el-table-column label="名称" prop="countryName" width="140" />
      <el-table-column label="代码" prop="countryCode" width="80" />
      <el-table-column label="区域" prop="region" width="120" />
      <el-table-column label="风险等级" prop="riskLevel" width="100">
        <template #default="s">
          <el-tag :type="s.row.riskLevel==='high'?'danger':s.row.riskLevel==='medium'?'warning':'success'" size="small">{{ s.row.riskLevel }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="政治体制" prop="politicalSystem" width="180" />
      <el-table-column label="选举周期" prop="electionCycle" width="100" />
      <el-table-column label="排序" prop="sortOrder" width="60" />
      <el-table-column label="操作" width="200">
        <template #default="s">
          <el-button type="text" @click="editRow(s.row)">编辑</el-button>
          <el-button type="text" @click="delRow(s.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog :title="editId?'编辑国别':'新增国别'" v-model="dialogOpen" width="600px">
      <el-form label-width="120px">
        <el-form-item label="国别名称"><el-input v-model="form.countryName" /></el-form-item>
        <el-form-item label="国别代码"><el-input v-model="form.countryCode" maxlength="10" style="width:120px" /></el-form-item>
        <el-form-item label="区域"><el-input v-model="form.region" /></el-form-item>
        <el-form-item label="风险等级">
          <el-select v-model="form.riskLevel" style="width:140px">
            <el-option label="低风险" value="low" />
            <el-option label="中风险" value="medium" />
            <el-option label="高风险" value="high" />
          </el-select>
        </el-form-item>
        <el-form-item label="政治体制"><el-input v-model="form.politicalSystem" /></el-form-item>
        <el-form-item label="选举周期"><el-input v-model="form.electionCycle" style="width:120px" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sortOrder" :min="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen=false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script setup name="EvalCountry">
import { ref, reactive, onMounted } from 'vue'
import request from '@/utils/request'

const list = ref([]); const loading = ref(false); const ids = ref([])
const dialogOpen = ref(false); const editId = ref(null)
const form = reactive({ countryName:'', countryCode:'', region:'', riskLevel:'medium', politicalSystem:'', electionCycle:'', sortOrder:0 })

async function getList() { loading.value=true; const r=await request({url:'/eval/country',method:'get'}); list.value=r.data||r||[]; loading.value=false }
function openAdd() { editId.value=null; Object.assign(form, {countryName:'',countryCode:'',region:'',riskLevel:'medium',politicalSystem:'',electionCycle:'',sortOrder:0}); dialogOpen.value=true }
function editRow(r) { editId.value=r.id; Object.assign(form, r); dialogOpen.value=true }
async function save() {
  if (editId.value) await request({url:`/eval/country/${editId.value}`,method:'put',data:form})
  else await request({url:'/eval/country',method:'post',data:form})
  dialogOpen.value=false; getList()
}
async function delRow(r) { await request({url:`/eval/country/${r.id}`,method:'delete'}); getList() }
onMounted(()=>{getList()})
</script>
