import request from '@/utils/request'

export function startReview(data) {
  return request({
    url: '/eval/review/start',
    method: 'post',
    data: data
  })
}

export function getReview(reviewId) {
  return request({
    url: '/eval/review/' + reviewId,
    method: 'get'
  })
}

export function getReviewProgress(reviewId) {
  return request({
    url: '/eval/review/' + reviewId + '/progress',
    method: 'get'
  })
}

export function getReviewOpinions(reviewId) {
  return request({
    url: '/eval/review/' + reviewId + '/opinions',
    method: 'get'
  })
}

export function exportReview(reviewId) {
  return request({
    url: '/eval/review/' + reviewId + '/export',
    method: 'get',
    responseType: 'blob'
  })
}

export function getProjectReviews(projectId) {
  return request({
    url: '/eval/project/' + projectId + '/reviews',
    method: 'get'
  })
}

export function listReview(query) {
  return request({
    url: '/eval/review/list',
    method: 'get',
    params: query
  })
}
