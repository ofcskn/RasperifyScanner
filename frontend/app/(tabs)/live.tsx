import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, Image, TouchableOpacity, ActivityIndicator,
} from 'react-native';
import { wsService } from '../../services/websocket';
import { fetchHealth, connectCamera, disconnectCamera } from '../../services/api';
import type { Detection, Counts } from '../../services/api';
import DetectionOverlay from '../../components/DetectionOverlay';

interface HealthData {
  status: string;
  camera_connected: boolean;
  active_adapter: string | null;
  cpu_percent: number | null;
  memory_percent: number | null;
}

export default function LiveScreen() {
  const [liveFrame, setLiveFrame] = useState<string | null>(null);
  const [detections, setDetections] = useState<Detection[]>([]);
  const [counts, setCounts] = useState<Counts>({ live: 0, cumulative: 0 });
  const [frameSize, setFrameSize] = useState<{ width: number; height: number } | null>(null);
  const [degraded, setDegraded] = useState(false);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [cameraLoading, setCameraLoading] = useState(false);
  const [lastFrameAt, setLastFrameAt] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());

  // Tick every second so the "X s ago" label stays fresh.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  // Subscribe to live_frame WebSocket events.
  // The WebSocket is connected at the app level (_layout.tsx), so just subscribe here.
  useEffect(() => {
    const unsub = wsService.subscribe((data) => {
      const ev = data as {
        event: string;
        frame_thumbnail?: string;
        detections?: Detection[];
        counts?: Counts;
        frame_size?: { width: number; height: number };
        degraded?: boolean;
      };
      if (ev.event === 'live_frame' && ev.frame_thumbnail) {
        setLiveFrame(ev.frame_thumbnail);
        setDetections(ev.detections ?? []);
        if (ev.counts) setCounts(ev.counts);
        if (ev.frame_size) setFrameSize(ev.frame_size);
        setDegraded(!!ev.degraded);
        setLastFrameAt(Date.now());
      }
    });
    return () => { unsub(); };
  }, []);

  // Poll health every 5 seconds.
  useEffect(() => {
    const load = async () => {
      try {
        setHealth(await fetchHealth());
      } catch {
        // keep last known state on error
      }
    };
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  const toggleCamera = useCallback(async () => {
    setCameraLoading(true);
    try {
      if (health?.camera_connected) {
        await disconnectCamera();
        setLiveFrame(null);
        setDetections([]);
        setCounts({ live: 0, cumulative: 0 });
        setLastFrameAt(null);
      } else {
        await connectCamera();
      }
      setHealth(await fetchHealth());
    } catch {
      // health poll will correct the displayed state
    } finally {
      setCameraLoading(false);
    }
  }, [health?.camera_connected]);

  const cameraOn = health?.camera_connected ?? false;
  const isLive = !!liveFrame;
  const secondsAgo = lastFrameAt != null ? Math.round((now - lastFrameAt) / 1000) : null;

  return (
    <View style={styles.container}>
      {/* Status bar */}
      <View style={styles.statusBar}>
        <View style={styles.statusLeft}>
          <View style={[styles.dot, { backgroundColor: cameraOn ? '#059669' : '#6b7280' }]} />
          <Text style={styles.statusText}>
            {cameraOn ? 'Camera Active' : 'Camera Offline'}
          </Text>
        </View>
        <View style={styles.statusRight}>
          {isLive && (
            <>
              <View style={styles.countChip}>
                <Text style={styles.countChipLabel}>IN FRAME</Text>
                <Text style={styles.countChipValue}>{counts.live}</Text>
              </View>
              <View style={[styles.countChip, styles.countChipAlt]}>
                <Text style={styles.countChipLabel}>UNIQUE</Text>
                <Text style={styles.countChipValue}>{counts.cumulative}</Text>
              </View>
              <View style={styles.livePill}>
                <View style={styles.livePillDot} />
                <Text style={styles.livePillText}>LIVE</Text>
              </View>
            </>
          )}
        </View>
      </View>

      {/* Frame — fills the middle of the screen */}
      <View style={styles.frameArea}>
        {liveFrame ? (
          <View style={styles.frameWrap}>
            <Image
              source={{ uri: `data:image/jpeg;base64,${liveFrame}` }}
              style={styles.frame}
              resizeMode="contain"
            />
            <DetectionOverlay detections={detections} frameSize={frameSize} />
            {degraded && (
              <View style={styles.degradedPill}>
                <Text style={styles.degradedText}>Reduced frame rate (CPU busy)</Text>
              </View>
            )}
          </View>
        ) : (
          <View style={styles.noSignal}>
            <Text style={styles.noSignalIcon}>📷</Text>
            <Text style={styles.noSignalTitle}>No Signal</Text>
            <Text style={styles.noSignalSub}>
              {cameraOn
                ? 'Waiting for frames from the Pi…'
                : 'Tap Connect Camera to start live view'}
            </Text>
          </View>
        )}
      </View>

      {/* Connect / Disconnect button */}
      <View style={styles.controls}>
        {health === null ? (
          <ActivityIndicator color="#2563eb" style={{ marginVertical: 8 }} />
        ) : (
          <TouchableOpacity
            style={[styles.camBtn, cameraOn ? styles.camBtnDisconnect : styles.camBtnConnect]}
            onPress={toggleCamera}
            disabled={cameraLoading}
          >
            {cameraLoading ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Text style={styles.camBtnText}>
                {cameraOn ? 'Disconnect Camera' : 'Connect Camera'}
              </Text>
            )}
          </TouchableOpacity>
        )}
      </View>

      {/* Info strip */}
      <View style={styles.infoStrip}>
        <Text style={styles.infoItem}>
          Adapter:{' '}
          <Text style={styles.infoValue}>{health?.active_adapter ?? '—'}</Text>
        </Text>
        {health?.cpu_percent != null && (
          <Text style={styles.infoItem}>
            CPU: <Text style={styles.infoValue}>{health.cpu_percent.toFixed(0)}%</Text>
          </Text>
        )}
        {secondsAgo !== null && (
          <Text style={styles.infoItem}>
            Frame: <Text style={styles.infoValue}>{secondsAgo}s ago</Text>
          </Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0a0a' },

  statusBar: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 16, paddingTop: 14, paddingBottom: 10,
  },
  statusLeft: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  statusText: { fontSize: 13, color: '#9ca3af', fontWeight: '500' },
  livePill: {
    flexDirection: 'row', alignItems: 'center', gap: 5,
    backgroundColor: '#dc2626', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20,
  },
  livePillDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: '#fff' },
  livePillText: { color: '#fff', fontSize: 11, fontWeight: '800', letterSpacing: 1 },
  statusRight: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  countChip: {
    backgroundColor: '#0e7490', borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3, alignItems: 'center',
  },
  countChipAlt: { backgroundColor: '#3f6212' },
  countChipLabel: { color: '#cffafe', fontSize: 8, fontWeight: '700', letterSpacing: 0.5 },
  countChipValue: { color: '#fff', fontSize: 15, fontWeight: '800' },

  frameArea: {
    flex: 1, backgroundColor: '#111827', justifyContent: 'center', alignItems: 'center',
  },
  frameWrap: { width: '100%', height: '100%' },
  frame: { width: '100%', height: '100%' },
  degradedPill: {
    position: 'absolute', bottom: 8, alignSelf: 'center',
    backgroundColor: 'rgba(217,119,6,0.9)', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12,
  },
  degradedText: { color: '#fff', fontSize: 11, fontWeight: '700' },

  noSignal: { alignItems: 'center', gap: 12 },
  noSignalIcon: { fontSize: 52 },
  noSignalTitle: { fontSize: 20, fontWeight: '700', color: '#4b5563' },
  noSignalSub: { fontSize: 14, color: '#374151', textAlign: 'center', paddingHorizontal: 40, lineHeight: 22 },

  controls: { paddingHorizontal: 16, paddingVertical: 14 },
  camBtn: {
    borderRadius: 10, paddingVertical: 14, alignItems: 'center', justifyContent: 'center',
  },
  camBtnConnect: { backgroundColor: '#2563eb' },
  camBtnDisconnect: { backgroundColor: '#dc2626' },
  camBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },

  infoStrip: {
    flexDirection: 'row', gap: 20, paddingHorizontal: 16, paddingBottom: 16, flexWrap: 'wrap',
  },
  infoItem: { fontSize: 12, color: '#6b7280' },
  infoValue: { color: '#9ca3af', fontWeight: '600' },
});
