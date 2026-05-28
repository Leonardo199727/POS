import { useState, useEffect } from 'react';

export const useCurrentTime = () => {
    const [date, setDate] = useState(new Date());

    useEffect(() => {
        const timer = setInterval(() => setDate(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    const timeString = date.toLocaleTimeString('es-MX', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
    });

    const secondsString = date.toLocaleTimeString('es-MX', {
        second: '2-digit',
    });

    const weekday = date.toLocaleDateString('es-MX', { weekday: 'long' });
    const capitalizedWeekday = weekday.charAt(0).toUpperCase() + weekday.slice(1);

    const day = date.getDate();
    const month = date.toLocaleDateString('es-MX', { month: 'long' });
    const capitalizedMonth = month.charAt(0).toUpperCase() + month.slice(1);
    const year = date.getFullYear();

    const dateStr = `${day} de ${capitalizedMonth}, ${year}`;

    return {
        time: timeString,
        seconds: secondsString,
        weekday: capitalizedWeekday,
        dateStr: dateStr,
    };
};
