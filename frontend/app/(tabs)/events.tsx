import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl, ActivityIndicator } from 'react-native';
import { fetchEvents, EventItem } from '../../services/api';
import { wsService } from '../../services/websocket';
import { Card } from '../../components/Card';
import { Badge } from '../../components/Badge';
import { ErrorView } from '../../components/ErrorView';
import { Colors, Spacing } from '../../constants/theme';

const SEVERITY_VARIANT: Record<string, 'info' | 'warning' | 'danger' | 'success'> = {
  info: 'info',
  warning: 'warning',
  error: 'danger',
  critical: 'danger',
  success: 'success',
};

export default function EventsScreen() {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const data = await fetchEvents(1, 50);
      setEvents(data.items);
    } catch {
      setError('Could not load events. Check the backend connection.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Live: prepend new events as they arrive over the WebSocket.
  useEffect(() => {
    const unsub = wsService.subscribe((data) => {
      const ev = data as { event: string } & EventItem;
      if (ev.event === 'event') {
        setEvents((prev) => [
          {
            id: ev.id,
            kind: ev.kind,
            severity: ev.severity,
            message: ev.message,
            data_json: (ev as any).data ?? null,
            created_at: ev.created_at,
          },
          ...prev,
        ].slice(0, 100));
      }
    });
    return () => { unsub(); };
  }, []);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={Colors.primary} />
      </View>
    );
  }

  if (error) {
    return <ErrorView message={error} onRetry={load} />;
  }

  return (
    <FlatList
      style={styles.list}
      contentContainerStyle={styles.content}
      data={events}
      keyExtractor={(e) => String(e.id)}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />
      }
      ListEmptyComponent={
        <View style={styles.center}>
          <Text style={styles.emptyIcon}>🔔</Text>
          <Text style={styles.emptyText}>No events yet</Text>
          <Text style={styles.emptySub}>Alerts and system events will appear here.</Text>
        </View>
      }
      renderItem={({ item }) => (
        <Card style={styles.card}>
          <View style={styles.row}>
            <Badge label={item.kind} variant={SEVERITY_VARIANT[item.severity] ?? 'neutral'} size="sm" />
            <Text style={styles.time}>{new Date(item.created_at).toLocaleString()}</Text>
          </View>
          <Text style={styles.message}>{item.message}</Text>
        </Card>
      )}
    />
  );
}

const styles = StyleSheet.create({
  list: { flex: 1, backgroundColor: Colors.background ?? '#f3f4f6' },
  content: { padding: Spacing.md, gap: Spacing.sm },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: Spacing.xl, gap: 6 },
  card: { gap: 6 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  time: { fontSize: 11, color: '#6b7280' },
  message: { fontSize: 14, color: '#111827' },
  emptyIcon: { fontSize: 40 },
  emptyText: { fontSize: 16, fontWeight: '700', color: '#4b5563' },
  emptySub: { fontSize: 13, color: '#6b7280', textAlign: 'center' },
});
