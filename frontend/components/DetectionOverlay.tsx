import React, { useState } from 'react';
import { View, Text, StyleSheet, LayoutChangeEvent } from 'react-native';
import type { Detection } from '../services/api';

interface Props {
  detections: Detection[];
  /** Source frame size, used only for its aspect ratio. */
  frameSize?: { width: number; height: number } | null;
}

/**
 * Maps normalized [x1,y1,x2,y2] boxes onto a frame rendered with
 * resizeMode="contain". The image is letterboxed inside this overlay, so we
 * first compute the displayed image rect (offset + size) from the container
 * size and the frame aspect ratio, then place each box within that rect.
 */
export function computeImageRect(
  containerW: number,
  containerH: number,
  frameW: number,
  frameH: number
) {
  if (containerW <= 0 || containerH <= 0 || frameW <= 0 || frameH <= 0) {
    return { offX: 0, offY: 0, dispW: containerW, dispH: containerH };
  }
  const containerAspect = containerW / containerH;
  const frameAspect = frameW / frameH;
  let dispW: number;
  let dispH: number;
  if (frameAspect > containerAspect) {
    // Frame is wider — full width, letterbox top/bottom.
    dispW = containerW;
    dispH = containerW / frameAspect;
  } else {
    dispH = containerH;
    dispW = containerH * frameAspect;
  }
  return { offX: (containerW - dispW) / 2, offY: (containerH - dispH) / 2, dispW, dispH };
}

export default function DetectionOverlay({ detections, frameSize }: Props) {
  const [size, setSize] = useState({ w: 0, h: 0 });

  const onLayout = (e: LayoutChangeEvent) => {
    const { width, height } = e.nativeEvent.layout;
    setSize({ w: width, h: height });
  };

  const fw = frameSize?.width ?? 16;
  const fh = frameSize?.height ?? 9;
  const { offX, offY, dispW, dispH } = computeImageRect(size.w, size.h, fw, fh);

  return (
    <View style={StyleSheet.absoluteFill} onLayout={onLayout} pointerEvents="none">
      {detections.map((d, i) => {
        const [x1, y1, x2, y2] = d.bbox;
        const isPerson = d.label === 'person';
        const color = isPerson ? '#22d3ee' : '#a3e635';
        const left = offX + x1 * dispW;
        const top = offY + y1 * dispH;
        const width = (x2 - x1) * dispW;
        const height = (y2 - y1) * dispH;
        if (width <= 0 || height <= 0) return null;
        return (
          <View key={`${d.track_id ?? 'd'}-${i}`} style={[styles.box, { left, top, width, height, borderColor: color }]}>
            <View style={[styles.labelChip, { backgroundColor: color }]}>
              <Text style={styles.labelText}>
                {d.label} {Math.round(d.confidence * 100)}%
              </Text>
            </View>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  box: { position: 'absolute', borderWidth: 2, borderRadius: 4 },
  labelChip: {
    position: 'absolute', top: -18, left: -2, paddingHorizontal: 5, paddingVertical: 1, borderRadius: 3,
  },
  labelText: { color: '#06202a', fontSize: 10, fontWeight: '800' },
});
