<template>
  <div class="app-container">
    <el-form :inline="true" v-show="showSearch">
      <el-form-item label="规则类型">
        <el-radio-group v-model="queryType" @change="getList">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="p">P 类</el-radio-button>
          <el-radio-button value="r">R 类</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="风险等级">
        <el-select v-model="queryLevel" placeholder="全部" clearable style="width:120px" @change="getList">
          <el-option label="高风险" value="high" />
          <el-option label="中风险" value="medium" />
          <el-option label="低风险" value="low" />
        </el-select>
      </el-form-item>
      <el-form-item label="搜索">
        <el-input v-model="queryKeyword" placeholder="规则编号/名称" clearable style="width:200px" @keyup.enter="getList" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="getList">查询</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-table v-loading="loading" :data="rules" :max-height="600" @expand-change="handleExpand">
      <el-table-column type="expand" width="30">
        <template #default="s">
          <div style="padding:12px 20px">
            <p><strong>规则原文：</strong></p>
            <pre style="white-space:pre-wrap;background:#f5f7fa;padding:12px;border-radius:4px;font-size:13px;">{{ s.row.full_text || '(无)' }}</pre>
            <p v-if="s.row.basis" style="margin-top:8px"><strong>制度依据：</strong>{{ s.row.basis }}</p>
            <p v-if="s.row.trigger_keywords"><strong>触发关键词：</strong>{{ s.row.trigger_keywords.join(', ') }}</p>
            <p v-if="s.row.confidence"><strong>置信度：</strong>{{ s.row.confidence }}</p>
            <p v-if="s.row.dimension"><strong>维度：</strong>{{ s.row.dimension }}</p>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="编号" prop="rule_id" width="100" sortable />
      <el-table-column label="类型" width="70">
        <template #default="s">
          <el-tag :type="s.row._type === 'P' ? '' : 'warning'" size="small">{{ s.row._type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="规则名称" prop="name" min-width="200" :show-overflow-tooltip="true" />
      <el-table-column label="部门" prop="department" width="100" />
      <el-table-column label="风险等级" width="90">
        <template #default="s">
          <el-tag :type="s.row.level === 'high' ? 'danger' : s.row.level === 'medium' ? 'warning' : 'info'" size="small">
            {{ s.row.level === 'high' ? '高' : s.row.level === 'medium' ? '中' : '低' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="分类" prop="category" width="100" />
    </el-table>

    <pagination v-show="total > 0" :total="total" v-model:page="pageNum" v-model:limit="pageSize" @pagination="getList" />
  </div>
</template>

<script setup name="EvalRules">
import { ref, reactive } from 'vue'
import request from '@/utils/request'

const rules = ref([])
const loading = ref(false)
const showSearch = ref(true)
const total = ref(0)
const pageNum = ref(1)
const pageSize = ref(20)
const queryType = ref('all')
const queryLevel = ref('')
const queryKeyword = ref('')

async function getList() {
  loading.value = true
  try {
    const res = await request({
      url: '/eval/rules',
      method: 'get',
      params: {
        rule_type: queryType.value,
        level: queryLevel.value,
        keyword: queryKeyword.value,
      }
    })
    const data = res.data || res || []
    rules.value = Array.isArray(data) ? data : []
    total.value = rules.value.length
  } finally {
    loading.value = false
  }
}

function handleExpand(row) {
  // expand row - content shown in template
}

function resetQuery() {
  queryLevel.value = ''
  queryKeyword.value = ''
  getList()
}

onMounted(() => { getList() })
</script>
