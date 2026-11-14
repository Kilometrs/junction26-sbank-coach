// "What the coach thinks it knows" artboard from the mockup.
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { LifeStages, Profile } from '../api';
import { Chevron, Pencil, Shield } from '../components/Icons';
import { Button, CoachAvatar, Header, IconButton, Tag, TagKind } from '../components/ui';
import { colors, eur, font, months } from '../theme';

type Props = {
  profile: Profile | null;
  lifeStages: LifeStages | null;
  stageSource: 'user' | 'guess' | 'default';
  detection: boolean;
  onBack: () => void;
  onSetStage: (stage: string) => void;
  onEditStage: () => void;
  onToggleDetection: () => void;
  onShowSent: () => void;
  onForget: () => void;
};

export function ProfileScreen(p: Props) {
  const { profile, lifeStages } = p;
  const signal = profile?.life_stage_signals[0];
  const askAbout = p.detection && p.stageSource === 'guess' && signal && lifeStages ? signal : null;

  return (
    <View style={{ flex: 1 }}>
      <Header title="Your money profile" onBack={p.onBack} />
      <ScrollView contentContainerStyle={s.body}>
        <Text style={[font(14), { lineHeight: 21 }]}>
          The coach uses this profile to tailor its advice. It's built from your transactions, and you can correct or delete anything.
        </Text>

        {askAbout && lifeStages ? (
          <View style={s.coachRow}>
            <CoachAvatar />
            <View style={s.question}>
              <Text style={[font(15), { lineHeight: 22 }]}>
                Quick check: {askAbout.why}{' '}
                <Text style={font(15, 600)}>Is "{lifeStages[askAbout.stage].label.toLowerCase()}" right for you?</Text>
              </Text>
              <Text style={font(12, 400, colors.muted)}>
                If yes, I'll aim for a {lifeStages[askAbout.stage].target_months}-month safety net.
              </Text>
              <View style={s.buttons}>
                <Button title="Yes, that's me" onPress={() => p.onSetStage(askAbout.stage)} />
                <Button title="No" kind="outline" onPress={p.onEditStage} />
                <Button title="Don't use this" kind="ghost" onPress={p.onToggleDetection} />
              </View>
            </View>
          </View>
        ) : null}

        <Text style={s.section}>What the coach thinks it knows</Text>
        {profile && lifeStages ? (
          <View style={s.group}>
            <Fact
              label="Your situation"
              value={lifeStages[profile.life_stage].label}
              tag={p.stageSource === 'user' ? ['confirmed', 'Confirmed by you'] : p.stageSource === 'guess' ? ['guess', 'Guess, please check'] : ['data', 'Default']}
              onEdit={p.onEditStage}
            />
            <Fact
              label="Income"
              value={`About ${eur(profile.income_monthly)} a month (lowest month this year ${eur(profile.income_lowest_month)})`}
              tag={['data', 'From your transactions']}
            />
            <Fact
              label="Must-pay costs"
              value={`${eur(profile.buckets_monthly.fixed)} regular bills + ${eur(profile.buckets_monthly.irregular)} irregular costs a month`}
              tag={['data', 'From your transactions']}
            />
            <Fact
              label="Everyday spending"
              value={`About ${eur(profile.buckets_monthly.flexible)} a month on eating out, fun, shopping and travel`}
              tag={['data', 'From your transactions']}
            />
            <Fact
              label="Safety net"
              value={`${eur(profile.balance)} covers ${months(profile.safety_net.months_now)}. Goal: ${months(profile.safety_net.target_months)} (${eur(profile.safety_net.target_eur)})`}
              tag={['data', `As of ${profile.as_of}`]}
              last
            />
          </View>
        ) : (
          <View style={[s.group, { padding: 16 }]}>
            <Text style={font(14, 400, colors.muted)}>Loading your profile…</Text>
          </View>
        )}

        <Text style={s.section}>Privacy</Text>
        <View style={s.group}>
          <View style={[s.toggleRow, s.line]}>
            <View style={{ flex: 1, gap: 2 }}>
              <Text style={font(15, 500)}>Detect my situation</Text>
              <Text style={font(12, 400, colors.muted)}>
                {p.detection ? 'Guesses from your transactions. You confirm before it counts.' : 'Off. The coach uses a standard 3-month goal.'}
              </Text>
            </View>
            <Pressable
              accessibilityRole="switch"
              accessibilityLabel="Detect my situation"
              accessibilityState={{ checked: p.detection }}
              onPress={p.onToggleDetection}
              style={[s.switch, p.detection ? s.switchOn : s.switchOff]}
            >
              <View style={s.knob} />
            </Pressable>
          </View>
          <View style={[s.privacy, s.line]}>
            <Shield />
            <Text style={[font(13), { lineHeight: 19, flex: 1 }]}>
              The AI only sees summaries like category totals, never your raw transactions or merchant names. Your profile is used for coaching only,
              never for marketing, credit decisions or pricing.
            </Text>
          </View>
          <Pressable accessibilityRole="link" onPress={p.onShowSent} style={({ pressed }) => [s.link, pressed && { opacity: 0.6 }]}>
            <Text style={font(15)}>See what was sent to the AI</Text>
            <Chevron />
          </Pressable>
        </View>

        <Button title="Forget everything about me" kind="neutral" onPress={p.onForget} />
      </ScrollView>
    </View>
  );
}

function Fact({ label, value, tag, onEdit, last }: { label: string; value: string; tag: [TagKind, string]; onEdit?: () => void; last?: boolean }) {
  return (
    <View style={[s.fact, !last && s.line]}>
      <View style={{ flex: 1, gap: 4 }}>
        <Text style={font(12, 400, colors.muted)}>{label}</Text>
        <Text style={[font(15, 500), { lineHeight: 21 }]}>{value}</Text>
        <Tag kind={tag[0]} text={tag[1]} />
      </View>
      {onEdit ? (
        <IconButton label={`Edit ${label.toLowerCase()}`} onPress={onEdit}>
          <Pencil />
        </IconButton>
      ) : (
        <View style={{ width: 44 }} />
      )}
    </View>
  );
}

const s = StyleSheet.create({
  body: { padding: 16, gap: 14 },
  coachRow: { flexDirection: 'row', gap: 8, alignItems: 'flex-end' },
  question: { flex: 1, backgroundColor: colors.white, borderRadius: 18, borderBottomLeftRadius: 4, padding: 14, gap: 12 },
  buttons: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  section: { ...font(15, 700, colors.green), paddingTop: 6 },
  group: { backgroundColor: colors.white, borderRadius: 16 },
  line: { borderBottomWidth: 1, borderBottomColor: colors.line },
  fact: { flexDirection: 'row', gap: 12, alignItems: 'flex-start', paddingVertical: 14, paddingLeft: 16, paddingRight: 8 },
  toggleRow: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, paddingLeft: 16 },
  switch: { width: 52, height: 32, borderRadius: 16, padding: 3, flexDirection: 'row' },
  switchOn: { backgroundColor: colors.green, justifyContent: 'flex-end' },
  switchOff: { backgroundColor: colors.border, justifyContent: 'flex-start' },
  knob: { width: 26, height: 26, borderRadius: 13, backgroundColor: colors.white },
  privacy: { flexDirection: 'row', gap: 10, paddingVertical: 14, paddingHorizontal: 16 },
  link: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', minHeight: 48, paddingHorizontal: 16 },
});
