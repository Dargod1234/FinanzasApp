import { Outlet } from 'react-router';
import { BottomNav } from '../components/BottomNav';

export function AppLayout() {
  return (
    <div className="flex flex-col min-h-screen">
      <div className="flex-1 overflow-y-auto pb-24">
        <Outlet />
      </div>
      <BottomNav />
    </div>
  );
}
