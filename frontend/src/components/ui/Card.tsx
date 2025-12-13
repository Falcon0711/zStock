import React, { memo } from 'react';

interface CardProps {
    children: React.ReactNode;
    className?: string;
    hover?: boolean;
    glass?: boolean;
    onClick?: () => void;
    style?: React.CSSProperties;
}

/**
 * Card component - A reusable container with consistent styling
 */
const Card: React.FC<CardProps> = memo(({
    children,
    className = '',
    hover = false,
    glass = false,
    onClick,
    style
}) => {
    const classes = [
        'card',
        hover && 'card-hover',
        glass && 'card-glass',
        onClick && 'card-interactive',
        className
    ].filter(Boolean).join(' ');

    return (
        <div className={classes} onClick={onClick} style={style}>
            {children}
        </div>
    );
});

Card.displayName = 'Card';

export default Card;
