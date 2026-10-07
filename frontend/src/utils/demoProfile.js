export const DEMO_PROFILE = {
  skills: ['Python', 'SQL', 'Pandas', 'Git', 'Excel'],
  gpa: '3.2', field_of_study: 'Computer Science',
  python: 1, java: 0, c_cpp: 0, sql: 1, machine_learning: 0,
  data_analysis: 1, cloud_computing: 0, cybersecurity: 0,
  web_development: 0, devops: 0, networking: 0,
  communication: 3, leadership: 3, problem_solving: 4, teamwork: 4, adaptability: 3,
}

export function rememberDemoSession(id) {
  try {
    const ids = JSON.parse(sessionStorage.getItem('careerflow-demo-sessions') || '[]')
    sessionStorage.setItem('careerflow-demo-sessions', JSON.stringify([...new Set([...ids, id])]))
  } catch { /* Demo labels remain available on the current result if storage is disabled. */ }
}

export function isDemoSession(id) {
  try { return JSON.parse(sessionStorage.getItem('careerflow-demo-sessions') || '[]').includes(id) }
  catch { return false }
}
