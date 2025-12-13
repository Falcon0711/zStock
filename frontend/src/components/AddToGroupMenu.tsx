import React, { memo, useState } from 'react';
import type { StockGroupKey } from '../types';

interface AddToGroupMenuProps {
    onAdd: (group: StockGroupKey) => Promise<void>;
    loading?: boolean;
}

const GROUPS = [
    { id: 'favorites' as const, label: '⭐ 自选股' },
    { id: 'holdings' as const, label: '💼 持有股' },
    { id: 'watching' as const, label: '👀 观测股' }
];

/**
 * AddToGroupMenu component - Dropdown menu for adding stocks to groups
 */
const AddToGroupMenu: React.FC<AddToGroupMenuProps> = memo(({ onAdd, loading = false }) => {
    const [isOpen, setIsOpen] = useState(false);

    const handleAdd = async (groupId: StockGroupKey) => {
        if (loading) return;
        await onAdd(groupId);
        setIsOpen(false);
    };

    return (
        <div style={{ position: 'relative' }}>
            <button
                className="btn btn-secondary"
                onClick={() => setIsOpen(!isOpen)}
                title="添加到分组"
            >
                <span>+</span>
                <span>添加</span>
            </button>

            {isOpen && (
                <>
                    <div
                        className="dropdown-overlay"
                        onClick={() => setIsOpen(false)}
                    />
                    <div className="dropdown-menu">
                        {GROUPS.map(group => (
                            <button
                                key={group.id}
                                className="dropdown-item"
                                onClick={() => handleAdd(group.id)}
                                disabled={loading}
                            >
                                {group.label}
                            </button>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
});

AddToGroupMenu.displayName = 'AddToGroupMenu';

export default AddToGroupMenu;
