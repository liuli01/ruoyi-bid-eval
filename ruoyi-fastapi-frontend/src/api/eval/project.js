import request from '@/utils/request'

export function listProject(query) {
  return request({
    url: '/eval/project/list',
    method: 'get',
    params: query
  })
}

export function getProject(projectId) {
  return request({
    url: '/eval/project/' + projectId,
    method: 'get'
  })
}

export function addProject(data) {
  return request({
    url: '/eval/project',
    method: 'post',
    data: data
  })
}

export function delProject(projectId) {
  return request({
    url: '/eval/project/' + projectId,
    method: 'delete'
  })
}
