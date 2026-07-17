import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { clearAccessToken } from "../../../shared/auth/tokens";
import { useSelectedOrganization } from "../../../shared/organizations/context";

const navigation = [
  { to: "/admin", label: "Overview", end: true },
  { to: "/admin/retrieval", label: "Retrieval" },
  { to: "/admin/answers", label: "Answers" },
  { to: "/admin/documents", label: "Documents" },
  { to: "/admin/evaluations", label: "Evaluations" },
  { to: "/admin/audit", label: "Audit log" },
];

export function AdminLayout() {
  const navigate = useNavigate();
  const { clearOrganization, organization } = useSelectedOrganization();

  function signOut() {
    clearAccessToken();
    clearOrganization();
    navigate("/login", { replace: true });
  }

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <div>
          <p className="eyebrow">SecureKnowledge</p>
          <h1>Administration</h1>
          <p className="organization-name">{organization?.name}</p>
        </div>
        <nav aria-label="Admin navigation">
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                isActive ? "admin-nav-link active" : "admin-nav-link"
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <button className="sign-out-button" onClick={signOut} type="button">
          Sign out
        </button>
      </aside>
      <main className="admin-content">
        <Outlet />
      </main>
    </div>
  );
}
