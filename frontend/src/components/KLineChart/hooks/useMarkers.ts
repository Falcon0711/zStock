import { useEffect } from 'react';
import type { ISeriesApi, SeriesMarker, Time } from 'lightweight-charts';
import type { ChartData } from '../types';

/**
 * Hook to manage buy/sell signal markers on the candlestick series.
 * Updates markers independently from chart creation.
 */
export function useMarkers(
    candlestickSeriesRef: React.RefObject<ISeriesApi<'Candlestick'> | null>,
    data: ChartData[],
    showSignals: boolean
) {
    useEffect(() => {
        if (!candlestickSeriesRef.current || data.length === 0) return;

        if (showSignals) {
            const markers: SeriesMarker<Time>[] = data
                .filter(d => d.signal_buy || d.signal_sell)
                .map(d => ({
                    time: d.time as Time,
                    position: d.signal_buy ? 'belowBar' : 'aboveBar',
                    color: d.signal_buy ? '#FF3B30' : '#34C759',
                    shape: d.signal_buy ? 'arrowUp' : 'arrowDown',
                    text: d.signal_buy ? '买' : '卖',
                } as SeriesMarker<Time>));
            candlestickSeriesRef.current.setMarkers(markers);
        } else {
            candlestickSeriesRef.current.setMarkers([]);
        }
    }, [candlestickSeriesRef, data, showSignals]);
}
