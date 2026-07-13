import React from 'react'
import { Authenticator, useAuthenticator } from '@aws-amplify/ui-react'
import AuthWrapper from './components/AuthWrapper'

function Inner() {
  const { authStatus } = useAuthenticator(ctx => [ctx.authStatus])

  if (authStatus !== 'authenticated') {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: '4rem' }}>
        <Authenticator />
      </div>
    )
  }

  return <AuthWrapper />
}

export default function App() {
  return (
    <Authenticator.Provider>
      <Inner />
    </Authenticator.Provider>
  )
}
