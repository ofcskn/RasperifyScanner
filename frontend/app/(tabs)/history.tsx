import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, FlatList, StyleSheet, ActivityIndicator,
  TouchableOpacity, TextInput, Image,
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
    } catch (err) {
      const status = (err as any)?.response?.status;
      if (status === 401) {
        setError('Session expired. Please log in again.');
      } else if (status) {
        setError(`Failed to load results (error ${status}).`);
      } else {
        setError('Cannot reach the server. Is the Pi connected?');
      }
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

  const DENSITY_COLORS: Record<string, string> = {
    empty: '#6b7280', sparse: '#059669', moderate: '#d97706',
    dense: '#ea580c', packed: '#dc2626',
  };

  const renderItem = ({ item }: { item: AnalysisResult }) => {
    const env: EnvironmentScan | null = item.environment_scan ?? null;
    const densityColor = env ? (DENSITY_COLORS[env.crowd_density] ?? '#6b7280') : '#6b7280';
    return (
      <View style={styles.card}>
        {/* Thumbnail */}
        {item.frame_thumbnail ? (
          <Image
            source={{ uri: `data:image/jpeg;base64,${item.frame_thumbnail}` }}
            style={styles.thumbnail}
            resizeMode="cover"
          />
        ) : (
          <View style={styles.thumbnailPlaceholder}>
            <Text style={styles.thumbnailPlaceholderText}>No image</Text>
          </View>
        )}

        {/* Header row */}
        <View style={styles.cardHeader}>
          <Text style={styles.provider}>{item.provider.toUpperCase()}</Text>
          <Text style={styles.timestamp}>{new Date(item.created_at).toLocaleString()}</Text>
        </View>

        {/* Environment summary */}
        {env ? (
          <View style={styles.envRow}>
            <Text style={styles.envIcon}>{ENV_ICONS[env.environment_type] ?? '📷'}</Text>
            <Text style={styles.envType}>{env.environment_type.replace('_', ' ')}</Text>
            <View style={[styles.densityBadge, { backgroundColor: densityColor }]}>
              <Text style={styles.densityText}>{env.crowd_density}</Text>
            </View>
            <Text style={styles.dot}>·</Text>
            <Text style={styles.peopleCount}>👥 {env.people_count}</Text>
          </View>
        ) : (
          <Text style={styles.frameId}>Frame: {item.frame_id.slice(0, 12)}…</Text>
        )}

        {/* Detections */}
        {item.detections.length > 0 && (
          <>
            <View style={styles.divider} />
            {item.detections.slice(0, 3).map((d, i) => (
              <View key={i} style={styles.detectionRow}>
                <Text style={styles.objName}>{d.object_name}</Text>
                <Text style={styles.conf}>{(d.confidence * 100).toFixed(0)}%</Text>
              </View>
            ))}
            {item.detections.length > 3 && (
              <Text style={styles.more}>+{item.detections.length - 3} more</Text>
            )}
          </>
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
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={() => load(1, applied)}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderItem}
          onEndReached={loadMore}
          onEndReachedThreshold={0.3}
          ListEmptyComponent={
            !loading ? (
              <Text style={styles.emptyText}>No results yet. Run a scan to get started.</Text>
            ) : null
          }
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
  errorContainer: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 40 },
  errorText: { color: '#dc2626', textAlign: 'center', fontSize: 14, marginBottom: 16 },
  retryBtn: { backgroundColor: '#2563eb', paddingHorizontal: 20, paddingVertical: 10, borderRadius: 8 },
  retryText: { color: '#fff', fontWeight: '600', fontSize: 14 },
  emptyText: { textAlign: 'center', color: '#9ca3af', marginTop: 60, fontSize: 14, paddingHorizontal: 32 },

  card: { backgroundColor: '#fff', borderRadius: 12, marginBottom: 12, shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 8, elevation: 3, overflow: 'hidden' },
  thumbnail: { width: '100%', height: 160, backgroundColor: '#0f172a' },
  thumbnailPlaceholder: { width: '100%', height: 120, backgroundColor: '#1e293b', justifyContent: 'center', alignItems: 'center' },
  thumbnailPlaceholderText: { color: '#475569', fontSize: 12 },

  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 12, paddingTop: 10, paddingBottom: 6 },
  provider: { fontSize: 11, fontWeight: '700', color: '#2563eb', backgroundColor: '#eff6ff', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  timestamp: { fontSize: 11, color: '#9ca3af' },

  envRow: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', paddingHorizontal: 12, paddingBottom: 8, gap: 6 },
  envIcon: { fontSize: 15 },
  envType: { fontSize: 13, fontWeight: '600', color: '#1e3a5f', textTransform: 'capitalize' },
  densityBadge: { paddingHorizontal: 7, paddingVertical: 2, borderRadius: 5 },
  densityText: { color: '#fff', fontSize: 10, fontWeight: '700', textTransform: 'uppercase' },
  dot: { fontSize: 13, color: '#d1d5db' },
  peopleCount: { fontSize: 13, color: '#374151' },

  frameId: { fontSize: 12, color: '#6b7280', paddingHorizontal: 12, paddingBottom: 8 },
  divider: { height: 1, backgroundColor: '#f3f4f6', marginHorizontal: 12 },
  detectionRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4, paddingHorizontal: 12 },
  objName: { fontSize: 13, color: '#111827' },
  conf: { fontSize: 13, fontWeight: '500', color: '#059669' },
  more: { fontSize: 12, color: '#9ca3af', paddingHorizontal: 12, paddingBottom: 10 },
});
