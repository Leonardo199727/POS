import React from 'react';

interface CartButtonProps {
    itemCount: number;
    onClick: () => void;
}

export const CartButton: React.FC<CartButtonProps> = ({ itemCount, onClick }) => {
    return (
        <button
            onClick={onClick}
            className="fixed bottom-12 right-12 z-50 flex items-center justify-center w-16 h-16 bg-primary text-white rounded-[50%] shadow-[0_8px_30px_rgb(0,0,0,0.5)] hover:bg-[#ff8a33] hover:scale-105 active:scale-95 transition-all outline-none focus:outline-none border-2 border-primary/50 group"
            aria-label="Abrir Carrito"
        >
            <span className="material-symbols-outlined text-[28px] group-hover:animate-pulse">
                shopping_cart
            </span>

            {itemCount >= 0 && (
                <div className="absolute -top-1 -right-1 bg-slate-900 border-2 border-primary text-white text-[11px] font-bold w-6 h-6 rounded-[50%] flex items-center justify-center shadow-lg">
                    {itemCount > 99 ? '99+' : itemCount}
                </div>
            )}
        </button>
    );
};
