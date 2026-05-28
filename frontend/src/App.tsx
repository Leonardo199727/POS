import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useContext } from "react";
import Login from "./pages/Login";
import Home from "./pages/Home";
import { Products } from "./pages/Products";
import { Customers } from "./pages/Customers";
import Inventory from "./pages/Inventory";
import Abonos from "./pages/Abonos";
import Reports from "./pages/Reports";
import CreditoCobranza from "./pages/CreditoCobranza";
import Settings from "./pages/Settings";
import { AuthContext } from "./context/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { useCart } from "./context/CartContext";
import { CartButton } from "./components/CartButton";
import { CartDrawer } from "./components/CartDrawer";
import { CajaModal } from "./components/CajaModal";

const App = () => {
  const { token } = useContext(AuthContext);
  const { cartItems, isCartOpen, setIsCartOpen, totalItems, updateQuantity, removeItem } = useCart();
  const location = useLocation();

  // El botón del carrito se muestra globalmente si hay items, excepto en login
  const isLoginPage = location.pathname === "/login";
  const showCartGlobally = !isLoginPage && (totalItems > 0 || isCartOpen);

  return (
    <>
      <Routes>
        <Route path="/login" element={token ? <Navigate to="/home" replace /> : <Login />} />
        <Route
          path="/home"
          element={
            <ProtectedRoute>
              <Home />
            </ProtectedRoute>
          }
        />
        <Route
          path="/products"
          element={
            <ProtectedRoute>
              <Products />
            </ProtectedRoute>
          }
        />
        <Route
          path="/clientes"
          element={
            <ProtectedRoute>
              <Customers />
            </ProtectedRoute>
          }
        />
        <Route
          path="/inventario"
          element={
            <ProtectedRoute>
              <Inventory />
            </ProtectedRoute>
          }
        />
        <Route
          path="/abonos"
          element={
            <ProtectedRoute>
              <Abonos />
            </ProtectedRoute>
          }
        />
        <Route
          path="/reportes"
          element={
            <ProtectedRoute>
              <Reports />
            </ProtectedRoute>
          }
        />
        <Route
          path="/reportes/credito-cobranza"
          element={
            <ProtectedRoute>
              <CreditoCobranza />
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <Settings />
            </ProtectedRoute>
          }
        />

        {/* Explicit root route */}
        <Route path="/" element={<Navigate to={token ? "/home" : "/login"} replace />} />

        {/* Fallback root route */}
        <Route path="*" element={<Navigate to={token ? "/home" : "/login"} replace />} />
      </Routes>

      {/* Global Cart UI - visible on all pages when cart has items */}
      {showCartGlobally && (
        <>
          <CartDrawer
            isOpen={isCartOpen}
            onClose={() => setIsCartOpen(false)}
            cartItems={cartItems}
            onUpdateQuantity={updateQuantity}
            onRemoveItem={removeItem}
          />
          {!isCartOpen && (
            <CartButton
              itemCount={totalItems}
              onClick={() => setIsCartOpen(true)}
            />
          )}
        </>
      )}

      {/* Modal de Apertura de Caja - global, solo si autenticado */}
      {token && <CajaModal />}
    </>
  );
};

export default App;