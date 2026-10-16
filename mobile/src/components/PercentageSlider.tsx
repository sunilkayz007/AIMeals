import { useRef, useState } from 'react';
import { View, PanResponder } from 'react-native';

interface PercentageSliderProps {
  value: number; // 0-100
  onChange: (value: number) => void;
  accentColor: string;
  trackColor?: string;
}

/**
 * A drag-to-select percentage slider, built entirely from core React
 * Native APIs (View, PanResponder) — deliberately NOT using HeroUI
 * Native's Slider component, since its exact props/API were never
 * verified against real docs, and guessing at a third-party API is
 * exactly the kind of mistake this session has worked hard to avoid
 * elsewhere (see the HeroUI Select decision earlier).
 *
 * Uses pageX (absolute screen coordinate) minus the track's measured
 * absolute page offset, consistently for both the initial touch and
 * every subsequent move — this avoids a known PanResponder gotcha
 * where `locationX` can behave inconsistently between the "grant" and
 * "move" phases of a gesture on some RN versions/platforms.
 */
export default function PercentageSlider({
  value,
  onChange,
  accentColor,
  trackColor = '#EDEFE4',
}: PercentageSliderProps) {
  const trackRef = useRef<View>(null);
  const trackPageXRef = useRef(0);
  const trackWidthRef = useRef(0);
  const [trackWidth, setTrackWidth] = useState(0);

  const handleLayout = () => {
    // measure() gives the absolute page position, not just the size —
    // needed to convert an absolute touch coordinate (pageX) into a
    // position relative to this specific track.
    trackRef.current?.measure((_x, _y, width, _height, pageX) => {
      trackPageXRef.current = pageX;
      trackWidthRef.current = width;
      setTrackWidth(width);
    });
  };

  const updateFromPageX = (pageX: number) => {
    const width = trackWidthRef.current;
    if (width <= 0) return;
    const relativeX = pageX - trackPageXRef.current;
    const clamped = Math.max(0, Math.min(width, relativeX));
    const pct = Math.round((clamped / width) * 100);
    onChange(pct);
  };

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: (evt) => updateFromPageX(evt.nativeEvent.pageX),
      onPanResponderMove: (evt) => updateFromPageX(evt.nativeEvent.pageX),
    })
  ).current;

  const thumbSize = 20;
  const thumbLeft = trackWidth > 0 ? (value / 100) * trackWidth - thumbSize / 2 : -thumbSize / 2;

  return (
    <View
      ref={trackRef}
      onLayout={handleLayout}
      {...panResponder.panHandlers}
      style={{ height: 32, justifyContent: 'center' }}
    >
      <View
        style={{
          height: 6,
          borderRadius: 100,
          backgroundColor: trackColor,
          overflow: 'hidden',
        }}
      >
        <View
          style={{
            height: 6,
            width: `${value}%`,
            backgroundColor: accentColor,
          }}
        />
      </View>
      <View
        style={{
          position: 'absolute',
          left: thumbLeft,
          width: thumbSize,
          height: thumbSize,
          borderRadius: thumbSize / 2,
          backgroundColor: accentColor,
          borderWidth: 2,
          borderColor: '#fff',
          shadowColor: '#000',
          shadowOpacity: 0.15,
          shadowRadius: 3,
          shadowOffset: { width: 0, height: 1 },
          elevation: 2,
        }}
      />
    </View>
  );
}
