import { View, Text } from 'react-native';
import Svg, { Circle } from 'react-native-svg';

interface ProgressRingProps {
  percent: number; // 0-100+ (can exceed 100 if over target — clamped visually)
  size?: number;
  strokeWidth?: number;
  color: string;
  trackColor?: string;
  centerLabel: string; // e.g. "72%"
}

/**
 * Circular progress ring using react-native-svg — already a real,
 * properly-linked native dependency in this project (came bundled with
 * the SDK 57 template), not a new package requiring a rebuild.
 */
export default function ProgressRing({
  percent,
  size = 84,
  strokeWidth = 8,
  color,
  trackColor = '#EDEFE4',
  centerLabel,
}: ProgressRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, percent));
  const strokeDashoffset = circumference * (1 - clamped / 100);

  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={size} height={size} style={{ position: 'absolute' }}>
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={trackColor}
          strokeWidth={strokeWidth}
          fill="none"
        />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          fill="none"
          rotation="-90"
          origin={`${size / 2}, ${size / 2}`}
        />
      </Svg>
      <Text style={{ fontSize: 13, fontWeight: '700', color: '#4A4640' }}>{centerLabel}</Text>
    </View>
  );
}
