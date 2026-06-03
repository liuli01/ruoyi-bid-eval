import request from '@/utils/request'

export function getLlmStatus() {
  return request({
    url: '/eval/llm/status',
    method: 'get'
  })
}
