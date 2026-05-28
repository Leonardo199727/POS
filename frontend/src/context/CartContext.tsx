import { createContext, useContext, useState, type ReactNode } from "react";

interface CartItem {
    producto: any;
    variante: any;
    cantidad: number;
}

interface CartContextType {
    cartItems: CartItem[];
    isCartOpen: boolean;
    setIsCartOpen: (open: boolean) => void;
    addToCart: (product: any, variant: any, quantity?: number) => void;
    updateQuantity: (variantId: number, delta: number) => void;
    removeItem: (variantId: number) => void;
    clearCart: () => void;
    totalItems: number;
}

const CartContext = createContext<CartContextType>({
    cartItems: [],
    isCartOpen: false,
    setIsCartOpen: () => { },
    addToCart: () => { },
    updateQuantity: () => { },
    removeItem: () => { },
    clearCart: () => { },
    totalItems: 0,
});

export const useCart = () => useContext(CartContext);

export const CartProvider = ({ children }: { children: ReactNode }) => {
    const [cartItems, setCartItems] = useState<CartItem[]>([]);
    const [isCartOpen, setIsCartOpen] = useState(false);

    const addToCart = (product: any, variant: any, quantity: number = 1) => {
        setCartItems(prev => {
            const existingItem = prev.find(item => item.variante.id === variant.id);
            if (existingItem) {
                const currentStock = variant.stock_actual;
                if (existingItem.cantidad + quantity > currentStock) {
                    alert('No hay suficiente stock para añadir más unidades.');
                    return prev;
                }
                return prev.map(item =>
                    item.variante.id === variant.id
                        ? { ...item, cantidad: item.cantidad + quantity }
                        : item
                );
            }
            return [...prev, { producto: product, variante: variant, cantidad: quantity }];
        });
    };

    const updateQuantity = (variantId: number, delta: number) => {
        setCartItems(prev => prev.map(item => {
            if (item.variante.id === variantId) {
                const newQuantity = item.cantidad + delta;
                if (newQuantity >= 1 && newQuantity <= item.variante.stock_actual) {
                    return { ...item, cantidad: newQuantity };
                }
            }
            return item;
        }));
    };

    const removeItem = (variantId: number) => {
        setCartItems(prev => prev.filter(item => item.variante.id !== variantId));
    };

    const clearCart = () => {
        setCartItems([]);
    };

    const totalItems = cartItems.reduce((acc, item) => acc + item.cantidad, 0);

    return (
        <CartContext.Provider value={{
            cartItems,
            isCartOpen,
            setIsCartOpen,
            addToCart,
            updateQuantity,
            removeItem,
            clearCart,
            totalItems,
        }}>
            {children}
        </CartContext.Provider>
    );
};
