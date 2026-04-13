import { createBrowserRouter, Outlet, redirect } from 'react-router';
import { Toaster } from 'sonner';
import { AuthProvider } from '../hooks/useAuth';
import { Login } from './pages/Login';
import { VerifyOTP } from './pages/VerifyOTP';
import { Onboarding } from './pages/Onboarding';
import { AppLayout } from './pages/AppLayout';
import { Dashboard } from './pages/Dashboard';
import { Transactions } from './pages/Transactions';
import { TransactionDetail } from './pages/TransactionDetail';
import { Profile } from './pages/Profile';

function Root() {
  return (
    <AuthProvider>
      <div
        className="min-h-screen flex justify-center items-start"
        style={{
          background: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #6366F1 100%)',
          fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        }}
      >
        <div
          className="w-full max-w-[390px] bg-[#F8FAFC] relative overflow-x-hidden"
          style={{ minHeight: '100vh' }}
        >
          <Outlet />
          <Toaster
            position="top-center"
            toastOptions={{
              style: { fontFamily: "'Inter', sans-serif", fontSize: 13 },
            }}
          />
        </div>
      </div>
    </AuthProvider>
  );
}

export const router = createBrowserRouter([
  {
    path: '/',
    Component: Root,
    children: [
      { index: true, Component: Login },
      { path: 'verify', Component: VerifyOTP },
      { path: 'onboarding', Component: Onboarding },
      { path: 'transaction/:id', Component: TransactionDetail },
      {
        path: 'app',
        Component: AppLayout,
        children: [
          { index: true, Component: Dashboard },
          { path: 'transactions', Component: Transactions },
          { path: 'profile', Component: Profile },
        ],
      },
      {
        path: '*',
        loader: () => redirect('/'),
      },
    ],
  },
]);
