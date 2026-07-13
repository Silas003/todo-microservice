import React, { useState } from 'react'
import { updateTask, deleteTask } from '../api/tasksApi'

const STATUS_COLORS = {
  Pending: '#f0ad4e',
  Completed: '#5cb85c',
  Expired: '#d9534f',
}

const styles = {
  card: {
    background: '#fff',
    border: '1px solid #ddd',
    borderRadius: '8px',
    padding: '1rem',
    marginBottom: '0.75rem',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  badge: (status) => ({
    display: 'inline-block',
    padding: '0.2rem 0.6rem',
    borderRadius: '12px',
    background: STATUS_COLORS[status] || '#ccc',
    color: '#fff',
    fontSize: '0.8rem',
    fontWeight: 'bold',
  }),
  actions: { display: 'flex', gap: '0.5rem', alignItems: 'center' },
  btn: (variant) => ({
    padding: '0.3rem 0.75rem',
    borderRadius: '4px',
    border: 'none',
    cursor: 'pointer',
    background: variant === 'danger' ? '#e94560' : '#1a1a2e',
    color: '#fff',
    fontSize: '0.85rem',
  }),
  meta: { fontSize: '0.8rem', color: '#888', marginTop: '0.25rem' },
}

export default function TaskItem({ task, onUpdate, onDelete }) {
  const [loading, setLoading] = useState(false)

  const handleComplete = async () => {
    setLoading(true)
    try {
      const updated = await updateTask(task.TaskId, { Status: 'Completed' })
      onUpdate({ ...task, ...updated, Status: 'Completed' })
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!window.confirm('Delete this task?')) return
    setLoading(true)
    try {
      await deleteTask(task.TaskId)
      onDelete(task.TaskId)
    } finally {
      setLoading(false)
    }
  }

  const deadlineDate = task.Deadline
    ? new Date(task.Deadline * 1000).toLocaleString()
    : 'N/A'

  return (
    <div style={styles.card}>
      <div>
        <strong>{task.Description}</strong>
        <p style={styles.meta}>Date: {task.Date || '—'} &nbsp;|&nbsp; Deadline: {deadlineDate}</p>
        <span style={styles.badge(task.Status)}>{task.Status}</span>
      </div>
      <div style={styles.actions}>
        {task.Status === 'Pending' && (
          <button
            style={styles.btn('primary')}
            onClick={handleComplete}
            disabled={loading}
          >
            Complete
          </button>
        )}
        <button
          style={styles.btn('danger')}
          onClick={handleDelete}
          disabled={loading}
        >
          Delete
        </button>
      </div>
    </div>
  )
}
