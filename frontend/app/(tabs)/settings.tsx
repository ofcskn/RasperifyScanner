import React, { useEffect, useState } from 'react';
import {
  View, Text, FlatList, StyleSheet, Switch, TouchableOpacity,
  TextInput, Modal, Alert, ActivityIndicator,
} from 'react-native';
import {
  fetchSchedules, createSchedule, toggleSchedule, deleteSchedule,
  Schedule, fetchHealth,
} from '../../services/api';

export default function SettingsScreen() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [loadError, setLoadError] = useState(false);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [newName, setNewName] = useState('');
  const [newInterval, setNewInterval] = useState('30');

  const loadAll = async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const [s, h] = await Promise.all([fetchSchedules(), fetchHealth()]);
      setSchedules(s);
      setHealth(h);
    } catch {
      setHealth({ adapters: [] });
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, []);

  const handleToggle = async (id: number, current: boolean) => {
    await toggleSchedule(id, !current);
    setSchedules((prev) => prev.map((s) => s.id === id ? { ...s, enabled: !current } : s));
  };

  const handleDelete = (id: number) => {
    Alert.alert('Delete Schedule', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete', style: 'destructive', onPress: async () => {
          await deleteSchedule(id);
          setSchedules((prev) => prev.filter((s) => s.id !== id));
        },
      },
    ]);
  };

  const handleCreate = async () => {
    const interval = parseInt(newInterval, 10);
    if (!newName || isNaN(interval) || interval < 5) {
      Alert.alert('Invalid input', 'Name required and interval must be ≥ 5 seconds.');
      return;
    }
    const sched = await createSchedule(newName, interval);
    setSchedules((prev) => [sched, ...prev]);
    setModalVisible(false);
    setNewName('');
    setNewInterval('30');
  };

  const renderSchedule = ({ item }: { item: Schedule }) => (
    <View style={styles.card}>
      <View style={styles.row}>
        <View style={{ flex: 1 }}>
          <Text style={styles.schedName}>{item.name}</Text>
          <Text style={styles.schedMeta}>Every {item.interval_seconds}s · ✅ {item.success_count} · ❌ {item.fail_count}</Text>
          {item.last_run && <Text style={styles.schedMeta}>Last: {new Date(item.last_run).toLocaleString()}</Text>}
        </View>
        <Switch value={item.enabled} onValueChange={() => handleToggle(item.id, item.enabled)} trackColor={{ true: '#2563eb' }} />
      </View>
      <TouchableOpacity onPress={() => handleDelete(item.id)}>
        <Text style={styles.deleteBtn}>Delete</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <View style={styles.container}>
      {/* Network / Health Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Network Adapters</Text>
        {health?.adapters?.map((a: any) => (
          <View key={a.name} style={styles.adapterRow}>
            <Text style={[styles.adapterName, { color: a.up ? '#059669' : '#9ca3af' }]}>
              {a.up ? '●' : '○'} {a.name} ({a.interface})
            </Text>
            <Text style={styles.adapterIp}>{a.ip ?? '—'}</Text>
          </View>
        )) ?? <Text style={styles.offline}>Pi offline</Text>}
      </View>

      {/* Schedules Section */}
      <View style={[styles.section, { flex: 1 }]}>
        <View style={styles.row}>
          <Text style={styles.sectionTitle}>Analysis Schedules</Text>
          <TouchableOpacity style={styles.addBtn} onPress={() => setModalVisible(true)}>
            <Text style={styles.addBtnText}>+ Add</Text>
          </TouchableOpacity>
        </View>
        {loading ? (
          <ActivityIndicator color="#2563eb" />
        ) : loadError ? (
          <Text style={styles.error}>Pi offline — could not load schedules.</Text>
        ) : (
          <FlatList
            data={schedules}
            keyExtractor={(s) => String(s.id)}
            renderItem={renderSchedule}
            ListEmptyComponent={<Text style={styles.empty}>No schedules configured.</Text>}
          />
        )}
      </View>

      {/* Create Schedule Modal */}
      <Modal visible={modalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modal}>
            <Text style={styles.modalTitle}>New Schedule</Text>
            <TextInput
              style={styles.input}
              placeholder="Name"
              value={newName}
              onChangeText={setNewName}
            />
            <TextInput
              style={styles.input}
              placeholder="Interval (seconds, min 5)"
              value={newInterval}
              onChangeText={setNewInterval}
              keyboardType="number-pad"
            />
            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setModalVisible(false)}>
                <Text style={styles.cancelText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.createBtn} onPress={handleCreate}>
                <Text style={styles.createText}>Create</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f0f4f8' },
  section: { backgroundColor: '#fff', margin: 12, borderRadius: 12, padding: 16, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 6, elevation: 2 },
  sectionTitle: { fontSize: 15, fontWeight: '700', color: '#1e3a5f', marginBottom: 8 },
  adapterRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 },
  adapterName: { fontSize: 13 },
  adapterIp: { fontSize: 13, color: '#6b7280' },
  offline: { fontSize: 13, color: '#9ca3af' },
  card: { backgroundColor: '#f8fafc', borderRadius: 8, padding: 12, marginBottom: 8, borderWidth: 1, borderColor: '#e5e7eb' },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  schedName: { fontSize: 14, fontWeight: '600', color: '#111827' },
  schedMeta: { fontSize: 12, color: '#6b7280', marginTop: 2 },
  deleteBtn: { color: '#dc2626', fontSize: 12, marginTop: 6 },
  addBtn: { backgroundColor: '#2563eb', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 6 },
  addBtnText: { color: '#fff', fontWeight: '600', fontSize: 13 },
  empty: { textAlign: 'center', color: '#9ca3af', paddingVertical: 16 },
  error: { textAlign: 'center', color: '#dc2626', paddingVertical: 16 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'center', alignItems: 'center' },
  modal: { backgroundColor: '#fff', borderRadius: 16, padding: 24, width: '85%' },
  modalTitle: { fontSize: 16, fontWeight: '700', color: '#1e3a5f', marginBottom: 16 },
  input: { borderWidth: 1, borderColor: '#d1d5db', borderRadius: 8, padding: 10, fontSize: 14, marginBottom: 12 },
  modalActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 12 },
  cancelBtn: { paddingHorizontal: 16, paddingVertical: 8 },
  cancelText: { color: '#6b7280', fontWeight: '600' },
  createBtn: { backgroundColor: '#2563eb', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8 },
  createText: { color: '#fff', fontWeight: '600' },
});
