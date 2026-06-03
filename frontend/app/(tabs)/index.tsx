import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, ActivityIndicator,
  TouchableOpacity, Alert, Image,
} from 'react-native';
import { wsService } from '../../services/websocket';
import { fetchHealth, triggerAnalysis, connectCamera, disconnectCamera, EnvironmentScan } from '../../services/api';

interface AnalysisEvent {
  event: string;
  id: number;
  frame_id: string;
  provider: string;
  frame_thumbnail: string | null;
  detections: Array<{ object_name: string; confidence: number }>;
  metrics: Record<string, number>;
  environment_scan: EnvironmentScan | null;
}

interface HealthData {
  status: string;
  camera_connected: boolean;
  active_adapter: string | null;
  cpu_percent: number | null;
  memory_percent: number | null;
}

const ENV_ICONS: Record<string, string> = {
  train: '🚆', bus: '🚌', subway: '🚇', tram: '🚊',
  club: '🎶', bar: '🍺', restaurant: '🍽️', cafe: '☕',
  park: '🌳', street: '🏙️', office: '🏢', shop: '🛍️',
  stadium: '🏟️', waiting_room: '🪑', unknown: '📷',
};

const DENSITY_COLORS: Record<string, string> = {
  empty: '#6b7280', sparse: '#059669', moderate: '#d97706',
  dense: '#ea580c', packed: '#dc2626',
};

function timeAgo(iso: string | null): string {
  if (!iso) return '—';
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

export default function DashboardScreen() {
  const [latest, setLatest] = useState<AnalysisEvent | null>(null);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [connected, setConnected] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [cameraLoading, setCameraLoading] = useState(false);
  const [lastScanTime, setLastScanTime] = useState<string | null>(null);

  useEffect(() => {
    wsService.connect();
    setConnected(true);
    const unsub = wsService.subscribe((data) => {
      const event = data as AnalysisEvent;
      if (event.event === 'analysis_complete') {
        setLatest(event);
        setLastScanTime(new Date().toISOString());
      }
    });
    return () => {
      unsub();
      wsService.disconnect();
      setConnected(false);
    };
  }, []);

  useEffect(() => {
    const load = async () => {
      try {
        const h = await fetchHealth();
        setHealth(h);
      } catch {
        setHealth({ status: 'unreachable', camera_connected: false, active_adapter: null, cpu_percent: null, memory_percent: null });
      }
    };
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  const runScanNow = useCallback(async () => {
    setScanning(true);
    try {
      await triggerAnalysis();
    } catch {
      Alert.alert('Scan Failed', 'Could not trigger analysis. Is the backend reachable?');
    } finally {
      setScanning(false);
    }
  }, []);

  const toggleCamera = useCallback(async () => {
    setCameraLoading(true);
    try {
      if (health?.camera_connected) {
        await disconnectCamera();
      } else {
        await connectCamera();
      }
      const h = await fetchHealth();
      setHealth(h);
    } catch {
      Alert.alert('Camera Error', 'Could not change camera state. Is the backend reachable?');
    } finally {
      setCameraLoading(false);
    }
  }, [health?.camera_connected]);

  const env = latest?.environment_scan ?? null;
  const envIcon = env ? (ENV_ICONS[env.environment_type] ?? '📷') : null;
  const densityColor = env ? (DENSITY_COLORS[env.crowd_density] ?? '#6b7280') : '#6b7280';

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>RasperifyScanner</Text>

      {/* Camera & Connection Status */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Camera & Connection</Text>
        {health ? (
          <>
            <View style={styles.cameraStatus}>
              <View style={[styles.statusDot, { backgroundColor: health.camera_connected ? '#059669' : '#dc2626' }]} />
              <Text style={styles.cameraStatusText}>
                {health.camera_connected ? 'Camera Connected' : 'Camera Disconnected'}
              </Text>
            </View>
            <View style={styles.statusRow}>
              <Text style={styles.rowLabel}>Backend</Text>
              <Text style={[styles.rowValue, { color: health.status === 'ok' ? '#059669' : '#dc2626' }]}>
                {health.status === 'ok' ? 'Online' : 'Offline'}
              </Text>
            </View>
            <View style={styles.statusRow}>
              <Text style={styles.rowLabel}>Network</Text>
              <Text style={styles.rowValue}>{health.active_adapter ?? 'None'}</Text>
            </View>
            {health.cpu_percent != null && (
              <View style={styles.statusRow}>
                <Text style={styles.rowLabel}>CPU / Memory</Text>
                <Text style={styles.rowValue}>
                  {health.cpu_percent.toFixed(1)}% / {health.memory_percent?.toFixed(1) ?? '—'}%
                </Text>
              </View>
            )}
            <View style={styles.statusRow}>
              <Text style={styles.rowLabel}>Live Stream</Text>
              <Text style={[styles.rowValue, { color: connected ? '#059669' : '#9ca3af' }]}>
                {connected ? 'Connected' : 'Disconnected'}
              </Text>
            </View>
          </>
        ) : (
          <ActivityIndicator color="#2563eb" />
        )}

        {health && (
          <TouchableOpacity
            style={[
              styles.liveModeBtn,
              health.camera_connected ? styles.liveModeBtnActive : styles.liveModeBtnInactive,
              cameraLoading && styles.scanBtnDisabled,
            ]}
            onPress={toggleCamera}
            disabled={cameraLoading}
          >
            {cameraLoading ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <>
                <View style={[styles.liveDot, { backgroundColor: health.camera_connected ? '#fff' : '#9ca3af' }]} />
                <Text style={styles.liveModeBtnText}>
                  {health.camera_connected ? 'LIVE  ·  Disconnect' : 'Connect Camera (Live Mode)'}
                </Text>
              </>
            )}
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={[styles.scanBtn, scanning && styles.scanBtnDisabled]}
          onPress={runScanNow}
          disabled={scanning}
        >
          {scanning
            ? <ActivityIndicator color="#fff" size="small" />
            : <Text style={styles.scanBtnText}>Run Scan Now</Text>
          }
        </TouchableOpacity>
      </View>

      {/* Current Environment */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Current Environment</Text>

        {latest?.frame_thumbnail ? (
          <Image
            source={{ uri: `data:image/jpeg;base64,${latest.frame_thumbnail}` }}
            style={styles.frameImage}
            resizeMode="cover"
          />
        ) : (
          <View style={styles.framePlaceholder}>
            <Text style={styles.framePlaceholderText}>No frame captured yet</Text>
          </View>
        )}

        {env ? (
          <>
            <View style={styles.envHeader}>
              <Text style={styles.envIcon}>{envIcon}</Text>
              <View style={styles.envHeaderText}>
                <Text style={styles.envType}>{env.environment_type.replace('_', ' ').toUpperCase()}</Text>
                <View style={[styles.densityBadge, { backgroundColor: densityColor }]}>
                  <Text style={styles.densityText}>{env.crowd_density.toUpperCase()}</Text>
                </View>
              </View>
              <View style={styles.peopleChip}>
                <Text style={styles.peopleNumber}>{env.people_count}</Text>
                <Text style={styles.peopleLabel}>people</Text>
              </View>
            </View>

            <View style={styles.ambientRow}>
              <Text style={styles.ambientItem}>💡 {env.ambient_conditions.lighting}</Text>
              <Text style={styles.ambientItem}>🕐 {env.ambient_conditions.estimated_time}</Text>
            </View>

            {env.notable_observations.length > 0 && (
              <>
                <Text style={styles.obsLabel}>Notable</Text>
                {env.notable_observations.map((obs, i) => (
                  <Text key={i} style={styles.obsItem}>• {obs}</Text>
                ))}
              </>
            )}

            <Text style={styles.scanMeta}>
              via {latest?.provider} · {timeAgo(lastScanTime)}
            </Text>
          </>
        ) : latest ? (
          <>
            <Text style={styles.sectionLabel}>Detections ({latest.detections.length})</Text>
            {latest.detections.map((d, i) => (
              <View key={i} style={styles.detectionRow}>
                <Text style={styles.objectName}>{d.object_name}</Text>
                <Text style={styles.confidence}>{(d.confidence * 100).toFixed(0)}%</Text>
              </View>
            ))}
          </>
        ) : (
          <Text style={styles.empty}>
            Use "Run Scan Now" or configure a schedule in Settings.
          </Text>
        )}
      </View>

      {/* Last scan info strip */}
      <View style={styles.infoStrip}>
        <Text style={styles.infoText}>
          Last scan: {timeAgo(lastScanTime)}
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f0f4f8' },
  content: { padding: 16, paddingBottom: 32 },
  title: { fontSize: 22, fontWeight: 'bold', color: '#1e3a5f', marginBottom: 16 },

  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 16, shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 8, elevation: 3 },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#1e3a5f', marginBottom: 12 },

  cameraStatus: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  statusDot: { width: 10, height: 10, borderRadius: 5, marginRight: 8 },
  cameraStatusText: { fontSize: 15, fontWeight: '600', color: '#111827' },

  statusRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 },
  rowLabel: { fontSize: 13, color: '#6b7280' },
  rowValue: { fontSize: 13, fontWeight: '500', color: '#111827' },

  liveModeBtn: { flexDirection: 'row', borderRadius: 10, paddingVertical: 10, alignItems: 'center', justifyContent: 'center', marginTop: 12, gap: 8 },
  liveModeBtnActive: { backgroundColor: '#dc2626' },
  liveModeBtnInactive: { backgroundColor: '#374151' },
  liveModeBtnText: { color: '#fff', fontWeight: '700', fontSize: 14 },
  liveDot: { width: 8, height: 8, borderRadius: 4 },

  scanBtn: { backgroundColor: '#2563eb', borderRadius: 10, paddingVertical: 12, alignItems: 'center', marginTop: 10 },
  scanBtnDisabled: { backgroundColor: '#93c5fd' },
  scanBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },

  frameImage: { width: '100%', height: 200, borderRadius: 8, marginBottom: 14, backgroundColor: '#0f172a' },
  framePlaceholder: { width: '100%', height: 200, borderRadius: 8, marginBottom: 14, backgroundColor: '#1e293b', justifyContent: 'center', alignItems: 'center' },
  framePlaceholderText: { color: '#475569', fontSize: 13 },

  envHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  envIcon: { fontSize: 32, marginRight: 12 },
  envHeaderText: { flex: 1 },
  envType: { fontSize: 16, fontWeight: '800', color: '#111827', letterSpacing: 0.5 },
  densityBadge: { marginTop: 4, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6, alignSelf: 'flex-start' },
  densityText: { color: '#fff', fontSize: 11, fontWeight: '700' },

  peopleChip: { alignItems: 'center', backgroundColor: '#eff6ff', borderRadius: 10, paddingHorizontal: 12, paddingVertical: 6 },
  peopleNumber: { fontSize: 26, fontWeight: '900', color: '#2563eb', lineHeight: 30 },
  peopleLabel: { fontSize: 10, color: '#6b7280', fontWeight: '600' },

  ambientRow: { flexDirection: 'row', gap: 16, marginBottom: 10 },
  ambientItem: { fontSize: 13, color: '#374151' },

  obsLabel: { fontSize: 13, fontWeight: '600', color: '#374151', marginBottom: 4 },
  obsItem: { fontSize: 13, color: '#4b5563', paddingVertical: 2 },

  scanMeta: { fontSize: 11, color: '#9ca3af', marginTop: 10, textAlign: 'right' },

  sectionLabel: { fontSize: 13, fontWeight: '600', color: '#374151', marginBottom: 4 },
  detectionRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4, borderBottomWidth: 0.5, borderBottomColor: '#e5e7eb' },
  objectName: { fontSize: 14, color: '#111827' },
  confidence: { fontSize: 14, fontWeight: '600', color: '#2563eb' },

  empty: { fontSize: 14, color: '#9ca3af', textAlign: 'center', paddingVertical: 20, lineHeight: 22 },

  infoStrip: { backgroundColor: '#eff6ff', borderRadius: 8, padding: 10, alignItems: 'center' },
  infoText: { fontSize: 12, color: '#3b82f6' },
});
