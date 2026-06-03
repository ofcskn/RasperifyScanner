import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, FlatList, StyleSheet, ActivityIndicator,
  TouchableOpacity, TextInput,
} from 'react-native';
import { fetchResults, AnalysisResult, ResultFilters, EnvironmentScan } from '../../services/api';

export default function HistoryScreen() {
  const [items, setItems] = useState<AnalysisResult[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showFilters, setShowFilters] = useState(false);
  const [draft, setDraft] = useState<ResultFilters>({});
  const [applied, setApplied] = useState<ResultFilters>({});

  const load = useCallback(async (p: number, filters: ResultFilters) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchResults(p, 20, filters);
      if (p === 1) {
        setItems(data.items);
      } else {
        setItems((prev) => [...prev, ...data.items]);
      }
      setTotal(data.total);
      setPage(p);
    } catch {
      setError('Failed to load results. Is the Pi connected?');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(1, applied); }, [load, applied]);

  const loadMore = () => {
    if (!loading && items.length < total) load(page + 1, applied);
  };

  const applyFilters = () => {
    setApplied({ ...draft });
    setShowFilters(false);
  };

  const clearFilters = () => {
    setDraft({});
    setApplied({});
    setShowFilters(false);
  };

  const hasFilters = Object.values(applied).some(Boolean);

  const ENV_ICONS: Record<string, string> = {
    train: '🚆', bus: '🚌', subway: '🚇', tram: '🚊',
    club: '🎶', bar: '🍺', restaurant: '🍽️', cafe: '☕',
    park: '🌳', street: '🏙️', office: '🏢', shop: '🛍️',
    stadium: '🏟️', waiting_room: '🪑', unknown: '📷',
  };

  const renderItem = ({ item }: { item: AnalysisResult }) => {
    const env: EnvironmentScan | null = item.environment_scan ?? null;
    return (
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Text style={styles.provider}>{item.provider.toUpperCase()}</Text>
          <Text style={styles.timestamp}>{new Date(item.created_at).toLocaleString()}</Text>
        </View>

        {env ? (
          <View style={styles.envRow}>
            <Text style={styles.envIcon}>{ENV_ICONS[env.environment_type] ?? '📷'}</Text>
            <Text style={styles.envType}>{env.environment_type.replace('_', ' ')}</Text>
            <Text style={styles.dot}>·</Text>
            <Text style={styles.peopleCount}>👥 {env.people_count}</Text>
            <Text style={styles.dot}>·</Text>
            <Text style={styles.density}>{env.crowd_density}</Text>
          </View>
        ) : (
          <Text style={styles.frameId}>Frame: {item.frame_id.slice(0, 12)}…</Text>
        )}

        <Text style={styles.detectionCount}>
          {item.detections.length} detection{item.detections.length !== 1 ? 's' : ''}
        </Text>
        {item.detections.slice(0, 3).map((d, i) => (
          <View key={i} style={styles.detectionRow}>
            <Text style={styles.objName}>{d.object_name}</Text>
            <Text style={styles.conf}>{(d.confidence * 100).toFixed(0)}%</Text>
          </View>
        ))}
        {item.detections.length > 3 && (
          <Text style={styles.more}>+{item.detections.length - 3} more</Text>
        )}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.topBar}>
        <Text style={styles.header}>History ({total})</Text>
        <TouchableOpacity
          style={[styles.filterBtn, hasFilters && styles.filterBtnActive]}
          onPress={() => setShowFilters((v) => !v)}
        >
          <Text style={[styles.filterBtnText, hasFilters && styles.filterBtnTextActive]}>
            {hasFilters ? 'Filtered ▾' : 'Filter ▾'}
          </Text>
        </TouchableOpacity>
      </View>

      {showFilters && (
        <View style={styles.filterPanel}>
          <TextInput
            style={styles.input}
            placeholder="From date (YYYY-MM-DD)"
            value={draft.dateFrom ?? ''}
            onChangeText={(v) => setDraft((d) => ({ ...d, dateFrom: v || undefined }))}
          />
          <TextInput
            style={styles.input}
            placeholder="To date (YYYY-MM-DD)"
            value={draft.dateTo ?? ''}
            onChangeText={(v) => setDraft((d) => ({ ...d, dateTo: v || undefined }))}
          />
          <TextInput
            style={styles.input}
            placeholder="Object name (e.g. person)"
            value={draft.objectName ?? ''}
            onChangeText={(v) => setDraft((d) => ({ ...d, objectName: v || undefined }))}
          />
          <TextInput
            style={styles.input}
            placeholder="Min confidence % (0–100)"
            value={draft.minConfidence != null ? String(draft.minConfidence) : ''}
            onChangeText={(v) => setDraft((d) => ({ ...d, minConfidence: v ? parseFloat(v) : undefined }))}
            keyboardType="numeric"
          />
          <TextInput
            style={styles.input}
            placeholder="Environment type (e.g. train, bus, club)"
            value={draft.environmentType ?? ''}
            onChangeText={(v) => setDraft((d) => ({ ...d, environmentType: v || undefined }))}
          />
          <View style={styles.filterActions}>
            <TouchableOpacity style={styles.clearBtn} onPress={clearFilters}>
              <Text style={styles.clearText}>Clear</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.applyBtn} onPress={applyFilters}>
              <Text style={styles.applyText}>Apply</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {error ? (
        <Text style={styles.error}>{error}</Text>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderItem}
          onEndReached={loadMore}
          onEndReachedThreshold={0.3}
          ListFooterComponent={loading ? <ActivityIndicator style={{ margin: 16 }} color="#2563eb" /> : null}
          contentContainerStyle={{ padding: 16, paddingBottom: 32 }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f0f4f8' },
  topBar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingTop: 16, paddingBottom: 4 },
  header: { fontSize: 18, fontWeight: 'bold', color: '#1e3a5f' },
  filterBtn: { borderWidth: 1, borderColor: '#d1d5db', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8 },
  filterBtnActive: { backgroundColor: '#2563eb', borderColor: '#2563eb' },
  filterBtnText: { fontSize: 13, fontWeight: '600', color: '#374151' },
  filterBtnTextActive: { color: '#fff' },
  filterPanel: { backgroundColor: '#fff', marginHorizontal: 12, borderRadius: 12, padding: 14, marginBottom: 8, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 6, elevation: 2 },
  input: { borderWidth: 1, borderColor: '#d1d5db', borderRadius: 8, padding: 9, fontSize: 14, marginBottom: 8 },
  filterActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 10, marginTop: 4 },
  clearBtn: { paddingHorizontal: 14, paddingVertical: 8 },
  clearText: { color: '#6b7280', fontWeight: '600' },
  applyBtn: { backgroundColor: '#2563eb', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 8 },
  applyText: { color: '#fff', fontWeight: '600' },
  error: { color: '#dc2626', textAlign: 'center', margin: 32 },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 14, marginBottom: 12, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 6, elevation: 2 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  provider: { fontSize: 11, fontWeight: '700', color: '#2563eb', backgroundColor: '#eff6ff', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  timestamp: { fontSize: 11, color: '#9ca3af' },
  frameId: { fontSize: 12, color: '#6b7280', marginBottom: 4 },
  detectionCount: { fontSize: 13, fontWeight: '600', color: '#374151', marginBottom: 4 },
  detectionRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 2 },
  objName: { fontSize: 13, color: '#111827' },
  conf: { fontSize: 13, fontWeight: '500', color: '#059669' },
  more: { fontSize: 12, color: '#9ca3af', marginTop: 4 },
  envRow: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', marginBottom: 4, gap: 4 },
  envIcon: { fontSize: 14 },
  envType: { fontSize: 13, fontWeight: '600', color: '#1e3a5f', textTransform: 'capitalize' },
  dot: { fontSize: 13, color: '#d1d5db' },
  peopleCount: { fontSize: 13, color: '#374151' },
  density: { fontSize: 12, color: '#6b7280', textTransform: 'capitalize' },
});
