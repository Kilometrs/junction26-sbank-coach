// Stroke icons copied from the mockup's inline SVGs.
import Svg, { Circle, Path, Rect } from 'react-native-svg';

import { colors } from '../theme';

type P = { size?: number; color?: string };

export const Back = ({ size = 22, color = colors.heading }: P) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
    <Path d="M15 5l-7 7 7 7" />
  </Svg>
);

export const Person = ({ size = 22, color = colors.heading }: P) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round">
    <Circle cx={12} cy={8} r={4} />
    <Path d="M4 20c1.5-4 4.5-6 8-6s6.5 2 8 6" />
  </Svg>
);

export const Cap = ({ size = 20, color = colors.green }: P) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round">
    <Path d="M2 9l10-5 10 5-10 5z" />
    <Path d="M6 11v5c2 2 10 2 12 0v-5" />
  </Svg>
);

export const Headset = ({ size = 16, color = colors.white }: P) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <Path d="M4 12a8 8 0 0 1 16 0v5a3 3 0 0 1-3 3h-2" />
    <Path d="M4 12v3a2 2 0 0 0 2 2h1v-6H6a2 2 0 0 0-2 2" />
    <Path d="M20 12v3" />
  </Svg>
);

export const Send = ({ size = 20, color = colors.white }: P) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <Path d="M12 19V5" />
    <Path d="M6 11l6-6 6 6" />
  </Svg>
);

export const Mic = ({ size = 20, color = colors.green }: P) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
    <Rect x={9} y={3} width={6} height={11} rx={3} />
    <Path d="M5 11a7 7 0 0 0 14 0" />
    <Path d="M12 18v3" />
  </Svg>
);

export const Check = ({ size = 12, color = colors.green }: P) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
    <Path d="M5 12l5 5 9-10" />
  </Svg>
);

export const Alert = ({ size = 12, color = colors.warnInk }: P) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
    <Circle cx={12} cy={12} r={9} />
    <Path d="M12 8v5" />
    <Path d="M12 16.5v.01" />
  </Svg>
);

export const Pencil = ({ size = 18, color = colors.muted }: P) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
    <Path d="M4 20h4L19 9l-4-4L4 16z" />
    <Path d="M13 7l4 4" />
  </Svg>
);

export const Shield = ({ size = 18, color = colors.green }: P) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
    <Path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" />
  </Svg>
);

export const Chevron = ({ size = 16, color = colors.muted }: P) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
    <Path d="M9 5l7 7-7 7" />
  </Svg>
);
