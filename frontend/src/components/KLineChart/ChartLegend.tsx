import React from 'react';
import type { HoverData, ChartData } from './types';

interface ChartLegendProps {
    currentData: HoverData | ChartData | null;
}

/**
 * Chart legend component showing indicator values.
 */
export const ChartLegend: React.FC<ChartLegendProps> = ({ currentData }) => {
    return (
        <div style={{ display: 'flex', gap: '1rem', flex: 1, flexWrap: 'wrap', fontSize: '0.8rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <div style={{ width: '16px', height: '3px', background: '#8B5CF6', borderRadius: '2px' }} />
                <span style={{ color: '#8B5CF6' }}>
                    BBI{currentData?.bbi != null ? `: ${currentData.bbi.toFixed(2)}` : ''}
                </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <div style={{ width: '16px', height: '3px', background: '#FFD700', borderRadius: '2px' }} />
                <span style={{ color: '#FFD700' }}>
                    短期趋势线{currentData?.zhixing_trend != null ? `: ${currentData.zhixing_trend.toFixed(2)}` : ''}
                </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <div style={{ width: '16px', height: '3px', background: '#888888', borderRadius: '2px' }} />
                <span style={{ color: '#888888' }}>
                    多空线{currentData?.zhixing_multi != null ? `: ${currentData.zhixing_multi.toFixed(2)}` : ''}
                </span>
            </div>
        </div>
    );
};
