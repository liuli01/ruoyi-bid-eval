import request from '@/utils/request'

export function uploadMaterial(projectId, formData) {
  return request({
    url: '/eval/project/' + projectId + '/upload',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function listMaterials(projectId) {
  return request({
    url: '/eval/project/' + projectId + '/materials',
    method: 'get'
  })
}

export function downloadMaterial(materialId) {
  return request({
    url: '/eval/material/' + materialId + '/download',
    method: 'get',
    responseType: 'blob'
  })
}
