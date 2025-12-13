import React, { memo } from 'react';

interface MetricCardProps {
    icon: string;
    label: string;
    value: string;
    color: string;
}

/**
 * MetricCard component - Displays a key metric with icon, label and value
 */
const MetricCard: React.FC<MetricCardProps> = memo(({ icon, label, value, color }) => {
    return (
        <div className="metric-card">
            <div className="metric-card-icon">{icon}</div>
            <div className="metric-card-content">
                <div className="metric-card-label">{label}</div>
                <div className="metric-card-value" style={{ color }}>{value}</div>
            </div>
        </div>
    );
});

MetricCard.displayName = 'MetricCard';

export default MetricCard;
