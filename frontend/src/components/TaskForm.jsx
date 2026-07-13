import React, { useState } from 'react'
import { createTask } from '../api/tasksApi'

const styles = {
  form: {
    background: '#f9f9f9',
    border: '1px solid #ddd',
    borderRadius: '8px',
    padding: '1rem',
    margin: '1rem 0',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  },
  input: {
    padding: '0.5rem',
    borderRadius: '4px',
    border: '1px solid #ccc',
    fontSize: '1rem',
  },
  error: { color: '#e94560' },
  submit: {
    padding: '0.5rem',
    background: '#1a1a2e',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '1rem',
  },
}

export default function TaskForm({ onCreated }) {
  const [description, setDescription] = useState('')
  const [date, setDate] = useState('')
  const [deadline, setDeadline] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!description.trim()) {
      setError('Description is required')
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      const payload = { Description: description, Date: date }
      if (deadline) {
        payload.Deadline = Math.floor(new Date(deadline).getTime() / 1000)
      }
      const task = await createTask(payload)
      setDescription('')
      setDate('')
      setDeadline('')
      onCreated(task)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form style={styles.form} onSubmit={handleSubmit}>
      <input
        style={styles.input}
        placeholder="Task description"
        value={description}
        onChange={e => setDescription(e.target.value)}
        required
      />
      <input
        style={styles.input}
        type="date"
        value={date}
        onChange={e => setDate(e.target.value)}
      />
      <label style={{ fontSize: '0.85rem', color: '#555' }}>
        Deadline (default: 5 min from now)
      </label>
      <input
        style={styles.input}
        type="datetime-local"
        value={deadline}
        onChange={e => setDeadline(e.target.value)}
      />
      {error && <p style={styles.error}>{error}</p>}
      <button style={styles.submit} type="submit" disabled={submitting}>
        {submitting ? 'Creating...' : 'Create Task'}
      </button>
    </form>
  )
}
