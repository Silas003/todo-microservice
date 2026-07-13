import React, { useCallback, useEffect, useState } from 'react'
import { listTasks } from '../api/tasksApi'
import TaskForm from './TaskForm'
import TaskItem from './TaskItem'

const styles = {
  container: { maxWidth: '800px', margin: '2rem auto', padding: '0 1rem' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  error: { color: '#e94560', margin: '1rem 0' },
  empty: { color: '#888', textAlign: 'center', margin: '2rem 0' },
  tabs: { display: 'flex', gap: '0.5rem', margin: '1rem 0' },
  tab: (active) => ({
    padding: '0.4rem 1rem',
    borderRadius: '4px',
    cursor: 'pointer',
    background: active ? '#1a1a2e' : '#eee',
    color: active ? '#fff' : '#333',
    border: 'none',
  }),
}

const ALL_STATUSES = ['All', 'Pending', 'Completed', 'Expired']

export default function TaskList() {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('All')
  const [showForm, setShowForm] = useState(false)

  const fetchTasks = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await listTasks()
      setTasks(data || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchTasks() }, [fetchTasks])

  const filtered = filter === 'All' ? tasks : tasks.filter(t => t.Status === filter)

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2>My Tasks</h2>
        <button onClick={() => setShowForm(v => !v)}>
          {showForm ? 'Cancel' : '+ New Task'}
        </button>
      </div>

      {showForm && (
        <TaskForm onCreated={(task) => {
          setTasks(prev => [task, ...prev])
          setShowForm(false)
        }} />
      )}

      <div style={styles.tabs}>
        {ALL_STATUSES.map(s => (
          <button key={s} style={styles.tab(filter === s)} onClick={() => setFilter(s)}>{s}</button>
        ))}
      </div>

      {error && <p style={styles.error}>{error}</p>}
      {loading && <p>Loading...</p>}
      {!loading && filtered.length === 0 && <p style={styles.empty}>No tasks found.</p>}

      {filtered.map(task => (
        <TaskItem
          key={task.TaskId}
          task={task}
          onUpdate={(updated) => setTasks(prev => prev.map(t => t.TaskId === updated.TaskId ? updated : t))}
          onDelete={(taskId) => setTasks(prev => prev.filter(t => t.TaskId !== taskId))}
        />
      ))}
    </div>
  )
}
