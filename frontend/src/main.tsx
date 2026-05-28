import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { CartProvider } from "./context/CartContext";
import { CajaProvider } from "./context/CajaContext";
import { RefreshProvider } from "./context/RefreshContext";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <BrowserRouter>
    <AuthProvider>
      <CajaProvider>
        <RefreshProvider>
          <CartProvider>
            <App />
          </CartProvider>
        </RefreshProvider>
      </CajaProvider>
    </AuthProvider>
  </BrowserRouter>
);