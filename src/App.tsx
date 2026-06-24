import { NavLink, Route, Routes } from 'react-router-dom';
import { useEffect } from 'react';

import ImportPage from './pages/ImportPage';
import AnalysisPage from './pages/AnalysisPage';
import ReportPage from './pages/ReportPage';
import SettingsPage from './pages/SettingsPage';
import DataSourcesPage from './pages/DataSourcesPage';
import StoryPage from './pages/StoryPage';
import SelvesPage from './pages/SelvesPage';
import ReframePage from './pages/ReframePage';
import { applyTheme } from './utils/theme';

const NAV_GROUPS = [
  {
    label: '数据',
    items: [
      { to: '/', label: '导入', end: true },
      { to: '/sources', label: '数据源' },
      { to: '/settings', label: '设置' },
    ],
  },
  {
    label: '分析',
    items: [{ to: '/analysis', label: '分析' }],
  },
  {
    label: '洞察',
    items: [
      { to: '/report', label: '报告' },
      { to: '/story', label: '故事' },
      { to: '/selves', label: '自我' },
      { to: '/reframe', label: '重构' },
    ],
  },
];

export default function App() {
  useEffect(() => {
    window.chronosAPI.getSettings().then((s) => applyTheme(s.theme ?? 'light'));
  }, []);

  return (
    <div className="app">
      <aside className="app-sidebar">
        <div className="sidebar-brand">
          <h1 className="app-title">Chronos</h1>
          <p className="app-subtitle">个人心理健康洞察</p>
        </div>
        <nav className="sidebar-nav">
          {NAV_GROUPS.map((group) => (
            <div key={group.label} className="nav-group">
              <span className="nav-group-label">{group.label}</span>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      <main className="app-content">
        <Routes>
          <Route path="/" element={<ImportPage />} />
          <Route path="/sources" element={<DataSourcesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/analysis" element={<AnalysisPage />} />
          <Route path="/report" element={<ReportPage />} />
          <Route path="/story" element={<StoryPage />} />
          <Route path="/selves" element={<SelvesPage />} />
          <Route path="/reframe" element={<ReframePage />} />
        </Routes>
      </main>
    </div>
  );
}
