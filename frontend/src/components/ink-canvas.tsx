import { useCallback, useState } from 'react';
import {
  StyleSheet,
  View,
  type GestureResponderEvent,
  type LayoutChangeEvent,
} from 'react-native';
import Svg, { Polyline } from 'react-native-svg';

import type { Stroke, StrokePoint } from '@/api/types';

interface InkCanvasProps {
  strokes: Stroke[];
  onChange: (strokes: Stroke[]) => void;
  strokeColor?: string;
  strokeWidth?: number;
  readonly?: boolean;
}

/**
 * Stylus/finger drawing surface backed by RN responder events — they map to
 * pointer events on web and capture stylus input on Android.
 *
 * Points are stored normalized (0–1 relative to canvas size) so the backend
 * can re-render them onto the worksheet image at any resolution.
 */
export function InkCanvas({
  strokes,
  onChange,
  strokeColor = '#1a1aff',
  strokeWidth = 4,
  readonly = false,
}: InkCanvasProps) {
  const [size, setSize] = useState({ width: 1, height: 1 });
  const [current, setCurrent] = useState<StrokePoint[]>([]);

  const onLayout = useCallback((e: LayoutChangeEvent) => {
    const { width, height } = e.nativeEvent.layout;
    setSize({ width: Math.max(width, 1), height: Math.max(height, 1) });
  }, []);

  const makePoint = useCallback(
    (e: GestureResponderEvent): StrokePoint => {
      const { locationX, locationY } = e.nativeEvent;
      return {
        x: Math.min(Math.max(locationX / size.width, 0), 1),
        y: Math.min(Math.max(locationY / size.height, 0), 1),
        t: Date.now(),
      };
    },
    [size],
  );

  const onGrant = useCallback(
    (e: GestureResponderEvent) => setCurrent([makePoint(e)]),
    [makePoint],
  );

  const onMove = useCallback(
    (e: GestureResponderEvent) =>
      setCurrent((prev) => (prev.length ? [...prev, makePoint(e)] : prev)),
    [makePoint],
  );

  const onRelease = useCallback(
    (e: GestureResponderEvent) => {
      const pts = [...current, makePoint(e)];
      setCurrent([]);
      if (pts.length > 0) {
        onChange([
          ...strokes,
          { points: pts, color: strokeColor, width: strokeWidth },
        ]);
      }
    },
    [current, strokes, makePoint, onChange, strokeColor, strokeWidth],
  );

  const toPoints = (points: StrokePoint[]) =>
    points.map((p) => `${p.x * size.width},${p.y * size.height}`).join(' ');

  return (
    <View
      style={styles.canvas}
      onLayout={onLayout}
      onStartShouldSetResponder={() => !readonly}
      onMoveShouldSetResponder={() => !readonly}
      onResponderGrant={onGrant}
      onResponderMove={onMove}
      onResponderRelease={onRelease}
      onResponderTerminate={onRelease}
    >
      <Svg style={styles.svg} pointerEvents="none">
        {strokes.map((s, i) => (
          <Polyline
            key={i}
            points={toPoints(s.points)}
            stroke={s.color}
            strokeWidth={s.width}
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ))}
        {current.length > 0 && (
          <Polyline
            points={toPoints(current)}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  canvas: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    backgroundColor: 'transparent',
  },
  svg: { flex: 1 },
});
