// Charts drawn inside the coach's message, on the line where it wrote [[chart:id]].
// The coach picks the chart type, labels and values with its chart tools (../../charts.py); the backend only accepts
// values the engine returned. So everything this file shows is either the coach's labels or an engine number:
// no maths here, and axes only mark 0 and values from the chart itself.
import { ReactNode } from 'react';
import { StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { VictoryAxis, VictoryBar, VictoryChart, VictoryGroup, VictoryLabel, VictoryLine, VictoryScatter, VictoryStack } from 'victory-native';

import { BarChartSpec, BeforeAfterSpec, ChartSpec, KeyFiguresSpec, LineChartSpec, ProgressSpec, Unit } from '../api';
import { colors, eur, font, months, monthsShort, PHONE_MAX_WIDTH } from '../theme';

export type Part = { kind: 'text'; text: string } | { kind: 'chart'; spec: ChartSpec };

const MARKER = /\[\[(?:chart:([A-Za-z0-9_]+)|show:[a-z_]+)\]\]/g;

/** Split a coach reply into its text and the charts it placed with [[chart:id]] lines, each chart at most once. */
export function messageParts(content: string, charts: Record<string, ChartSpec> = {}): Part[] {
  const parts: Part[] = [];
  const used = new Set<string>();
  const pushText = (t: string) => {
    const text = t.trim();
    if (text) parts.push({ kind: 'text', text });
  };
  let from = 0;
  for (const m of content.matchAll(MARKER)) {
    pushText(content.slice(from, m.index));
    const id = m[1];
    if (id && charts[id] && !used.has(id)) {
      parts.push({ kind: 'chart', spec: charts[id] });
      used.add(id);
    }
    from = (m.index ?? 0) + m[0].length;
  }
  pushText(content.slice(from));
  return parts;
}

/** Text with chart markers removed: for history sent back to the coach, so old ids never reach a new reply. */
export const withoutMarkers = (content: string) => content.replace(MARKER, '').replace(/\n{3,}/g, '\n\n').trim();

// Charts sit in the coach's bubble. Their inner width is the phone column minus the chat padding (2×16),
// the avatar and its gap (36), the bubble's padding (2×14) and the panel's own padding (2×12).
const INSET = 32 + 36 + 28 + 24;
const useChartWidth = () => Math.min(useWindowDimensions().width, PHONE_MAX_WIDTH) - INSET;

/** One series colour per position; a highlighted bar is green and the rest are this muted green-grey. */
const SERIES = [colors.green, colors.grey, colors.greenDark, '#6FA584'];
const MUTED_BAR = '#A3B8AA';

/** A value with its unit, for rows and legends: €1 329, 2 years 9 months, 20%, 12. */
export function fmt(value: number, unit: Unit, sign?: 'plus' | 'minus'): string {
  switch (unit) {
    case 'eur':
      return sign === 'plus' ? eur(Math.abs(value), true) : sign === 'minus' ? eur(-Math.abs(value)) : eur(value);
    case 'months':
      return months(value);
    case 'percent':
      return `${value}%`;
    default:
      return String(value);
  }
}

/** Compact form for chart labels: "2 y 9 mo" instead of "2 years 9 months". */
const fmtShort = (value: number, unit: Unit) => (unit === 'months' ? monthsShort(value) : fmt(value, unit));

/** "2026-04" from the engine reads as "4/26"; any label the coach wrote stays as it is. */
const shortLabel = (label: string) => label.replace(/^(\d{4})-(\d{2})$/, (_, y: string, m: string) => `${Number(m)}/${y.slice(2)}`);

export function Chart({ spec }: { spec: ChartSpec }) {
  switch (spec.type) {
    case 'bar_chart':
      return <BarChart spec={spec} />;
    case 'line_chart':
      return <LineChart spec={spec} />;
    case 'progress':
      return <Progress spec={spec} />;
    case 'before_after':
      return <BeforeAfter spec={spec} />;
    case 'key_figures':
      return <KeyFigures spec={spec} />;
    default:
      return null;
  }
}

function Panel({ title, badge, note, children }: { title: string; badge?: string; note?: string; children: ReactNode }) {
  return (
    <View style={s.panel}>
      <View style={s.titleRow}>
        <Text style={[font(13, 600), s.shrink]}>{title}</Text>
        {badge ? (
          <View style={s.pill}>
            <Text style={font(12, 600, colors.green)}>{badge}</Text>
          </View>
        ) : null}
      </View>
      {children}
      {note ? <Text style={[font(12, 400, colors.muted), { lineHeight: 17 }]}>{note}</Text> : null}
    </View>
  );
}

function Row({ label, value, strong, color }: { label: string; value: string; strong?: boolean; color?: string }) {
  return (
    <View style={s.row}>
      <Text style={[font(13), s.shrink]}>{label}</Text>
      <Text style={font(13, strong ? 600 : 400, color ?? (strong ? colors.ink : colors.muted))}>{value}</Text>
    </View>
  );
}

function Legend({ items }: { items: { name: string; color: string; dashed?: boolean; value?: string }[] }) {
  return (
    <View style={s.legend}>
      {items.map((it, i) => (
        <View key={i} style={s.legendItem}>
          <View
            style={
              it.dashed
                ? { width: 16, height: 0, borderTopWidth: 2, borderStyle: 'dashed', borderColor: it.color }
                : { width: 16, height: 8, borderRadius: 2, backgroundColor: it.color }
            }
          />
          <Text style={font(12, 400, colors.muted)}>
            {it.name}
            {it.value ? <Text style={font(12, 600, it.color === colors.grey ? colors.muted : it.color)}> · {it.value}</Text> : null}
          </Text>
        </View>
      ))}
    </View>
  );
}

// ---- key figures ----------------------------------------------------------------------------------------------

function KeyFigures({ spec }: { spec: KeyFiguresSpec }) {
  return (
    <Panel title={spec.title} badge={spec.badge} note={spec.note}>
      {spec.headline ? (
        <View style={{ gap: 2 }}>
          <Text style={font(12, 400, colors.muted)}>{spec.headline.label}</Text>
          <Text style={[font(28, 700, colors.green), { letterSpacing: -0.5 }]}>{fmt(spec.headline.value, spec.headline.unit)}</Text>
        </View>
      ) : null}
      <View style={s.rows}>
        {spec.rows.map((r, i) => (
          <Row
            key={i}
            label={r.label}
            value={fmt(r.value, r.unit, r.sign)}
            strong={r.sign === 'plus'}
            color={r.sign === 'plus' ? colors.green : undefined}
          />
        ))}
      </View>
    </Panel>
  );
}

// ---- progress -------------------------------------------------------------------------------------------------

function Progress({ spec }: { spec: ProgressSpec }) {
  // A little room past the largest value, so a target at the top still shows as a mark.
  const scale = Math.max(spec.target?.value ?? 0, ...spec.bars.map((b) => b.value), 1e-9) * 1.08;
  const pct = (v: number) => `${Math.max(0, Math.min(100, (v / scale) * 100))}%` as const;
  return (
    <Panel title={spec.title} badge={spec.badge} note={spec.note}>
      {spec.bars.map((b, i) => (
        <View key={i} style={{ gap: 6 }} accessible accessibilityLabel={`${b.label}: ${fmt(b.value, spec.unit)}`}>
          {/* The value sits next to its label, not at the right edge: there it read as the target mark's value. */}
          <Text style={font(13)}>
            {b.label} · <Text style={font(13, 600, i === spec.bars.length - 1 ? colors.green : colors.ink)}>{fmt(b.value, spec.unit)}</Text>
          </Text>
          <View style={s.gauge}>
            <View style={[s.gaugeFill, { width: pct(b.value), backgroundColor: i === spec.bars.length - 1 ? colors.green : '#9CCFAD' }]} />
            {spec.target ? <View style={[s.gaugeTarget, { left: pct(spec.target.value) }]} /> : null}
          </View>
        </View>
      ))}
      {spec.target ? (
        <View style={s.legendItem}>
          <View style={{ width: 2, height: 12, backgroundColor: colors.heading }} />
          <Text style={font(12, 400, colors.muted)}>
            {spec.target.label} · <Text style={font(12, 600)}>{fmt(spec.target.value, spec.unit)}</Text>
          </Text>
        </View>
      ) : null}
    </Panel>
  );
}

// ---- before and after ------------------------------------------------------------------------------------------

/** The part of the bar a one-off cost takes away. */
const TAKEN = '#E0796B';

function BeforeAfter({ spec }: { spec: BeforeAfterSpec }) {
  const before = Math.max(0, spec.before.value);
  const after = Math.max(0, Math.min(before, spec.after.value));
  // A little room past the largest value, so a target at the top still shows as a mark.
  const scale = Math.max(spec.target?.value ?? 0, before, 1e-9) * 1.08;
  const pct = (v: number) => `${Math.max(0, Math.min(100, (v / scale) * 100))}%` as const;
  return (
    <Panel title={spec.title} badge={spec.badge} note={spec.note}>
      <View
        style={s.gauge}
        accessible
        accessibilityLabel={`${spec.before.label}: ${fmt(spec.before.value, spec.unit)}. ${spec.change.label}: ${fmt(spec.change.value, spec.unit, 'minus')}. ${spec.after.label}: ${fmt(spec.after.value, spec.unit)}.`}
      >
        {/* The whole amount in the "taken" colour, then what stays drawn over it: the gap between them is the cost. */}
        <View style={[s.gaugeFill, { width: pct(before), backgroundColor: TAKEN }]} />
        <View style={[s.gaugeFill, { width: pct(after), backgroundColor: colors.green, borderTopRightRadius: 0, borderBottomRightRadius: 0 }]} />
        {spec.target ? <View style={[s.gaugeTarget, { left: pct(spec.target.value) }]} /> : null}
      </View>
      <View style={s.rows}>
        <Row label={spec.before.label} value={fmt(spec.before.value, spec.unit)} />
        <Row label={spec.change.label} value={fmt(spec.change.value, spec.unit, 'minus')} strong color={TAKEN} />
        <Row label={spec.after.label} value={fmt(spec.after.value, spec.unit)} strong color={spec.after.value < 0 ? TAKEN : colors.green} />
      </View>
      {spec.target ? (
        <View style={s.legendItem}>
          <View style={{ width: 2, height: 12, backgroundColor: colors.heading }} />
          <Text style={[font(12, 400, colors.muted), s.shrink]}>
            {spec.target.label} · <Text style={font(12, 600)}>{fmt(spec.target.value, spec.unit)}</Text>
          </Text>
        </View>
      ) : null}
    </Panel>
  );
}

// ---- bar chart ------------------------------------------------------------------------------------------------

type BarDatum = { x: number; y: number; fill: string; label: string };
/** Victory hands each bar's datum back to style callbacks. */
const fillOf = (datum: unknown) => (datum as Partial<BarDatum> | undefined)?.fill ?? colors.green;

const chartText = { fontFamily: 'Inter_400Regular', fontSize: 10, fill: colors.muted };

function BarChart({ spec }: { spec: BarChartSpec }) {
  const width = useChartWidth();
  const n = spec.categories.length;
  const many = spec.series.length > 1;
  const grouped = many && !spec.stacked;
  // Bars are always horizontal, so names get the full width on the left and never run into each other.
  // Victory counts x from the bottom; flip it so the first category is on top.
  const xOf = (ci: number) => n - ci;
  const colorOf = (si: number, ci: number) => {
    if (many) return SERIES[si % SERIES.length];
    if (spec.highlight) return spec.categories[ci] === spec.highlight ? colors.green : MUTED_BAR;
    return colors.green;
  };
  const data = spec.series.map((ser, si) =>
    ser.values.map<BarDatum>((y, ci) => ({ x: xOf(ci), y, fill: colorOf(si, ci), label: spec.stacked ? '' : fmtShort(y, spec.unit) })),
  );

  // The name column takes at most 40% of the width. A longer name wraps onto a second line, and only what still
  // does not fit is cut with "…" (the full name stays in the accessibility label). Inter at 10 px is about
  // 6.2 px per character.
  const maxChars = Math.max(4, Math.floor((width * 0.4 - 12) / 6.2));
  const cut = (l: string) => (l.length > maxChars ? l.slice(0, maxChars - 1).trimEnd() + '…' : l);
  const names = spec.categories.map(shortLabel);
  const labels = names.map((l) => {
    if (l.length <= maxChars) return l;
    const at = l.lastIndexOf(' ', maxChars); // the last space the first line can end on
    return at > 0 ? `${l.slice(0, at)}\n${cut(l.slice(at + 1))}` : cut(l);
  });
  const longest = Math.max(...labels.flatMap((l) => l.split('\n')).map((l) => l.length), 1);
  const pad = { top: 8, bottom: 8, left: 12 + longest * 6.2, right: spec.stacked ? 12 : 52 };
  const slots = n * (grouped ? spec.series.length : 1);
  const height = pad.top + pad.bottom + Math.max(slots * 26, 30) + (grouped ? n * 8 : 0);
  const span = (height - pad.top - pad.bottom) / n;
  const barWidth = Math.max(6, Math.min(18, (span * 0.62) / (grouped ? spec.series.length : 1)));

  const bars = data.map((d, si) => (
    <VictoryBar
      key={si}
      data={d}
      barWidth={barWidth}
      cornerRadius={{ top: 3 }}
      labels={({ datum }: { datum?: unknown }) => (datum as Partial<BarDatum> | undefined)?.label ?? ''}
      labelComponent={<VictoryLabel style={{ ...chartText, fill: colors.ink }} />}
      style={{ data: { fill: ({ datum }: { datum?: unknown }) => fillOf(datum) } }}
    />
  ));
  const summary = spec.series
    .map((ser) => `${ser.name}: ` + ser.values.map((v, i) => `${names[i]} ${fmt(v, spec.unit)}`).join(', '))
    .join('. ');

  return (
    <Panel title={spec.title} note={spec.note}>
      <View accessible accessibilityLabel={`${spec.title}. ${summary}`}>
        <VictoryChart
          width={width}
          height={height}
          padding={pad}
          horizontal
          domain={{ x: [0.5, n + 0.5] }}
        >
          <VictoryAxis
            tickValues={labels.map((_, i) => xOf(i))}
            tickFormat={(t: number) => labels[n - t] ?? ''}
            style={{ axis: { stroke: colors.border }, ticks: { size: 0 }, tickLabels: { ...chartText, padding: 6 } }}
          />
          {spec.stacked ? (
            <VictoryStack>{bars}</VictoryStack>
          ) : grouped ? (
            // A group also fills from the bottom: reverse it so the first series is on top, as in the legend.
            <VictoryGroup offset={barWidth + 2}>{[...bars].reverse()}</VictoryGroup>
          ) : (
            bars[0]
          )}
        </VictoryChart>
      </View>
      {many ? (
        <Legend
          items={spec.series.map((ser, si) => ({
            name: ser.name,
            color: SERIES[si % SERIES.length],
            // One stacked bar (a timeline) has no room for labels inside: its legend carries the values.
            value: spec.stacked && n === 1 ? fmtShort(ser.values[0], spec.unit) : undefined,
          }))}
        />
      ) : null}
    </Panel>
  );
}

// ---- line chart -----------------------------------------------------------------------------------------------

type LineDatum = { x: number; y: number; color: string; dashed: boolean };
const lineOf = (datum: unknown) => datum as Partial<LineDatum> | undefined;
const PAD = { top: 26, bottom: 26, left: 44, right: 28 }; // right: room for the last x label, e.g. "3 y 8 mo"

function LineChart({ spec }: { spec: LineChartSpec }) {
  const width = useChartWidth();
  const byMonths = spec.x_unit === 'months';
  const lines = spec.series.map((ser, si) => {
    const color = ser.dashed ? colors.grey : SERIES[si % SERIES.length];
    const points = byMonths ? (ser.points ?? []) : (ser.values ?? []).map((y, i) => ({ x: i + 1, y }));
    return { ...ser, color, points };
  });
  const allY = lines.flatMap((l) => l.points.map((p) => p.y));
  const topY = Math.max(spec.reference?.value ?? 0, ...allY, 1e-9);
  // Axis marks only 0 and values that are in the chart: the furthest point, or the reference line.
  const yTick = spec.reference?.value ?? Math.max(...allY);
  const lastX = Math.max(...lines.map((l) => l.points[l.points.length - 1]?.x ?? 0), 1e-9);
  const labels = (spec.x_labels ?? []).map(shortLabel);
  const xTicks = byMonths ? [0, lastX] : labels.map((_, i) => i + 1);
  const xDomain: [number, number] = byMonths ? [0, lastX] : [0.7, labels.length + 0.3];

  const ends = lines.map((l) => ({ ...l.points[l.points.length - 1], color: l.color, dashed: !!l.dashed }));
  return (
    <Panel title={spec.title} note={spec.note}>
      <View
        accessible
        accessibilityLabel={
          `${spec.title}. ` +
          lines.map((l) => `${l.name}: ` + l.points.map((p) => `${byMonths ? months(p.x) : labels[p.x - 1]} ${fmt(p.y, spec.unit)}`).join(', ')).join('. ')
        }
      >
        <VictoryChart width={width} height={170} padding={PAD} domain={{ x: xDomain, y: [0, topY * 1.12] }}>
          <VictoryAxis
            tickValues={xTicks}
            tickFormat={(t: number) => (byMonths ? (t === 0 ? 'Now' : monthsShort(t)) : (labels[t - 1] ?? ''))}
            style={{ axis: { stroke: colors.border }, ticks: { size: 0 }, tickLabels: { ...chartText, padding: 6 } }}
          />
          <VictoryAxis
            dependentAxis
            tickValues={[0, yTick]}
            tickFormat={(t: number) => fmtShort(t, spec.unit)}
            style={{ axis: { stroke: 'transparent' }, grid: { stroke: colors.border, strokeOpacity: 0.5 }, ticks: { size: 0 }, tickLabels: { ...chartText, padding: 4 } }}
          />
          {spec.reference ? (
            <VictoryLine
              data={[{ x: xDomain[0], y: spec.reference.value }, { x: xDomain[1], y: spec.reference.value }]}
              style={{ data: { stroke: colors.green, strokeWidth: 1, strokeDasharray: '4 4' } }}
            />
          ) : null}
          {spec.reference ? (
            <VictoryLabel
              text={`${spec.reference.label} · ${fmtShort(spec.reference.value, spec.unit)}`}
              x={width - PAD.right}
              y={12}
              textAnchor="end"
              style={{ ...chartText, fontFamily: 'Inter_600SemiBold', fontSize: 11, fill: colors.green }}
            />
          ) : null}
          {lines.map((l, i) => (
            <VictoryLine
              key={i}
              data={l.points}
              style={{ data: { stroke: l.color, strokeWidth: l.dashed ? 2 : 3, strokeDasharray: l.dashed ? '5 4' : undefined, strokeLinecap: 'round' } }}
            />
          ))}
          <VictoryScatter
            data={ends}
            size={({ datum }: { datum?: unknown }) => (lineOf(datum)?.dashed ? 4 : 5)}
            style={{
              data: {
                fill: ({ datum }: { datum?: unknown }) => (lineOf(datum)?.dashed ? colors.mint : (lineOf(datum)?.color ?? colors.green)),
                stroke: ({ datum }: { datum?: unknown }) => lineOf(datum)?.color ?? colors.green,
                strokeWidth: 2,
              },
            }}
          />
        </VictoryChart>
      </View>
      <Legend
        items={lines.map((l) => {
          const end = l.points[l.points.length - 1];
          return { name: l.name, color: l.color, dashed: !!l.dashed, value: byMonths && end ? monthsShort(end.x) : undefined };
        })}
      />
    </Panel>
  );
}

const s = StyleSheet.create({
  panel: { backgroundColor: colors.mint, borderRadius: 12, padding: 12, gap: 10 },
  titleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  shrink: { flexShrink: 1 },
  rows: { gap: 6 },
  row: { flexDirection: 'row', justifyContent: 'space-between', gap: 12 },
  pill: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999, backgroundColor: colors.white },
  gauge: { height: 12, borderRadius: 6, backgroundColor: colors.white, overflow: 'hidden' },
  gaugeFill: { position: 'absolute', left: 0, top: 0, bottom: 0, borderRadius: 6 },
  gaugeTarget: { position: 'absolute', top: 0, bottom: 0, width: 2, marginLeft: -1, backgroundColor: colors.heading },
  legend: { flexDirection: 'row', flexWrap: 'wrap', columnGap: 16, rowGap: 6 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
});
