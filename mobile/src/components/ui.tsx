// Small building blocks shared by both screens.
import { ReactNode } from 'react';
import { Pressable, StyleProp, StyleSheet, Text, View, ViewStyle } from 'react-native';

import { colors, font } from '../theme';
import { Alert, Back, Check, Headset } from './Icons';

export function Header({ title, subtitle, onBack, right }: { title: string; subtitle?: string; onBack?: () => void; right?: ReactNode }) {
  return (
    <View style={s.header}>
      {onBack ? (
        <IconButton label="Back" onPress={onBack}>
          <Back />
        </IconButton>
      ) : (
        <View style={s.icon} />
      )}
      <View style={s.headerText}>
        <Text style={font(17, 600, colors.heading)}>{title}</Text>
        {subtitle ? <Text style={font(12, 400, colors.muted)}>{subtitle}</Text> : null}
      </View>
      {right ?? <View style={s.icon} />}
    </View>
  );
}

export function IconButton({ label, onPress, children, style }: { label: string; onPress: () => void; children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={label} onPress={onPress} hitSlop={4} style={({ pressed }) => [s.icon, style, pressed && s.pressed]}>
      {children}
    </Pressable>
  );
}

type ButtonKind = 'primary' | 'outline' | 'ghost' | 'neutral';

export function Button({ title, onPress, kind = 'primary', style, disabled }: { title: string; onPress: () => void; kind?: ButtonKind; style?: StyleProp<ViewStyle>; disabled?: boolean }) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [s.button, s[kind], style, (pressed || disabled) && s.pressed]}
    >
      <Text style={buttonText[kind]}>{title}</Text>
    </Pressable>
  );
}

const buttonText: Record<ButtonKind, object> = {
  primary: font(14, 600, colors.white),
  outline: font(14, 600, colors.green),
  ghost: font(14, 400, colors.muted),
  neutral: font(15, 600, colors.ink),
};

export type TagKind = 'confirmed' | 'guess' | 'data';

export function Tag({ kind, text }: { kind: TagKind; text: string }) {
  const style = kind === 'confirmed' ? s.tagGreen : kind === 'guess' ? s.tagWarn : s.tagGrey;
  const color = kind === 'confirmed' ? colors.green : kind === 'guess' ? colors.warnInk : colors.heading;
  return (
    <View style={[s.tag, style]}>
      {kind === 'confirmed' ? <Check /> : kind === 'guess' ? <Alert /> : null}
      <Text style={font(12, 600, color)}>{text}</Text>
    </View>
  );
}

export function Badge({ text }: { text: string }) {
  return (
    <View style={s.badge}>
      <Text style={font(12, 600, colors.green)}>{text}</Text>
    </View>
  );
}

export function CoachAvatar() {
  return (
    <View style={s.avatar}>
      <Headset />
    </View>
  );
}

/** Renders **bold** spans, which the language model likes to use. */
export function Rich({ text, style }: { text: string; style: object }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <Text style={style}>
      {parts.map((p, i) =>
        p.startsWith('**') && p.endsWith('**') ? (
          <Text key={i} style={{ fontFamily: 'Inter_600SemiBold' }}>
            {p.slice(2, -2)}
          </Text>
        ) : (
          p
        ),
      )}
    </Text>
  );
}

export const Divider = () => <View style={{ height: 1, backgroundColor: colors.line }} />;

const s = StyleSheet.create({
  header: {
    height: 60,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 8,
    backgroundColor: colors.white,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  headerText: { alignItems: 'center', gap: 2, flex: 1 },
  icon: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  pressed: { opacity: 0.6 },
  button: { minHeight: 44, borderRadius: 999, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 18 },
  primary: { backgroundColor: colors.green },
  outline: { backgroundColor: colors.white, borderWidth: 1.5, borderColor: colors.green },
  ghost: { backgroundColor: 'transparent', paddingHorizontal: 10 },
  neutral: { minHeight: 48, backgroundColor: colors.white, borderWidth: 1.5, borderColor: colors.border },
  tag: { alignSelf: 'flex-start', flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 999 },
  tagGreen: { backgroundColor: colors.mint },
  tagWarn: { backgroundColor: colors.warnBg },
  tagGrey: { backgroundColor: colors.chip },
  badge: { alignSelf: 'flex-start', backgroundColor: colors.mint, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
  avatar: { width: 28, height: 28, borderRadius: 14, backgroundColor: colors.green, alignItems: 'center', justifyContent: 'center' },
});
