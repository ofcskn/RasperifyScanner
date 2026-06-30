import React, { useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, Linking, ActivityIndicator,
} from 'react-native';
import { fetchHealth } from '../../services/api';

interface AdapterRow {
  name: string;
  interface: string;
  up: boolean;
  ip: string | null;
}

interface NetworkHealth {
  active_adapter: string | null;
  adapters: AdapterRow[];
}

type Section = {
  id: string;
  title: string;
  icon: string;
  content: React.ReactNode;
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f0f4f8' },

  header: { backgroundColor: '#1e3a5f', padding: 20, paddingTop: 24 },
  headerTitle: { fontSize: 22, fontWeight: '800', color: '#fff', marginBottom: 6 },
  headerSub: { fontSize: 13, color: '#93c5fd', lineHeight: 18 },

  section: { backgroundColor: '#fff', marginHorizontal: 12, marginTop: 10, borderRadius: 12, overflow: 'hidden', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 6, elevation: 2 },
  sectionHeader: { flexDirection: 'row', alignItems: 'center', padding: 14 },
  sectionIcon: { fontSize: 20, marginRight: 10 },
  sectionTitle: { flex: 1, fontSize: 15, fontWeight: '700', color: '#1e3a5f' },
  chevron: { fontSize: 12, color: '#6b7280' },
  sectionBody: { padding: 16, paddingTop: 0, borderTopWidth: 1, borderTopColor: '#f3f4f6' },

  body: { fontSize: 13, color: '#374151', lineHeight: 20, marginBottom: 10 },
  bold: { fontWeight: '700' },
  mono: { fontFamily: 'monospace', fontSize: 12, color: '#1e3a5f' },
  subheading: { fontSize: 13, fontWeight: '700', color: '#1e3a5f', marginTop: 14, marginBottom: 6 },

  codeBlock: { backgroundColor: '#1e293b', borderRadius: 8, padding: 12, marginVertical: 8 },
  codeText: { fontFamily: 'monospace', fontSize: 12, color: '#e2e8f0', lineHeight: 18 },

  infoBox: { borderLeftWidth: 4, borderRadius: 6, padding: 10, marginVertical: 8 },
  infoText: { fontSize: 12, color: '#374151', lineHeight: 18 },

  step: { flexDirection: 'row', marginVertical: 8, gap: 10 },
  stepBadge: { width: 24, height: 24, borderRadius: 12, backgroundColor: '#2563eb', alignItems: 'center', justifyContent: 'center', marginTop: 2 },
  stepNum: { color: '#fff', fontSize: 12, fontWeight: '700' },
  stepTitle: { fontSize: 13, fontWeight: '700', color: '#111827', marginBottom: 4 },

  adapterCard: { backgroundColor: '#f8fafc', borderRadius: 8, padding: 12, marginVertical: 6, borderWidth: 1, borderColor: '#e5e7eb' },
  adapterCardTitle: { fontSize: 14, fontWeight: '700', color: '#111827', marginBottom: 4 },
  adapterCardDesc: { fontSize: 12, color: '#6b7280', lineHeight: 18, marginBottom: 6 },
  adapterCardFix: { fontSize: 12, color: '#059669', lineHeight: 18 },

  table: { borderWidth: 1, borderColor: '#e5e7eb', borderRadius: 8, overflow: 'hidden', marginVertical: 8 },
  tableRow: { flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: '#e5e7eb' },
  tableCell: { flex: 1, padding: 8, fontSize: 12, color: '#374151' },
  tableHeader: { fontWeight: '700', backgroundColor: '#f3f4f6', color: '#111827' },

  troubleRow: { paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#f3f4f6' },
  troubleSymptom: { fontSize: 12, fontWeight: '600', color: '#dc2626', marginBottom: 2 },
  troubleFix: { fontSize: 12, color: '#374151', lineHeight: 18 },

  docLink: { marginTop: 16, backgroundColor: '#eff6ff', borderRadius: 8, padding: 12, alignItems: 'center', borderWidth: 1, borderColor: '#bfdbfe' },
  docLinkText: { fontSize: 13, color: '#2563eb', fontWeight: '600' },

  liveStatusLoading: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 10 },
  liveStatusLoadingText: { fontSize: 12, color: '#6b7280' },
  liveAdapterRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: '#f3f4f6' },
  liveDot: { width: 9, height: 9, borderRadius: 5, marginRight: 10 },
  liveAdapterName: { flex: 1, fontSize: 13, fontWeight: '600', color: '#111827' },
  liveAdapterState: { fontSize: 12, fontFamily: 'monospace', color: '#374151' },
});

function CodeBlock({ children }: { children: string }) {
  return (
    <View style={styles.codeBlock}>
      <Text style={styles.codeText}>{children}</Text>
    </View>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <View style={styles.step}>
      <View style={styles.stepBadge}>
        <Text style={styles.stepNum}>{n}</Text>
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.stepTitle}>{title}</Text>
        {children}
      </View>
    </View>
  );
}

function InfoBox({ type, children }: { type: 'tip' | 'warn' | 'error'; children: React.ReactNode }) {
  const colors = { tip: '#d1fae5', warn: '#fef3c7', error: '#fee2e2' };
  const borders = { tip: '#059669', warn: '#d97706', error: '#dc2626' };
  const icons = { tip: 'ℹ️', warn: '⚠️', error: '❌' };
  return (
    <View style={[styles.infoBox, { backgroundColor: colors[type], borderLeftColor: borders[type] }]}>
      <Text style={styles.infoText}>{icons[type]}  {children}</Text>
    </View>
  );
}

const ADAPTER_LABELS: Record<string, string> = {
  usb: 'USB (usb0)',
  ethernet: 'Ethernet (eth0)',
  wifi: 'WiFi (wlan0)',
};

/**
 * Live network status — reads the actual adapter state from /health instead of
 * asserting a fixed assumption about which interface "should" be primary. The
 * backend's active_adapter is whichever interface is genuinely up (priority:
 * USB → Ethernet → WiFi), so this reflects reality whether the Pi is on
 * Ethernet, WiFi, or USB-C.
 */
function LiveAdapterStatus() {
  const [health, setHealth] = useState<NetworkHealth | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const data = (await fetchHealth()) as NetworkHealth;
        if (active) { setHealth(data); setError(false); }
      } catch {
        if (active) setError(true);
      }
    };
    load();
    const id = setInterval(load, 10000);
    return () => { active = false; clearInterval(id); };
  }, []);

  if (error) {
    return (
      <InfoBox type="error">
        Could not reach the backend to read network status. Confirm the backend is running and the app's API URL points at the Pi.
      </InfoBox>
    );
  }

  if (!health) {
    return (
      <View style={styles.liveStatusLoading}>
        <ActivityIndicator color="#2563eb" />
        <Text style={styles.liveStatusLoadingText}>Reading live adapter status…</Text>
      </View>
    );
  }

  const active = health.active_adapter;
  const activeRow = health.adapters?.find((a) => a.name === active) ?? null;

  return (
    <View>
      {active && activeRow ? (
        <InfoBox type="tip">
          You are connected via {ADAPTER_LABELS[active] ?? active} at {activeRow.ip}. This is the active adapter the backend is reachable on right now.
        </InfoBox>
      ) : (
        <InfoBox type="warn">
          No active adapter — none of the interfaces below are up with an IP. Connect Ethernet, WiFi, or USB-C gadget mode using the steps in the sections below.
        </InfoBox>
      )}

      {(health.adapters ?? []).map((a) => {
        const isActive = a.name === active;
        const stateColor = a.up && a.ip ? '#059669' : '#9ca3af';
        return (
          <View key={a.interface} style={styles.liveAdapterRow}>
            <View style={[styles.liveDot, { backgroundColor: stateColor }]} />
            <Text style={styles.liveAdapterName}>
              {ADAPTER_LABELS[a.name] ?? a.name}
              {isActive ? '  ·  active' : ''}
            </Text>
            <Text style={styles.liveAdapterState}>
              {a.up && a.ip ? a.ip : a.up ? 'up (no IP)' : 'down'}
            </Text>
          </View>
        );
      })}
    </View>
  );
}

function AdapterCard({ name, icon, description, fix }: { name: string; icon: string; description: string; fix: string }) {
  return (
    <View style={styles.adapterCard}>
      <Text style={styles.adapterCardTitle}>{icon} {name}</Text>
      <Text style={styles.adapterCardDesc}>{description}</Text>
      <Text style={styles.adapterCardFix}>{fix}</Text>
    </View>
  );
}

const sections: Section[] = [
  {
    id: 'adapters',
    title: 'Why No Active Adapter?',
    icon: '🔌',
    content: (
      <View>
        <Text style={styles.body}>
          The dashboard shows <Text style={styles.bold}>active_adapter: null</Text> when none of the three network interfaces on the Pi are up. The Pi has three ways to connect:
        </Text>

        <AdapterCard
          name="USB (usb0)"
          icon="🔵"
          description="Pi connected to your Mac/PC via USB-C cable in gadget mode. This is the primary connection for development — fastest and most reliable."
          fix="Fix: Install rpi-usb-gadget on the Pi, run 'sudo rpi-usb-gadget on', reboot, and plug in the USB-C data cable."
        />
        <AdapterCard
          name="Ethernet (eth0)"
          icon="🟡"
          description="Pi connected via a physical Ethernet cable to your router or directly to your computer."
          fix="Fix: Plug an Ethernet cable into the Pi's RJ-45 port and your router. The Pi gets an IP from DHCP automatically."
        />
        <AdapterCard
          name="WiFi (wlan0)"
          icon="🟢"
          description="Pi connected to your WiFi network. Requires WiFi credentials to have been set during SD card flashing in Raspberry Pi Imager."
          fix="Fix: Re-flash the SD card with correct WiFi credentials in Imager's Advanced Options, or run 'sudo raspi-config' → System Options → Wireless LAN on the Pi."
        />

        <Text style={styles.subheading}>Live status</Text>
        <LiveAdapterStatus />

        <Text style={[styles.body, { marginTop: 12 }]}>
          The active adapter is whichever interface is up first in priority order (<Text style={styles.bold}>USB → Ethernet → WiFi</Text>). Setting up USB-C gadget mode (Section below) adds the fastest direct-cable link, but Ethernet and WiFi work on their own.
        </Text>
      </View>
    ),
  },
  {
    id: 'usb',
    title: 'Set Up USB-C Gadget Mode',
    icon: '🔧',
    content: (
      <View>
        <Text style={styles.body}>
          USB-C gadget mode lets the Pi appear as a USB Ethernet adapter on your Mac. No router needed — plug the cable in and the Pi is reachable at a fixed IP.
        </Text>

        <Text style={styles.subheading}>Step 1 — Install on the Pi</Text>
        <Text style={styles.body}>SSH into the Pi and run:</Text>
        <CodeBlock>{'sudo apt update\nsudo apt install rpi-usb-gadget\nsudo rpi-usb-gadget on'}</CodeBlock>

        <InfoBox type="tip">
          Plug the USB-C data cable into your Mac before rebooting, so the interface appears immediately on boot.
        </InfoBox>

        <Step n={1} title="Reboot the Pi">
          <CodeBlock>{'sudo reboot'}</CodeBlock>
        </Step>

        <Step n={2} title="Verify on your Mac">
          <Text style={styles.body}>Open Terminal on your Mac and check:</Text>
          <CodeBlock>{'ifconfig | grep -A4 "10.12.194"'}</CodeBlock>
          <Text style={styles.body}>You should see <Text style={styles.mono}>inet 10.12.194.2</Text>. The Pi is always at <Text style={styles.mono}>10.12.194.1</Text>.</Text>
        </Step>

        <Step n={3} title="SSH via USB-C (no WiFi needed)">
          <CodeBlock>{'ssh pi@10.12.194.1'}</CodeBlock>
        </Step>

        <Text style={styles.subheading}>Two modes — automatic switching</Text>
        <View style={styles.table}>
          <View style={styles.tableRow}>
            <Text style={[styles.tableCell, styles.tableHeader]}>Mode</Text>
            <Text style={[styles.tableCell, styles.tableHeader]}>Pi IP</Text>
            <Text style={[styles.tableCell, styles.tableHeader]}>When</Text>
          </View>
          <View style={styles.tableRow}>
            <Text style={styles.tableCell}>SHARED</Text>
            <Text style={styles.tableCell}>10.12.194.1</Text>
            <Text style={styles.tableCell}>No ICS on host</Text>
          </View>
          <View style={styles.tableRow}>
            <Text style={styles.tableCell}>CLIENT</Text>
            <Text style={styles.tableCell}>raspberrypi.local</Text>
            <Text style={styles.tableCell}>ICS enabled on host</Text>
          </View>
        </View>

        <InfoBox type="warn">
          Use a data-capable USB-C cable. Many USB-C cables are power-only and look identical. If the interface never appears on your Mac, swap the cable first.
        </InfoBox>
      </View>
    ),
  },
  {
    id: 'camera',
    title: 'Connect the Camera',
    icon: '📷',
    content: (
      <View>
        <Text style={styles.body}>
          The Pi Camera Module connects via a CSI ribbon cable. The app shows <Text style={styles.mono}>camera_connected: false</Text> if the cable is not seated correctly.
        </Text>

        <InfoBox type="tip">
          On Raspberry Pi OS Bookworm, the camera is enabled automatically via camera_auto_detect=1 — there is no "Camera" option in raspi-config Interface Options. No extra configuration needed.
        </InfoBox>

        <Text style={styles.subheading}>Physical connection</Text>
        <InfoBox type="error">
          Power off the Pi before touching the ribbon cable. Hot-plugging can damage the camera.
        </InfoBox>
        <CodeBlock>{'sudo shutdown -h now\n# Wait for green LED to stop, then unplug power'}</CodeBlock>

        <Step n={1} title="Find the CSI port">
          <Text style={styles.body}>The narrow black connector between the two HDMI ports and the USB-A ports, labelled "CAMERA".</Text>
        </Step>
        <Step n={2} title="Open the locking tab">
          <Text style={styles.body}>Lift the brown plastic locking tab straight up ~2 mm. It does not detach.</Text>
        </Step>
        <Step n={3} title="Insert the ribbon cable">
          <Text style={styles.body}>Blue strip faces toward the USB-A ports. Metal contacts face the HDMI side. Slide in fully, then press the locking tab flat.</Text>
        </Step>
        <Step n={4} title="Connect camera end">
          <Text style={styles.body}>Same process on the camera module: lift tab, blue strip toward the lens, press tab down.</Text>
        </Step>
        <Step n={5} title="Power on and verify">
          <Text style={styles.body}>Reconnect power, SSH in, then check:</Text>
          <CodeBlock>{'vcgencmd get_camera\n# Expected: supported=1 detected=1\n\nlibcamera-jpeg -o /tmp/test.jpg && echo "Camera OK"'}</CodeBlock>
        </Step>

        <Text style={styles.subheading}>If detected=0 — diagnose with I2C</Text>
        <Text style={styles.body}>This checks whether the camera module is electrically present on the bus:</Text>
        <CodeBlock>{'sudo apt install i2c-tools\ni2cdetect -y 0\n# Camera v2 (IMX219) appears at 0x10\n# Camera v3 (IMX708) appears at 0x1a\n# Empty grid = cable not seated or wrong end'}</CodeBlock>

        <InfoBox type="tip">
          If i2cdetect shows an empty grid: power off, reseat both ribbon cable ends pressing locking tabs firmly closed, power on again. The blue strip orientation must be correct on both ends.
        </InfoBox>
      </View>
    ),
  },
  {
    id: 'deploy',
    title: 'Deploy the Backend',
    icon: '🚀',
    content: (
      <View>
        <Text style={styles.body}>
          Once SSH access is working, deploy the RasperifyScanner backend on the Pi.
        </Text>

        <Step n={1} title="Clone the repo">
          <CodeBlock>{'cd ~\ngit clone https://github.com/<your-username>/RasperifyScanner.git\ncd RasperifyScanner/backend'}</CodeBlock>
        </Step>
        <Step n={2} title="Create virtual environment">
          <CodeBlock>{'python3 -m venv .venv\nsource .venv/bin/activate'}</CodeBlock>
        </Step>
        <Step n={3} title="Install dependencies">
          <CodeBlock>{'pip install --upgrade pip\npip install -r requirements.txt'}</CodeBlock>
          <InfoBox type="tip">Takes 5–15 minutes on Pi hardware — this is normal.</InfoBox>
        </Step>
        <Step n={4} title="Configure environment variables">
          <CodeBlock>{'cp .env.example .env\nnano .env'}</CodeBlock>
          <Text style={styles.body}>Set <Text style={styles.mono}>GEMINI_API_KEY</Text> (required), <Text style={styles.mono}>SECRET_KEY</Text> (random hex), and <Text style={styles.mono}>CAMERA_MOCK=false</Text>.</Text>
        </Step>
        <Step n={5} title="Run the backend">
          <CodeBlock>{'uvicorn main:app --host 0.0.0.0 --port 8000'}</CodeBlock>
          <Text style={styles.body}>Test from your Mac:</Text>
          <CodeBlock>{'curl http://10.12.194.1:8000/api/v1/health'}</CodeBlock>
        </Step>
        <Step n={6} title="Enable auto-start on boot">
          <Text style={styles.body}>Follow Section 11 in the full PI_SETUP.md to install the systemd service so the backend starts automatically after every reboot.</Text>
        </Step>
      </View>
    ),
  },
  {
    id: 'troubleshoot',
    title: 'Troubleshooting',
    icon: '🛠️',
    content: (
      <View>
        <Text style={styles.subheading}>Pi not found on network</Text>
        <View style={styles.troubleRow}>
          <Text style={styles.troubleSymptom}>Solid red LED only</Text>
          <Text style={styles.troubleFix}>SD card write failed — reflash with Raspberry Pi Imager</Text>
        </View>
        <View style={styles.troubleRow}>
          <Text style={styles.troubleSymptom}>Red + green LED but ping fails</Text>
          <Text style={styles.troubleFix}>Normal — Pi OS blocks ICMP. Use SSH directly: ssh pi@&lt;ip&gt;</Text>
        </View>
        <View style={styles.troubleRow}>
          <Text style={styles.troubleSymptom}>Not in nmap results</Text>
          <Text style={styles.troubleFix}>Wrong WiFi credentials in Imager. Reflash with correct SSID/password.</Text>
        </View>

        <Text style={styles.subheading}>USB-C adapter not appearing on Mac</Text>
        <View style={styles.troubleRow}>
          <Text style={styles.troubleSymptom}>No USB Ethernet in System Settings</Text>
          <Text style={styles.troubleFix}>1) Swap cable (power-only cables look identical to data cables) 2) Verify rpi-usb-gadget was installed and Pi was rebooted</Text>
        </View>
        <View style={styles.troubleRow}>
          <Text style={styles.troubleSymptom}>10.12.194.1 unreachable</Text>
          <Text style={styles.troubleFix}>Disable VPN on your Mac — VPNs intercept the local routing table and block the USB link</Text>
        </View>

        <Text style={styles.subheading}>Camera not detected</Text>
        <View style={styles.troubleRow}>
          <Text style={styles.troubleSymptom}>camera_connected: false</Text>
          <Text style={styles.troubleFix}>Run: vcgencmd get_camera. If detected=0, power off and reseat both ribbon cable ends.</Text>
        </View>
        <View style={styles.troubleRow}>
          <Text style={styles.troubleSymptom}>libcamera-hello error</Text>
          <Text style={styles.troubleFix}>Run sudo raspi-config → Interface Options → Camera → Enable → Reboot</Text>
        </View>

        <Text style={styles.subheading}>Backend not starting</Text>
        <CodeBlock>{'sudo journalctl -u rasperify -n 50 --no-pager'}</CodeBlock>
        <View style={styles.troubleRow}>
          <Text style={styles.troubleSymptom}>ModuleNotFoundError: picamera2</Text>
          <Text style={styles.troubleFix}>sudo apt install python3-picamera2</Text>
        </View>
        <View style={styles.troubleRow}>
          <Text style={styles.troubleSymptom}>Address already in use</Text>
          <Text style={styles.troubleFix}>sudo fuser -k 8000/tcp && sudo systemctl restart rasperify</Text>
        </View>
        <View style={styles.troubleRow}>
          <Text style={styles.troubleSymptom}>GEMINI_API_KEY not set</Text>
          <Text style={styles.troubleFix}>Edit ~/RasperifyScanner/backend/.env and add the key</Text>
        </View>
      </View>
    ),
  },
  {
    id: 'ipref',
    title: 'IP Address Reference',
    icon: '🌐',
    content: (
      <View>
        <Text style={styles.body}>Quick reference for all connection modes:</Text>

        <View style={styles.table}>
          <View style={styles.tableRow}>
            <Text style={[styles.tableCell, styles.tableHeader]}>Mode</Text>
            <Text style={[styles.tableCell, styles.tableHeader]}>Pi IP</Text>
          </View>
          <View style={styles.tableRow}>
            <Text style={styles.tableCell}>USB-C SHARED (no ICS)</Text>
            <Text style={[styles.tableCell, styles.mono]}>10.12.194.1</Text>
          </View>
          <View style={styles.tableRow}>
            <Text style={styles.tableCell}>USB-C CLIENT (macOS ICS)</Text>
            <Text style={[styles.tableCell, styles.mono]}>192.168.2.x</Text>
          </View>
          <View style={styles.tableRow}>
            <Text style={styles.tableCell}>USB-C CLIENT (Windows ICS)</Text>
            <Text style={[styles.tableCell, styles.mono]}>192.168.137.x</Text>
          </View>
          <View style={styles.tableRow}>
            <Text style={styles.tableCell}>USB-C CLIENT (Linux ICS)</Text>
            <Text style={[styles.tableCell, styles.mono]}>10.42.0.x</Text>
          </View>
          <View style={styles.tableRow}>
            <Text style={styles.tableCell}>WiFi / Ethernet</Text>
            <Text style={[styles.tableCell, styles.mono]}>raspberrypi.local</Text>
          </View>
        </View>

        <Text style={styles.subheading}>Backend URLs</Text>
        <CodeBlock>{'# USB-C SHARED\nhttp://10.12.194.1:8000/api/v1/health\n\n# WiFi / USB CLIENT\nhttp://raspberrypi.local:8000/api/v1/health'}</CodeBlock>

        <TouchableOpacity
          style={styles.docLink}
          onPress={() => Linking.openURL('https://github.com/raspberrypi/rpi-usb-gadget')}
        >
          <Text style={styles.docLinkText}>📖 rpi-usb-gadget official docs</Text>
        </TouchableOpacity>
      </View>
    ),
  },
];

export default function HelpScreen() {
  const [expanded, setExpanded] = useState<string | null>('adapters');

  const toggle = (id: string) => setExpanded((prev) => (prev === id ? null : id));

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 40 }}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Setup Guide</Text>
        <Text style={styles.headerSub}>
          Step-by-step instructions for connecting your Raspberry Pi 4 and getting the scanner running.
        </Text>
      </View>

      {sections.map((s) => (
        <View key={s.id} style={styles.section}>
          <TouchableOpacity style={styles.sectionHeader} onPress={() => toggle(s.id)} activeOpacity={0.7}>
            <Text style={styles.sectionIcon}>{s.icon}</Text>
            <Text style={styles.sectionTitle}>{s.title}</Text>
            <Text style={styles.chevron}>{expanded === s.id ? '▲' : '▼'}</Text>
          </TouchableOpacity>
          {expanded === s.id && (
            <View style={styles.sectionBody}>{s.content}</View>
          )}
        </View>
      ))}
    </ScrollView>
  );
}
