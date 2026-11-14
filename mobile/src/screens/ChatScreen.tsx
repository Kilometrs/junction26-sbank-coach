// "Chat: Can I afford a €600 laptop?" artboard from the mockup.
import { ComponentRef, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ChartSpec, LifeStages, Profile } from '../api';
import { Chart, messageParts } from '../components/Visuals';
import { Cap, Person, Send } from '../components/Icons';
import { Button, CoachAvatar, Header, IconButton, Rich } from '../components/ui';
import { colors, font } from '../theme';

export type Message = { role: 'user' | 'assistant'; content: string; charts?: Record<string, ChartSpec>; options?: string[]; time: Date; failed?: boolean };

type Props = {
  profile: Profile | null;
  lifeStages: LifeStages | null;
  stageSource: 'user' | 'guess' | 'default';
  messages: Message[];
  busy: boolean;
  onSend: (text: string) => void;
  onBack: () => void;
  onOpenProfile: () => void;
  onEditStage: () => void;
};

export function ChatScreen({ profile, lifeStages, stageSource, messages, busy, onSend, onBack, onOpenProfile, onEditStage }: Props) {
  const [text, setText] = useState('');
  const scroll = useRef<ComponentRef<typeof ScrollView>>(null);
  const insets = useSafeAreaInsets();

  useEffect(() => {
    const t = setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 50);
    return () => clearTimeout(t);
  }, [messages.length, busy]);

  const send = (value: string) => {
    const v = value.trim();
    if (!v || busy) return;
    setText('');
    onSend(v);
  };

  const stage = profile && lifeStages ? lifeStages[profile.life_stage] : null;
  // Answer buttons belong to the coach's latest question; once the user replies they're gone.
  const last = messages[messages.length - 1];
  const options = last?.role === 'assistant' && !last.failed ? (last.options ?? []) : [];
  const firstTime = messages[0]?.time;

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Header
        title="Money coach"
        subtitle="Uses your S-Pankki data"
        onBack={onBack}
        right={
          <IconButton label="What the coach knows about you" onPress={onOpenProfile}>
            <Person />
          </IconButton>
        }
      />

      <ScrollView ref={scroll} style={{ flex: 1 }} contentContainerStyle={s.body} keyboardShouldPersistTaps="handled">
        <View style={s.stageCard}>
          <View style={s.stageIcon}>
            <Cap />
          </View>
          <View style={{ flex: 1, gap: 2 }}>
            <Text style={font(12, 400, colors.muted)}>
              Your situation{stageSource === 'guess' ? ' (a guess)' : stageSource === 'default' ? ' (not set)' : ''}
            </Text>
            <Text style={font(14, 500)}>
              {stage ? `${stage.label} · safety-net goal ${stage.target_months} months` : 'Loading…'}
            </Text>
          </View>
          <Pressable accessibilityRole="button" accessibilityLabel="Edit your situation" onPress={onEditStage} style={s.edit}>
            <Text style={font(14, 600, colors.green)}>Edit</Text>
          </Pressable>
        </View>

        {firstTime ? <Text style={[font(12, 400, colors.muted), s.time]}>Today {clock(firstTime)}</Text> : null}

        {messages.length === 0 ? (
          <CoachBubble text="Hi! I'm your money coach. Ask me whether you can afford something, how much is safe to spend this month, or how to build a safety net." />
        ) : null}

        {messages.map((m, i) =>
          m.role === 'user' ? (
            <View key={i} style={[s.userBubble, m.failed && { opacity: 0.6 }]}>
              <Text style={[font(15, 400, colors.white), { lineHeight: 21 }]}>{m.content}</Text>
            </View>
          ) : (
            <CoachMessage key={i} content={m.content} charts={m.charts} />
          ),
        )}

        {busy ? (
          <View style={s.coachRow}>
            <CoachAvatar />
            <View style={[s.coachBubble, { flexDirection: 'row', gap: 8, alignItems: 'center' }]}>
              <ActivityIndicator size="small" color={colors.green} />
              <Text style={font(15, 400, colors.muted)}>Looking at your numbers…</Text>
            </View>
          </View>
        ) : options.length ? (
          <View style={s.chips} accessibilityLabel="Answers to the coach's question">
            {options.map((o) => (
              <Button key={o} title={o} kind="outline" onPress={() => send(o)} style={s.answer} />
            ))}
          </View>
        ) : null}
      </ScrollView>

      <View style={[s.composer, { paddingBottom: Math.max(insets.bottom, 12) + 12 }]}>
        <TextInput
          accessibilityLabel="Ask the money coach"
          value={text}
          onChangeText={setText}
          onSubmitEditing={() => send(text)}
          placeholder="Ask about your money…"
          placeholderTextColor={colors.muted}
          returnKeyType="send"
          style={[font(15), s.input]}
        />
        <IconButton label="Send" onPress={() => send(text)} style={[s.send, (!text.trim() || busy) && { opacity: 0.5 }]}>
          <Send />
        </IconButton>
      </View>
    </KeyboardAvoidingView>
  );
}

/** A coach reply: its text, with each [[chart:id]] line replaced by that chart, in one bubble. */
function CoachMessage({ content, charts }: { content: string; charts?: Record<string, ChartSpec> }) {
  const parts = messageParts(content, charts);
  const hasVisual = parts.some((p) => p.kind === 'chart');
  return (
    <View style={s.coachRow}>
      <CoachAvatar />
      <View style={[s.coachBubble, hasVisual && s.wideBubble]}>
        {parts.map((p, j) =>
          p.kind === 'text' ? (
            <Rich key={j} text={p.text} style={[font(15), { lineHeight: 22 }]} />
          ) : (
            <Chart key={j} spec={p.spec} />
          ),
        )}
      </View>
    </View>
  );
}

function CoachBubble({ text }: { text: string }) {
  return (
    <View style={s.coachRow}>
      <CoachAvatar />
      <View style={s.coachBubble}>
        <Rich text={text} style={[font(15), { lineHeight: 22 }]} />
      </View>
    </View>
  );
}

const clock = (d: Date) => `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;

const s = StyleSheet.create({
  body: { padding: 16, gap: 12 },
  stageCard: { flexDirection: 'row', alignItems: 'center', gap: 12, backgroundColor: colors.white, borderRadius: 14, padding: 12, paddingLeft: 14 },
  stageIcon: { width: 36, height: 36, borderRadius: 18, backgroundColor: colors.mint, alignItems: 'center', justifyContent: 'center' },
  edit: { height: 44, paddingHorizontal: 8, justifyContent: 'center' },
  time: { textAlign: 'center', paddingTop: 4 },
  userBubble: {
    alignSelf: 'flex-end',
    maxWidth: '78%',
    backgroundColor: colors.green,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 18,
    borderBottomRightRadius: 4,
  },
  coachRow: { flexDirection: 'row', gap: 8, alignItems: 'flex-end' },
  coachBubble: {
    maxWidth: '82%',
    flexShrink: 1,
    backgroundColor: colors.white,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 18,
    borderBottomLeftRadius: 4,
    gap: 10,
  },
  // A reply with a chart takes the full row, so the chart has room (Visuals.tsx sizes charts to this width).
  wideBubble: { flex: 1, maxWidth: '100%', paddingHorizontal: 14, paddingVertical: 12 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginLeft: 36 },
  answer: { paddingHorizontal: 16 },
  composer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingTop: 10,
    paddingHorizontal: 12,
    backgroundColor: colors.white,
    borderTopWidth: 1,
    borderTopColor: colors.line,
  },
  input: { flex: 1, height: 44, borderWidth: 1, borderColor: colors.border, borderRadius: 999, paddingHorizontal: 16 },
  send: { borderRadius: 22, backgroundColor: colors.green },
});
