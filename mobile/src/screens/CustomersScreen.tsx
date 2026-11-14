// Demo-only entry: pick which synthetic S-Bank customer you are.
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { API_URL, Customer, api } from '../api';
import { Chevron } from '../components/Icons';
import { Button, Header } from '../components/ui';
import { colors, font } from '../theme';

export function CustomersScreen({ onPick }: { onPick: (c: Customer) => void }) {
  const [customers, setCustomers] = useState<Customer[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    api.customers().then(setCustomers).catch((e: Error) => setError(e.message));
  };
  useEffect(load, []);

  return (
    <View style={{ flex: 1 }}>
      <Header title="Money coach" subtitle="Demo: choose a customer" />
      <ScrollView contentContainerStyle={s.body}>
        <Text style={[font(14), { lineHeight: 21 }]}>
          Each demo customer is a synthetic S-Pankki customer with their own transactions. The coach only sees summaries of them.
        </Text>
        {error ? (
          <View style={s.list}>
            <View style={{ padding: 16, gap: 10 }}>
              <Text style={font(15, 600)}>Can't reach the coach server</Text>
              <Text style={font(13, 400, colors.muted)}>
                Tried {API_URL}. Start it from the project folder with{' '}
                <Text style={font(13, 600, colors.ink)}>.venv/bin/uvicorn app:app --host 0.0.0.0</Text>
              </Text>
              <Button title="Try again" kind="outline" onPress={load} />
            </View>
          </View>
        ) : !customers ? (
          <ActivityIndicator color={colors.green} style={{ marginTop: 24 }} />
        ) : (
          <View style={s.list}>
            {customers.map((c, i) => (
              <Pressable
                key={c.id}
                accessibilityRole="button"
                onPress={() => onPick(c)}
                style={({ pressed }) => [s.item, i < customers.length - 1 && s.itemLine, pressed && { opacity: 0.6 }]}
              >
                <View style={{ flex: 1, gap: 2 }}>
                  <Text style={font(15, 500)}>{c.label}</Text>
                  <Text style={font(12, 400, colors.muted)}>{c.id}</Text>
                </View>
                <Chevron />
              </Pressable>
            ))}
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  body: { padding: 16, gap: 14 },
  list: { backgroundColor: colors.white, borderRadius: 16 },
  item: { flexDirection: 'row', alignItems: 'center', gap: 12, minHeight: 60, paddingHorizontal: 16, paddingVertical: 10 },
  itemLine: { borderBottomWidth: 1, borderBottomColor: colors.line },
});
