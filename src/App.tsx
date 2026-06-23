import { NavLink, Route, Routes } from 'react-router-dom';
import ImportPage from './pages/ImportPage';
import AnalysisPage from './pages/AnalysisPage';
import ReportPage from './pages/ReportPage';

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">Chronos</h1>
        <p className="app-subtitle">个人心理健康洞察</p>
        <nav className="app-nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : '')}>
            导入
          </NavLink>
          <NavLink to="/analysis" className={({ isActive }) => (isActive ? 'active' : '')}>
            分析
          </NavLink>
          <NavLink to="/report" className={({ isActive }) => (isActive ? 'active' : '')}>
            报告
          </NavLink>
        </nav>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<ImportPage />} />
          <Route path="/analysis" element={<AnalysisPage />} />
          <Route path="/report" element={<ReportPage />} />
        </Routes>
      </main>
    </div>
  );
}
