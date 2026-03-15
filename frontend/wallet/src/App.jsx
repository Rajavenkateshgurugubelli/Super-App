import React from 'react';
import { Routes, Route } from 'react-router-dom';
import AppLayout from './layout/AppLayout.jsx';
import HomePage from './features/home/HomePage.jsx';
import PaymentsPage from './features/payments/PaymentsPage.jsx';
import ShopPage from './features/shop/ShopPage.jsx';
import ServicesPage from './features/services/ServicesPage.jsx';
import ProfilePage from './features/profile/ProfilePage.jsx';
import './App.css';

function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/payments" element={<PaymentsPage />} />
        <Route path="/shop" element={<ShopPage />} />
        <Route path="/services" element={<ServicesPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Routes>
    </AppLayout>
  );
}

export default App;

