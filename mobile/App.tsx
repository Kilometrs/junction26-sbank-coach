// Money coach: phone UI for the S-Bank "Personal Economic Trainer", built from the Claude Design mockup.
import { Inter_400Regular, Inter_500Medium, Inter_600SemiBold, Inter_700Bold, useFonts } from '@expo-google-fonts/inter';
import { StatusBar } from 'expo-status-bar';
import { ReactNode, useCallback, useEffect, useState } from 'react';
import { Modal, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

import { Customer, LifeStages, Profile, api } from './src/api';
import { Check } from './src/components/Icons';
import { withoutMarkers } from './src/components/Visuals';
import { Button } from './src/components/ui';
import { ChatScreen, Message } from './src/screens/ChatScreen';
import { CustomersScreen } from './src/screens/CustomersScreen';
import { ProfileScreen } from './src/screens/ProfileScreen';
import { colors, font, PHONE_MAX_WIDTH } from './src/theme';

type Screen = 'customers' | 'chat' | 'profile';

export default function App() {
  const [fontsLoaded] = useFonts({ Inter_400Regular, Inter_500Medium, Inter_600SemiBold, Inter_700Bold });

  const [screen, setScreen] = useState<Screen>('customers');
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [lifeStages, setLifeStages] = useState<LifeStages | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [userStage, setUserStage] = useState<string | null>(null); // confirmed by the user
  const [detection, setDetection] = useState(true);
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  const [picker, setPicker] = useState(false);
  const [sentSheet, setSentSheet] = useState(false);

  // What we send as life_stage: the user's choice, or nothing (engine guesses), or a neutral default when detection is off.
  const stage = userStage ?? (detection ? null : 'stable');
  const stageSource = userStage ? 'user' : detection ? 'guess' : 'default';

  useEffect(() => {
    api.lifeStages().then(setLifeStages).catch(() => {});
  }, []);

  useEffect(() => {
    if (!customer) return;
    let live = true;
    api.profile(customer.id, stage).then((p) => live && setProfile(p)).catch(() => {});
    return () => {
      live = false;
    };
  }, [customer, stage]);

  const reset = () => {
    setMessages([]);
    setUserStage(null);
    setDetection(true);
    setProfile(null);
  };

  const pickCustomer = (c: Customer) => {
    reset();
    setCustomer(c);
    setScreen('chat');
  };

  const send = useCallback(
    async (text: string) => {
      if (!customer) return;
      const history: Message[] = [...messages.filter((m) => !m.failed), { role: 'user', content: text, time: new Date() }];
      setMessages(history);
      setBusy(true);
      try {
        const out = await api.chat(customer.id, history.map(({ role, content }) => ({ role, content: withoutMarkers(content) })), stage);
        if (out.error) {
          // The model dropped out partway (e.g. llm_unavailable). The backend still returns the tool results it
          // gathered, but without the coach's explanation they'd be unexplained numbers: show only the message,
          // and keep this exchange out of the history sent next time.
          history[history.length - 1].failed = true;
          setMessages([...history, { role: 'assistant', content: out.reply, time: new Date(), failed: true }]);
          return;
        }
        setMessages([...history, { role: 'assistant', content: out.reply, charts: out.charts, options: out.options, time: new Date() }]);
        if (out.life_stage && out.life_stage !== stage) setUserStage(out.life_stage);
      } catch {
        history[history.length - 1].failed = true;
        setMessages([
          ...history,
          { role: 'assistant', content: "I couldn't reach the coach server. Check that it's running and try again.", time: new Date(), failed: true },
        ]);
      } finally {
        setBusy(false);
      }
    },
    [customer, messages, stage],
  );

  if (!fontsLoaded) return null;

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <View style={s.backdrop}>
        <SafeAreaView edges={['top']} style={s.phone}>
          {screen === 'customers' || !customer ? (
            <CustomersScreen onPick={pickCustomer} />
          ) : screen === 'chat' ? (
            <ChatScreen
              profile={profile}
              lifeStages={lifeStages}
              stageSource={stageSource}
              messages={messages}
              busy={busy}
              onSend={send}
              onBack={() => setScreen('customers')}
              onOpenProfile={() => setScreen('profile')}
              onEditStage={() => setPicker(true)}
            />
          ) : (
            <ProfileScreen
              profile={profile}
              lifeStages={lifeStages}
              stageSource={stageSource}
              detection={detection}
              onBack={() => setScreen('chat')}
              onSetStage={setUserStage}
              onEditStage={() => setPicker(true)}
              onToggleDetection={() => setDetection((d) => !d)}
              onShowSent={() => setSentSheet(true)}
              onForget={() => {
                reset();
                setScreen('chat');
              }}
            />
          )}
        </SafeAreaView>
      </View>

      <Sheet visible={picker} title="What's your situation?" onClose={() => setPicker(false)}>
        <Text style={[font(13, 400, colors.muted), { lineHeight: 19 }]}>
          Your situation sets how big a safety net the coach aims for.
        </Text>
        <View style={s.options}>
          {lifeStages &&
            Object.entries(lifeStages).map(([key, v], i, all) => {
              const selected = profile?.life_stage === key && stageSource === 'user';
              return (
                <Pressable
                  key={key}
                  accessibilityRole="radio"
                  accessibilityState={{ selected }}
                  onPress={() => {
                    setUserStage(key);
                    setPicker(false);
                  }}
                  style={({ pressed }) => [s.option, i < all.length - 1 && s.optionLine, pressed && { opacity: 0.6 }]}
                >
                  <View style={{ flex: 1, gap: 2 }}>
                    <Text style={font(15, 500)}>{v.label}</Text>
                    <Text style={font(12, 400, colors.muted)}>Safety-net goal {v.target_months} months</Text>
                  </View>
                  {selected ? <Check size={18} /> : null}
                </Pressable>
              );
            })}
        </View>
      </Sheet>

      <Sheet visible={sentSheet} title="What was sent to the AI" onClose={() => setSentSheet(false)}>
        <Text style={[font(13, 400, colors.muted), { lineHeight: 19 }]}>
          This summary is all the language model gets about you, plus the results of the calculations it asks for.
        </Text>
        <View style={s.sent}>
          <Text style={[font(13), { lineHeight: 20 }]}>{profile?.persona_text ?? 'Loading…'}</Text>
        </View>
      </Sheet>
    </SafeAreaProvider>
  );
}

function Sheet({ visible, title, onClose, children }: { visible: boolean; title: string; onClose: () => void; children: ReactNode }) {
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={s.scrim}>
        <Pressable accessibilityLabel="Close" style={StyleSheet.absoluteFill} onPress={onClose} />
        <View style={s.sheet}>
          <Text style={font(17, 600, colors.heading)}>{title}</Text>
          <ScrollView contentContainerStyle={{ gap: 12 }}>{children}</ScrollView>
          <Button title="Close" kind="outline" onPress={onClose} />
        </View>
      </View>
    </Modal>
  );
}

const s = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: Platform.OS === 'web' ? colors.webBackdrop : colors.mint },
  phone: { flex: 1, width: '100%', maxWidth: PHONE_MAX_WIDTH, alignSelf: 'center', backgroundColor: colors.mint },
  scrim: { flex: 1, justifyContent: 'flex-end', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.35)' },
  sheet: {
    width: '100%',
    maxWidth: PHONE_MAX_WIDTH,
    maxHeight: '85%',
    backgroundColor: colors.white,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 20,
    paddingBottom: 32,
    gap: 14,
  },
  options: { borderWidth: 1, borderColor: colors.line, borderRadius: 16 },
  option: { flexDirection: 'row', alignItems: 'center', gap: 12, minHeight: 56, paddingHorizontal: 16, paddingVertical: 8 },
  optionLine: { borderBottomWidth: 1, borderBottomColor: colors.line },
  sent: { backgroundColor: colors.mint, borderRadius: 12, padding: 14 },
});
