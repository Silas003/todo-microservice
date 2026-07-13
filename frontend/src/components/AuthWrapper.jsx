import React from 'react'
import { useAuthenticator } from '@aws-amplify/ui-react'
import TaskList from './TaskList'

const styles = {
  nav: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0.75rem 1.5rem',
    background: '#1a1a2e',
    color: '#fff',
  },
  signOut: {
    background: '#e94560',
    color: '#fff',
    border: 'none',
    padding: '0.4rem 1rem',
    borderRadius: '4px',
    cursor: 'pointer',
  },
}

export default function AuthWrapper() {
  const { user, signOut } = useAuthenticator(ctx => [ctx.user, ctx.signOut])

  return (
    <>
      <nav style={styles.nav}>
        <span>Task Manager</span>
        <span>
          {user?.signInDetails?.loginId || user?.username}
          &nbsp;&nbsp;
          <button style={styles.signOut} onClick={signOut}>Sign Out</button>
        </span>
      </nav>
      <TaskList />
    </>
  )
}
