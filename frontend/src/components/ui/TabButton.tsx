import React, { memo } from 'react';

interface TabButtonProps {
    active: boolean;
    onClick: () => void;
    children: React.ReactNode;
}

/**
 * TabButton component - A toggle button for tab navigation
 */
const TabButton: React.FC<TabButtonProps> = memo(({ active, onClick, children }) => {
    const classes = ['tab-button', active && 'active'].filter(Boolean).join(' ');

    return (
        <button className={classes} onClick={onClick}>
            {children}
        </button>
    );
});

TabButton.displayName = 'TabButton';

export default TabButton;
