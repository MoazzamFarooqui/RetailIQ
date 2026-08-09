import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import Layout from './components/Layout/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Analytics from './pages/Analytics';
import Forecast from './pages/Forecast';
import Inventory from './pages/Inventory';
import ModelInsights from './pages/ModelInsights';
import AIInsights from './pages/AIInsights';
import Upload from './pages/Upload';
import Stores from './pages/Stores';
import Products from './pages/Products';
import Advisor from './pages/Advisor';
import Alerts from './pages/Alerts';
import Reports from './pages/Reports';
import WhatIf from './pages/WhatIf';
import DataHealth from './pages/DataHealth';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex items-center justify-center min-h-screen"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" /></div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function App() {
  const { user } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="forecast" element={<Forecast />} />
        <Route path="inventory" element={<Inventory />} />
        <Route path="model-insights" element={<ModelInsights />} />
        <Route path="ai-insights" element={<AIInsights />} />
        <Route path="upload" element={<Upload />} />
        <Route path="stores" element={<Stores />} />
        <Route path="products" element={<Products />} />
        <Route path="advisor" element={<Advisor />} />
        <Route path="alerts" element={<Alerts />} />
        <Route path="reports" element={<Reports />} />
        <Route path="what-if" element={<WhatIf />} />
        <Route path="data-health" element={<DataHealth />} />
      </Route>
    </Routes>
  );
}

export default App;
