import { NavLink, Outlet } from "react-router-dom";
import { LayoutDashboard, LogOut, ScanSearch } from "lucide-react";
import { useAuthStore } from "../stores/useAuthStore";

export default function AppLayout() {
  const { user, logout } = useAuthStore();

  return (
    <div className="min-h-screen flex bg-ink-950">
      <aside className="w-60 shrink-0 border-r border-ink-700 flex flex-col justify-between p-5">
        <div>
          <div className="flex items-center gap-2 mb-10">
            <div className="w-7 h-7 rounded-md bg-signal-amber/90 diff-gutter gutter-high" />
            <span className="font-display font-semibold text-lg tracking-tight">RepoSage</span>
          </div>

          <nav className="space-y-1">
            <SideLink to="/dashboard" icon={<LayoutDashboard size={17} />} label="Dashboard" />
            <SideLink to="/analyses/new" icon={<ScanSearch size={17} />} label="New analysis" />
          </nav>
        </div>

        <div className="border-t border-ink-700 pt-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-full bg-ink-700 flex items-center justify-center text-xs font-mono">
              {(user?.full_name || user?.email || "?")[0]?.toUpperCase()}
            </div>
            <div className="text-sm truncate">
              <div className="text-mist-100 truncate">{user?.full_name || "Account"}</div>
              <div className="text-mist-400 text-xs truncate">{user?.email}</div>
            </div>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-2 text-mist-300 hover:text-signal-rose text-sm transition-colors"
          >
            <LogOut size={15} /> Log out
          </button>
        </div>
      </aside>

      <main className="flex-1 min-w-0">
        <Outlet />
      </main>
    </div>
  );
}

function SideLink({ to, icon, label }: { to: string; icon: React.ReactNode; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
          isActive
            ? "bg-ink-800 text-mist-100"
            : "text-mist-300 hover:bg-ink-800/60 hover:text-mist-100"
        }`
      }
    >
      {icon}
      {label}
    </NavLink>
  );
}
