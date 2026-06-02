import React, { useEffect, useState } from 'react';
import { View, Text, Image, ScrollView, StyleSheet, ActivityIndicator, TouchableOpacity } from 'react-native';
import { wsService } from '../../services/websocket';
import { fetchHealth } from '../../services/api';

interface Detection {
  object_name: string;
  confidence: number;
  bbox: object | null;
}

interface AnalysisEvent {
  event: string;
  id: number;
  frame_id: string;
  provider: string;
  detections: Detection[];
  metrics: Record<string, number>;
}

interface HealthData {
  status: string;
  camera_connected: boolean;
  active_adapter: string | null;
  cpu_percent: number | null;
  memory_percent: number | null;
}

export default function DashboardScreen() {
  const [latest, setLatest] = useState<AnalysisEvent | null>(null);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    wsService.connect();
    setConnected(true);
    const unsub = wsService.subscribe((data) => {
      const event = data as AnalysisEvent;
      if (event.event === 'analysis_complete') setLatest(event);
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

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>RasperifyScanner</Text>

      {/* System Status */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>System Status</Text>
        {health ? (
          <>
            <StatusRow label="Backend" value={health.status === 'ok' ? '✅ Online' : '❌ Offline'} />
            <StatusRow label="Camera" value={health.camera_connected ? '✅ Connected' : '❌ Disconnected'} />
            <StatusRow label="Active Adapter" value={health.active_adapter ?? 'None'} />
            {health.cpu_percent != null && <StatusRow label="CPU" value={`${health.cpu_percent.toFixed(1)}%`} />}
            {health.memory_percent != null && <StatusRow label="Memory" value={`${health.memory_percent.toFixed(1)}%`} />}
          </>
        ) : (
          <ActivityIndicator color="#2563eb" />
        )}
        <StatusRow label="WebSocket" value={connected ? '✅ Connected' : '❌ Disconnected'} />
      </View>

      {/* Latest Analysis */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Latest Analysis</Text>
        {latest ? (
          <>
            <Text style={styles.meta}>Provider: {latest.provider} · Frame: {latest.frame_id.slice(0, 8)}…</Text>
            <Text style={styles.sectionLabel}>Detections ({latest.detections.length})</Text>
            {latest.detections.map((d, i) => (
              <View key={i} style={styles.detectionRow}>
                <Text style={styles.objectName}>{d.object_name}</Text>
                <Text style={styles.confidence}>{(d.confidence * 100).toFixed(0)}%</Text>
              </View>
            ))}
            {Object.keys(latest.metrics).length > 0 && (
              <>
                <Text style={styles.sectionLabel}>Metrics</Text>
                {Object.entries(latest.metrics).map(([k, v]) => (
                  <StatusRow key={k} label={k} value={v.toFixed(3)} />
                ))}
              </>
            )}
          </>
        ) : (
          <Text style={styles.empty}>Waiting for analysis results…</Text>
        )}
      </View>
    </ScrollView>
  );
}

function StatusRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f0f4f8' },
  content: { padding: 16, paddingBottom: 32 },
  title: { fontSize: 22, fontWeight: 'bold', color: '#1e3a5f', marginBottom: 16 },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 16, shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 8, elevation: 3 },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#1e3a5f', marginBottom: 12 },
  meta: { fontSize: 12, color: '#6b7280', marginBottom: 8 },
  sectionLabel: { fontSize: 13, fontWeight: '600', color: '#374151', marginTop: 8, marginBottom: 4 },
  detectionRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4, borderBottomWidth: 0.5, borderBottomColor: '#e5e7eb' },
  objectName: { fontSize: 14, color: '#111827' },
  confidence: { fontSize: 14, fontWeight: '600', color: '#2563eb' },
  row: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 },
  rowLabel: { fontSize: 13, color: '#6b7280' },
  rowValue: { fontSize: 13, fontWeight: '500', color: '#111827' },
  empty: { fontSize: 14, color: '#9ca3af', textAlign: 'center', paddingVertical: 16 },
});
