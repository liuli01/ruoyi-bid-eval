import request from '@/utils/request'

// ======== 会商 ========
export function listConsultation() {
  return request({ url: '/portal/consultation/list', method: 'get' })
}
export function getConsultation(id) {
  return request({ url: `/portal/consultation/${id}`, method: 'get' })
}
export function createConsultation(data) {
  return request({ url: '/portal/consultation', method: 'post', data })
}
export function approveConsultation(id, data) {
  return request({ url: `/portal/consultation/${id}/approve`, method: 'post', data })
}

// ======== 立项 ========
export function listApproval() {
  return request({ url: '/portal/approval/list', method: 'get' })
}
export function getApproval(id) {
  return request({ url: `/portal/approval/${id}`, method: 'get' })
}
export function createApproval(data) {
  return request({ url: '/portal/approval', method: 'post', data })
}

// ======== 一事一议 ========
export function listYiyi() {
  return request({ url: '/portal/yiyi/list', method: 'get' })
}
export function getYiyi(id) {
  return request({ url: `/portal/yiyi/${id}`, method: 'get' })
}
export function createYiyi(data) {
  return request({ url: '/portal/yiyi', method: 'post', data })
}
export function checkYiyi(id, data) {
  return request({ url: `/portal/yiyi/${id}/check`, method: 'post', data })
}
export function approveYiyi(id, data) {
  return request({ url: `/portal/yiyi/${id}/approve`, method: 'post', data })
}
