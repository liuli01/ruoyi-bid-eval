<template>
  <div class="app-container">
    <el-card>
      <template #header><span><strong>F3 决策流水线 — 签报生成</strong></span></template>
      <el-form label-width="120px">
        <el-form-item label="项目ID">
          <el-input-number v-model="form.projectId" :min="1" />
        </el-form-item>
        <el-form-item label="评审ID（可选）">
          <el-input-number v-model="form.reviewId" :min="0" />
          <div style="font-size:12px;color:#999;margin-top:4px">不指定则使用项目的最新评审</div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="generateF3" :loading="loading">生成签报</el-button>
          <el-button @click="parseReply" :loading="parsing">解析回复函</el-button>
        </el-form-item>
      </el-form>
      <el-divider />
      <h4>回复函解析结果</h4>
      <div v-if="replyResult">
        <p><strong>总评：</strong>{{ replyResult.summary }}</p>
        <p><strong>建议：</strong>{{ replyResult.recommend }}</p>
        <el-table :data="replyResult.items || []" v-if="replyResult.items" :max-height="300">
          <el-table-column label="会商意见" prop="opinion" :show-overflow-tooltip="true" />
          <el-table-column label="子企业回应" prop="response" :show-overflow-tooltip="true" />
          <el-table-column label="R-T类型" prop="rtType" width="90" />
          <el-table-column label="置信度" prop="confidence" width="80">
            <template #default="s">{{ (s.row.confidence * 100).toFixed(0) }}%</template>
          </el-table-column>
        </el-table>
      </div>
      <el-empty v-else description="点击'解析回复函'分析子企业回复" />
      <el-divider />
      <h4>签报生成流程</h4>
      <el-steps :active="step" align-center>
        <el-step title="会商意见函" />
        <el-step title="子企业回复" />
        <el-step title="签报生成" />
      </el-steps>
    </el-card>
  </div>
</template>

<script setup name="EvalF3">
import { ref, reactive } from 'vue'
import request from '@/utils/request'

const form = reactive({ projectId: 28, reviewId: 0 })
const loading = ref(false)
const parsing = ref(false)
const replyResult = ref(null)
const step = ref(0)

async function parseReply() {
  parsing.value = true; step.value = 1
  try {
    const res = await request({ url:'/portal/f3/parse-reply', method:'post', data:{ projectId: form.projectId, reviewId: form.reviewId } })
    replyResult.value = res.data || res
    step.value = 2
  } finally { parsing.value = false }
}
async function generateF3() {
  loading.value = true
  step.value = 1
  try {
    const res = await request({
      url: '/eval/f3/generate',
      method: 'post',
      data: { projectId: form.projectId, reviewId: form.reviewId },
      responseType: 'blob'
    })
    step.value = 3
    const blob = new Blob([res], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `签报_${form.projectId}.docx`
    link.click()
    URL.revokeObjectURL(link.href)
  } finally {
    loading.value = false
  }
}
</script>
