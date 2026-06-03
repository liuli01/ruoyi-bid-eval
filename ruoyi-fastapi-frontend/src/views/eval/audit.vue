<template>
  <div class="app-container">
    <el-form :inline="true">
      <el-form-item label="项目ID">
        <el-input-number v-model="projectId" :min="1" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="loadAudit">查询</el-button>
      </el-form-item>
    </el-form>

    <el-timeline v-if="timeline.length > 0">
      <el-timeline-item v-for="item in timeline" :key="item.id" :timestamp="item.time" :type="item.status === 'done' || item.status === 'success' ? 'success' : item.status === 'error' ? 'danger' : 'info'">
        <h4>{{ item.action }}</h4>
        <p style="color:#666;font-size:13px">{{ item.detail }}</p>
      </el-timeline-item>
    </el-timeline>
    <el-empty v-else description="无审计记录" />
  </div>
</template>

<script setup name="EvalAudit">
import { ref } from 'vue'
import request from '@/utils/request'

const projectId = ref(28)
const timeline = ref([])
async function loadAudit() {
  const res = await request({ url: `/eval/audit/${projectId.value}`, method: 'get' })
  timeline.value = res.data || res || []
}
</script>
