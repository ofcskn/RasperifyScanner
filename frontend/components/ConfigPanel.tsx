import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, Switch, TextInput, ActivityIndicator, TouchableOpacity } from 'react-native';
import { fetchConfig, updateConfig, ScannerConfig } from '../services/api';
import { Card } from './Card';
import { Colors, Spacing } from '../constants/theme';

/** Live runtime configuration controls backed by GET/PATCH /config. */
export default function ConfigPanel() {
  const [cfg, setCfg] = useState<ScannerConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        setCfg(await fetchConfig());
      } catch {
        setError('Could not load configuration.');
      }
    })();
  }, []);

  const save = async (patch: Partial<ScannerConfig>) => {
    setSaving(true);
    setError(null);
    const prev = cfg;
    setCfg((c) => (c ? { ...c, ...patch } : c)); // optimistic
    try {
      setCfg(await updateConfig(patch));
    } catch {
      setError('Failed to save. Reverted.');
      setCfg(prev);
    } finally {
      setSaving(false);
    }
  };

  if (error && !cfg) return <Card><Text style={styles.error}>{error}</Text></Card>;
  if (!cfg) {
    return <Card><ActivityIndicator color={Colors.primary} /></Card>;
  }

  const step = (key: keyof ScannerConfig, delta: number, min: number, max: number, decimals = 2) => {
    const next = Math.min(max, Math.max(min, Number(((cfg[key] as number) + delta).toFixed(decimals))));
    save({ [key]: next } as Partial<ScannerConfig>);
  };

  return (
    <Card style={styles.card}>
      <Text style={styles.title}>Scanner Configuration {saving && <Text style={styles.saving}>· saving…</Text>}</Text>
      {error && <Text style={styles.error}>{error}</Text>}

      <Row label="Camera rotation (fix upside-down mount)">
        <TouchableOpacity
          style={[styles.rotateBtn, saving && styles.rotateBtnDisabled]}
          disabled={saving}
          onPress={() => save({ camera_rotation: (((cfg.camera_rotation ?? 0) + 90) % 360) })}
        >
          <Text style={styles.rotateBtnText}>{cfg.camera_rotation ?? 0}°</Text>
        </TouchableOpacity>
      </Row>

      <Row label="Detection enabled">
        <Switch value={cfg.detection_enabled} onValueChange={(v) => save({ detection_enabled: v })} />
      </Row>

      <Stepper
        label="Confidence threshold"
        value={cfg.detection_conf_threshold.toFixed(2)}
        onDec={() => step('detection_conf_threshold', -0.05, 0, 1)}
        onInc={() => step('detection_conf_threshold', 0.05, 0, 1)}
      />

      <Stepper
        label="Detection interval (s)"
        value={(cfg.detection_interval_seconds ?? 2).toFixed(1)}
        onDec={() => step('detection_interval_seconds', -0.5, 0.5, 30, 1)}
        onInc={() => step('detection_interval_seconds', 0.5, 0.5, 30, 1)}
      />

      <Stepper
        label="Analysis interval (s)"
        value={String(cfg.analysis_default_interval_seconds)}
        onDec={() => step('analysis_default_interval_seconds', -5, 5, 3600, 0)}
        onInc={() => step('analysis_default_interval_seconds', 5, 5, 3600, 0)}
      />

      <Stepper
        label="Person alert threshold"
        value={String(cfg.counting_person_alert_threshold)}
        onDec={() => step('counting_person_alert_threshold', -1, 0, 999, 0)}
        onInc={() => step('counting_person_alert_threshold', 1, 0, 999, 0)}
      />

      <Row label="Ollama model">
        <TextInput
          style={styles.input}
          defaultValue={cfg.ollama_model}
          onSubmitEditing={(e) => save({ ollama_model: e.nativeEvent.text.trim() })}
          autoCapitalize="none"
          returnKeyType="done"
        />
      </Row>

      <Row label="Store frames">
        <Switch value={cfg.store_frames} onValueChange={(v) => save({ store_frames: v })} />
      </Row>

      <Row label="Allow cloud AI (off = fully local)">
        <Switch value={cfg.allow_cloud} onValueChange={(v) => save({ allow_cloud: v })} />
      </Row>
    </Card>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      {children}
    </View>
  );
}

function Stepper({ label, value, onDec, onInc }: { label: string; value: string; onDec: () => void; onInc: () => void }) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.stepper}>
        <TouchableOpacity style={styles.stepBtn} onPress={onDec}><Text style={styles.stepBtnText}>−</Text></TouchableOpacity>
        <Text style={styles.stepValue}>{value}</Text>
        <TouchableOpacity style={styles.stepBtn} onPress={onInc}><Text style={styles.stepBtnText}>+</Text></TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { gap: Spacing.sm },
  title: { fontSize: 16, fontWeight: '700', color: Colors.text, marginBottom: 4 },
  saving: { fontSize: 12, color: Colors.textMuted, fontWeight: '400' },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 6 },
  label: { fontSize: 14, color: Colors.text, flex: 1, paddingRight: 8 },
  input: {
    borderWidth: 1, borderColor: Colors.border, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6,
    minWidth: 130, color: Colors.text,
  },
  stepper: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  stepBtn: {
    width: 32, height: 32, borderRadius: 8, backgroundColor: Colors.primaryLight,
    alignItems: 'center', justifyContent: 'center',
  },
  stepBtnText: { fontSize: 18, fontWeight: '800', color: Colors.primary },
  stepValue: { fontSize: 15, fontWeight: '700', color: Colors.text, minWidth: 48, textAlign: 'center' },
  rotateBtn: {
    paddingHorizontal: 16, height: 32, borderRadius: 8, backgroundColor: Colors.primaryLight,
    alignItems: 'center', justifyContent: 'center', minWidth: 64,
  },
  rotateBtnDisabled: { opacity: 0.5 },
  rotateBtnText: { fontSize: 15, fontWeight: '800', color: Colors.primary },
  error: { color: Colors.danger, fontSize: 13 },
});
