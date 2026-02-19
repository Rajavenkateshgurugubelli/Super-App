import { useState } from 'react'
import UserSignup from './components/UserSignup'
import WalletDashboard from './components/WalletDashboard'

function App() {
  const [user, setUser] = useState(null)

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col items-center py-10 px-4">
      <header className="mb-10 text-center">
        <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
          Global Genesis Super App
        </h1>
        <p className="text-slate-500 mt-2">Next-Gen Financial Operating System</p>
      </header>

      <main className="w-full max-w-4xl flex flex-col items-center gap-6">
        {!user ? (
          <UserSignup onUserCreated={setUser} />
        ) : (
          <WalletDashboard user={user} />
        )}
      </main>
    </div>
  )
}

export default App
