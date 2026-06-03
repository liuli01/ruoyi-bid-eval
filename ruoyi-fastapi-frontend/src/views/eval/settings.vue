<template>
  <div class="app-container">
    <el-card shadow="hover">
      <template #header><span><strong>LLM 配置</strong></span></template>
      <el-form label-width="140px">
        <el-form-item label="模型名称">
          <el-input v-model="form.llmModel" placeholder="deepseek-chat" style="max-width:400px" />
          <div class="el-form-item-msg">如 deepseek-chat / deepseek-v4-flash / gpt-4o</div>
        </el-form-item>
        <el-form-item label="API 地址">
          <el-input v-model="form.llmBaseUrl" placeholder="https://api.deepseek.com" style="max-width:400px" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="form.llmApiKey" type="password" show-password placeholder="sk-..." style="max-width:400px" />
          <div class="el-form-item-msg">当前 {{ llmConfigured ? '已配置' : '未配置' }}。修改后需重启后端生效。</div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="testConnection">测试连接</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="hover" style="margin-top:20px">
      <template #header><span><strong>评审参数</strong></span></template>
      <el-form label-width="140px">
        <el-form-item label="默认评审模式">
          <el-select v-model="form.reviewMode" style="width:200px">
            <el-option label="标准模式" value="standard" />
            <el-option label="完整模式（含深度复查）" value="complete" />
            <el-option label="快速模式" value="fast" />
          </el-select>
        </el-form-item>
        <el-form-item label="LLM 最大并发">
          <el-input-number v-model="form.llmConcurrency" :min="1" :max="20" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveSettings">保存设置</el-button>
          <el-button @click="loadSettings">刷新</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="testResult" shadow="hover" style="margin-top:20px">
      <template #header><span>连接测试结果</span></template>
      <pre style="white-space:pre-wrap">{{ testResult }}</pre>
    </el-card>
  </div>
</template>

<script setup name="EvalSettings">
import { ref, reactive, onMounted } from 'vue'
import request from '@/utils/request'

const form = reactive({
  reviewMode: 'standard',
  llmConcurrency: 5,
  llmModel: '',
  llmBaseUrl: '',
  llmApiKey: '',
})
const llmConfigured = ref(false)
const testResult = ref('')

async function loadSettings() {
  const res = await request({ url: '/eval/settings', method: 'get' })
  const d = res.data || res
  if (d) {
    form.reviewMode = d.reviewMode || 'standard'
    form.llmConcurrency = d.llmConcurrency || 5
    form.llmModel = d.llmModel || ''
    form.llmBaseUrl = d.llmBaseUrl || ''
    llmConfigured.value = d.llmConfigured || false
  }
}

async function saveSettings() {
  await request({
    url: '/eval/settings',
    method: 'post',
    data: {
      reviewMode: form.reviewMode,
      llmConcurrency: form.llmConcurrency,
      llmModel: form.llmModel,
      llmBaseUrl: form.llmBaseUrl,
    }
  })
  ElMessage.success('设置已保存')
}

async function testConnection() {
  testResult.value = '测试中...'
  try {
    const res = await request({ url: '/eval/llm/status', method: 'get' })
    const d = res.data || res
    testResult.value = `连接成功\n  模型: ${d.model}\n  地址: ${d.apiBase}\n  状态: ${d.configured ? '已配置' : '未配置'}`
  } catch (e) {
    testResult.value = `连接失败: ${e}`
  }
}

onMounted(() => { loadSettings() })
</script>

<style scoped>
.el-form-item-msg { font-size: 12px; color: #909399; margin-top: 4px; }
</style>
